"""
性能监控模块
提供API响应时间监控和慢请求告警功能
"""
import time
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._lock = threading.Lock()
        # 使用内存存储最近的响应时间数据（生产环境建议使用Redis）
        self._response_times = defaultdict(lambda: deque(maxlen=1000))  # 每个端点保留最近1000次请求
        self._slow_request_threshold = 1000  # 慢请求阈值：1000ms
        self._critical_threshold = 5000  # 严重慢请求阈值：5000ms
        
    def record_response_time(self, endpoint, method, response_time_ms, status_code):
        """记录API响应时间"""
        try:
            with self._lock:
                key = f"{method}:{endpoint}"
                timestamp = timezone.now()
                
                record = {
                    'timestamp': timestamp,
                    'response_time_ms': response_time_ms,
                    'status_code': status_code,
                    'is_slow': response_time_ms >= self._slow_request_threshold,
                    'is_critical': response_time_ms >= self._critical_threshold
                }
                
                self._response_times[key].append(record)
                
                # 记录慢请求日志
                if response_time_ms >= self._critical_threshold:
                    logger.warning(
                        f"严重慢请求: {method} {endpoint} - {response_time_ms:.2f}ms "
                        f"(状态码: {status_code})"
                    )
                elif response_time_ms >= self._slow_request_threshold:
                    logger.info(
                        f"慢请求: {method} {endpoint} - {response_time_ms:.2f}ms "
                        f"(状态码: {status_code})"
                    )
                
                # 缓存最新的统计数据（用于快速查询）
                self._update_cached_stats(key)
                
        except Exception as e:
            logger.error(f"记录响应时间失败: {str(e)}")
    
    def _update_cached_stats(self, endpoint_key):
        """更新缓存的统计数据"""
        try:
            records = list(self._response_times[endpoint_key])
            if not records:
                return
            
            # 计算最近100次请求的统计数据
            recent_records = records[-100:] if len(records) >= 100 else records
            response_times = [r['response_time_ms'] for r in recent_records]
            
            stats = {
                'avg_response_time': sum(response_times) / len(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'slow_requests_count': sum(1 for r in recent_records if r['is_slow']),
                'critical_requests_count': sum(1 for r in recent_records if r['is_critical']),
                'total_requests': len(recent_records),
                'slow_request_rate': sum(1 for r in recent_records if r['is_slow']) / len(recent_records) * 100,
                'last_updated': timezone.now().isoformat()
            }
            
            # 缓存5分钟
            cache.set(f"perf_stats:{endpoint_key}", stats, 300)
            
        except Exception as e:
            logger.error(f"更新缓存统计失败: {str(e)}")
    
    def get_endpoint_stats(self, endpoint=None, method=None, hours=24):
        """获取端点性能统计"""
        try:
            with self._lock:
                if endpoint and method:
                    # 获取特定端点的统计
                    key = f"{method}:{endpoint}"
                    cached_stats = cache.get(f"perf_stats:{key}")
                    if cached_stats:
                        return {key: cached_stats}
                    
                    records = list(self._response_times[key])
                    if not records:
                        return {key: None}
                    
                    return {key: self._calculate_stats(records, hours)}
                else:
                    # 获取所有端点的统计
                    all_stats = {}
                    for key in self._response_times.keys():
                        cached_stats = cache.get(f"perf_stats:{key}")
                        if cached_stats:
                            all_stats[key] = cached_stats
                        else:
                            records = list(self._response_times[key])
                            all_stats[key] = self._calculate_stats(records, hours)
                    
                    return all_stats
                    
        except Exception as e:
            logger.error(f"获取端点统计失败: {str(e)}")
            return {}
    
    def _calculate_stats(self, records, hours=24):
        """计算统计数据"""
        if not records:
            return None
        
        # 过滤指定时间范围内的记录
        cutoff_time = timezone.now() - timedelta(hours=hours)
        filtered_records = [r for r in records if r['timestamp'] >= cutoff_time]
        
        if not filtered_records:
            return None
        
        response_times = [r['response_time_ms'] for r in filtered_records]
        
        # 计算百分位数
        sorted_times = sorted(response_times)
        count = len(sorted_times)
        
        def percentile(p):
            index = int(count * p / 100)
            if index >= count:
                index = count - 1
            return sorted_times[index]
        
        return {
            'total_requests': count,
            'avg_response_time': sum(response_times) / count,
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p50_response_time': percentile(50),
            'p90_response_time': percentile(90),
            'p95_response_time': percentile(95),
            'p99_response_time': percentile(99),
            'slow_requests_count': sum(1 for r in filtered_records if r['is_slow']),
            'critical_requests_count': sum(1 for r in filtered_records if r['is_critical']),
            'slow_request_rate': sum(1 for r in filtered_records if r['is_slow']) / count * 100,
            'error_rate': sum(1 for r in filtered_records if r['status_code'] >= 400) / count * 100,
            'time_range_hours': hours,
            'last_updated': timezone.now().isoformat()
        }
    
    def get_slow_requests(self, hours=1, limit=50):
        """获取慢请求列表"""
        try:
            with self._lock:
                cutoff_time = timezone.now() - timedelta(hours=hours)
                slow_requests = []
                
                for endpoint_key, records in self._response_times.items():
                    for record in records:
                        if (record['timestamp'] >= cutoff_time and 
                            record['response_time_ms'] >= self._slow_request_threshold):
                            slow_requests.append({
                                'endpoint': endpoint_key,
                                'timestamp': record['timestamp'].isoformat(),
                                'response_time_ms': record['response_time_ms'],
                                'status_code': record['status_code'],
                                'is_critical': record['is_critical']
                            })
                
                # 按响应时间降序排序
                slow_requests.sort(key=lambda x: x['response_time_ms'], reverse=True)
                
                return slow_requests[:limit]
                
        except Exception as e:
            logger.error(f"获取慢请求列表失败: {str(e)}")
            return []
    
    def check_performance_alerts(self):
        """检查性能告警"""
        try:
            alerts = []
            
            # 检查最近1小时的性能数据
            stats = self.get_endpoint_stats(hours=1)
            
            for endpoint_key, endpoint_stats in stats.items():
                if not endpoint_stats:
                    continue
                
                # 检查慢请求率
                if endpoint_stats['slow_request_rate'] > 10:  # 慢请求率超过10%
                    alerts.append({
                        'type': 'high_slow_request_rate',
                        'level': 'warning',
                        'endpoint': endpoint_key,
                        'message': f"{endpoint_key} 慢请求率过高: {endpoint_stats['slow_request_rate']:.1f}%",
                        'value': endpoint_stats['slow_request_rate'],
                        'threshold': 10
                    })
                
                # 检查平均响应时间
                if endpoint_stats['avg_response_time'] > 2000:  # 平均响应时间超过2秒
                    alerts.append({
                        'type': 'high_avg_response_time',
                        'level': 'warning',
                        'endpoint': endpoint_key,
                        'message': f"{endpoint_key} 平均响应时间过高: {endpoint_stats['avg_response_time']:.0f}ms",
                        'value': endpoint_stats['avg_response_time'],
                        'threshold': 2000
                    })
                
                # 检查P95响应时间
                if endpoint_stats['p95_response_time'] > 5000:  # P95响应时间超过5秒
                    alerts.append({
                        'type': 'high_p95_response_time',
                        'level': 'critical',
                        'endpoint': endpoint_key,
                        'message': f"{endpoint_key} P95响应时间过高: {endpoint_stats['p95_response_time']:.0f}ms",
                        'value': endpoint_stats['p95_response_time'],
                        'threshold': 5000
                    })
                
                # 检查错误率
                if endpoint_stats['error_rate'] > 5:  # 错误率超过5%
                    alerts.append({
                        'type': 'high_error_rate',
                        'level': 'warning',
                        'endpoint': endpoint_key,
                        'message': f"{endpoint_key} 错误率过高: {endpoint_stats['error_rate']:.1f}%",
                        'value': endpoint_stats['error_rate'],
                        'threshold': 5
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查性能告警失败: {str(e)}")
            return []
    
    def get_performance_summary(self):
        """获取性能监控摘要"""
        try:
            # 获取最近24小时的统计
            stats = self.get_endpoint_stats(hours=24)
            
            if not stats:
                return {
                    'total_endpoints': 0,
                    'total_requests': 0,
                    'overall_avg_response_time': 0,
                    'slow_request_rate': 0,
                    'error_rate': 0,
                    'alerts_count': 0
                }
            
            # 计算总体统计
            total_requests = sum(s['total_requests'] for s in stats.values() if s)
            total_slow_requests = sum(s['slow_requests_count'] for s in stats.values() if s)
            total_errors = sum(s['total_requests'] * s['error_rate'] / 100 for s in stats.values() if s)
            
            # 计算加权平均响应时间
            weighted_avg_response_time = 0
            if total_requests > 0:
                weighted_avg_response_time = sum(
                    s['avg_response_time'] * s['total_requests'] 
                    for s in stats.values() if s
                ) / total_requests
            
            # 获取告警数量
            alerts = self.check_performance_alerts()
            
            return {
                'total_endpoints': len([s for s in stats.values() if s]),
                'total_requests': total_requests,
                'overall_avg_response_time': weighted_avg_response_time,
                'slow_request_rate': (total_slow_requests / total_requests * 100) if total_requests > 0 else 0,
                'error_rate': (total_errors / total_requests * 100) if total_requests > 0 else 0,
                'alerts_count': len(alerts),
                'critical_alerts_count': len([a for a in alerts if a['level'] == 'critical']),
                'warning_alerts_count': len([a for a in alerts if a['level'] == 'warning']),
                'last_updated': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取性能摘要失败: {str(e)}")
            return {}


# 单例实例
performance_monitor = PerformanceMonitor()