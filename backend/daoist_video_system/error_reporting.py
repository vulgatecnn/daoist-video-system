"""
错误报告和监控服务
"""
import logging
import json
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from collections import defaultdict, Counter
import threading
import time

logger = logging.getLogger(__name__)


class ErrorReportingService:
    """错误报告服务"""
    
    def __init__(self):
        self.error_stats = defaultdict(int)
        self.error_details = []
        self.last_report_time = timezone.now()
        self.report_interval = timedelta(hours=1)  # 每小时报告一次
        self.max_errors_per_report = 100
        self._lock = threading.Lock()
    
    def record_error(self, error_info):
        """记录错误信息"""
        with self._lock:
            # 统计错误类型
            error_type = error_info.get('exception_type', 'Unknown')
            self.error_stats[error_type] += 1
            
            # 保存错误详情
            error_record = {
                'timestamp': timezone.now().isoformat(),
                'error_id': error_info.get('error_id'),
                'type': error_type,
                'message': error_info.get('exception_message', ''),
                'path': error_info.get('path', ''),
                'method': error_info.get('method', ''),
                'user': error_info.get('user', ''),
                'ip_address': error_info.get('ip_address', ''),
                'user_agent': error_info.get('user_agent', '')
            }
            
            self.error_details.append(error_record)
            
            # 限制错误详情数量
            if len(self.error_details) > self.max_errors_per_report * 2:
                self.error_details = self.error_details[-self.max_errors_per_report:]
            
            # 检查是否需要发送报告
            self._check_and_send_report()
    
    def _check_and_send_report(self):
        """检查是否需要发送错误报告"""
        now = timezone.now()
        
        # 检查时间间隔
        if now - self.last_report_time >= self.report_interval:
            self._send_error_report()
            self.last_report_time = now
        
        # 检查严重错误（短时间内大量错误）
        recent_errors = [
            error for error in self.error_details
            if datetime.fromisoformat(error['timestamp'].replace('Z', '+00:00')) > now - timedelta(minutes=10)
        ]
        
        if len(recent_errors) >= 20:  # 10分钟内超过20个错误
            self._send_urgent_report(recent_errors)
    
    def _send_error_report(self):
        """发送错误报告"""
        if not self.error_stats:
            return
        
        try:
            report = self._generate_error_report()
            self._save_error_report(report)
            
            # 如果配置了邮件，发送邮件通知
            if hasattr(settings, 'ADMIN_EMAIL') and settings.ADMIN_EMAIL:
                self._send_email_report(report)
            
            # 清空统计数据
            self.error_stats.clear()
            self.error_details.clear()
            
            logger.info("错误报告已生成并发送")
            
        except Exception as e:
            logger.error(f"发送错误报告失败: {str(e)}")
    
    def _send_urgent_report(self, recent_errors):
        """发送紧急错误报告"""
        try:
            report = {
                'type': 'urgent',
                'timestamp': timezone.now().isoformat(),
                'message': f'检测到异常高频错误：10分钟内发生 {len(recent_errors)} 个错误',
                'recent_errors': recent_errors[-10:],  # 只包含最近10个错误
                'error_types': Counter([error['type'] for error in recent_errors])
            }
            
            self._save_error_report(report, urgent=True)
            
            if hasattr(settings, 'ADMIN_EMAIL') and settings.ADMIN_EMAIL:
                self._send_urgent_email(report)
            
            logger.warning(f"发送紧急错误报告：{len(recent_errors)} 个错误")
            
        except Exception as e:
            logger.error(f"发送紧急错误报告失败: {str(e)}")
    
    def _generate_error_report(self):
        """生成错误报告"""
        now = timezone.now()
        
        # 统计最常见的错误
        top_errors = Counter(self.error_stats).most_common(10)
        
        # 统计错误路径
        path_stats = Counter([error['path'] for error in self.error_details])
        top_paths = path_stats.most_common(5)
        
        # 统计用户错误
        user_stats = Counter([error['user'] for error in self.error_details if error['user'] != 'Anonymous'])
        top_users = user_stats.most_common(5)
        
        report = {
            'type': 'regular',
            'timestamp': now.isoformat(),
            'period': {
                'start': (now - self.report_interval).isoformat(),
                'end': now.isoformat()
            },
            'summary': {
                'total_errors': sum(self.error_stats.values()),
                'unique_error_types': len(self.error_stats),
                'affected_paths': len(path_stats),
                'affected_users': len(user_stats)
            },
            'top_errors': [{'type': error_type, 'count': count} for error_type, count in top_errors],
            'top_paths': [{'path': path, 'count': count} for path, count in top_paths],
            'top_users': [{'user': user, 'count': count} for user, count in top_users],
            'recent_errors': self.error_details[-20:] if len(self.error_details) > 20 else self.error_details
        }
        
        return report
    
    def _save_error_report(self, report, urgent=False):
        """保存错误报告到文件"""
        try:
            # 创建报告目录
            reports_dir = os.path.join(settings.BASE_DIR, 'logs', 'error_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = 'urgent_' if urgent else 'regular_'
            filename = f"{prefix}error_report_{timestamp}.json"
            filepath = os.path.join(reports_dir, filename)
            
            # 保存报告
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"错误报告已保存: {filepath}")
            
        except Exception as e:
            logger.error(f"保存错误报告失败: {str(e)}")
    
    def _send_email_report(self, report):
        """发送邮件报告"""
        try:
            subject = f"道士经文视频系统 - 错误报告 ({report['timestamp']})"
            
            message = f"""
系统错误报告

报告时间: {report['timestamp']}
报告周期: {report['period']['start']} 至 {report['period']['end']}

错误统计:
- 总错误数: {report['summary']['total_errors']}
- 错误类型数: {report['summary']['unique_error_types']}
- 受影响路径数: {report['summary']['affected_paths']}
- 受影响用户数: {report['summary']['affected_users']}

最常见错误:
"""
            
            for error in report['top_errors'][:5]:
                message += f"- {error['type']}: {error['count']} 次\n"
            
            message += "\n最常见错误路径:\n"
            for path in report['top_paths'][:3]:
                message += f"- {path['path']}: {path['count']} 次\n"
            
            message += "\n详细报告请查看系统日志文件。"
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False
            )
            
        except Exception as e:
            logger.error(f"发送邮件报告失败: {str(e)}")
    
    def _send_urgent_email(self, report):
        """发送紧急邮件通知"""
        try:
            subject = "【紧急】道士经文视频系统 - 高频错误警报"
            
            message = f"""
紧急错误警报！

检测时间: {report['timestamp']}
警报原因: {report['message']}

错误类型分布:
"""
            
            for error_type, count in report['error_types'].items():
                message += f"- {error_type}: {count} 次\n"
            
            message += "\n请立即检查系统状态并采取必要措施。"
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False
            )
            
        except Exception as e:
            logger.error(f"发送紧急邮件失败: {str(e)}")
    
    def get_error_statistics(self, hours=24):
        """获取错误统计信息"""
        try:
            # 读取最近的错误报告
            reports_dir = os.path.join(settings.BASE_DIR, 'logs', 'error_reports')
            if not os.path.exists(reports_dir):
                return {'total_errors': 0, 'error_types': {}, 'recent_reports': []}
            
            # 获取最近的报告文件
            now = datetime.now()
            cutoff_time = now - timedelta(hours=hours)
            
            recent_reports = []
            total_errors = 0
            error_types = Counter()
            
            for filename in os.listdir(reports_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(reports_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_time >= cutoff_time:
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                report = json.load(f)
                                recent_reports.append({
                                    'filename': filename,
                                    'timestamp': report.get('timestamp'),
                                    'type': report.get('type'),
                                    'summary': report.get('summary', {})
                                })
                                
                                # 累计统计
                                if 'summary' in report:
                                    total_errors += report['summary'].get('total_errors', 0)
                                
                                if 'top_errors' in report:
                                    for error in report['top_errors']:
                                        error_types[error['type']] += error['count']
                        
                        except Exception as e:
                            logger.error(f"读取错误报告失败 {filename}: {str(e)}")
            
            return {
                'total_errors': total_errors,
                'error_types': dict(error_types.most_common(10)),
                'recent_reports': sorted(recent_reports, key=lambda x: x['timestamp'], reverse=True)
            }
            
        except Exception as e:
            logger.error(f"获取错误统计失败: {str(e)}")
            return {'total_errors': 0, 'error_types': {}, 'recent_reports': []}


# 全局错误报告服务实例
error_reporting_service = ErrorReportingService()


class PerformanceMonitor:
    """性能监控服务"""
    
    def __init__(self):
        self.request_times = []
        self.slow_requests = []
        self.max_records = 1000
        self._lock = threading.Lock()
    
    def record_request(self, path, method, duration, status_code):
        """记录请求性能"""
        with self._lock:
            request_record = {
                'timestamp': timezone.now().isoformat(),
                'path': path,
                'method': method,
                'duration': duration,
                'status_code': status_code
            }
            
            self.request_times.append(request_record)
            
            # 记录慢请求（超过5秒）
            if duration > 5000:
                self.slow_requests.append(request_record)
            
            # 限制记录数量
            if len(self.request_times) > self.max_records:
                self.request_times = self.request_times[-self.max_records//2:]
            
            if len(self.slow_requests) > 100:
                self.slow_requests = self.slow_requests[-50:]
    
    def get_performance_stats(self, hours=1):
        """获取性能统计"""
        with self._lock:
            now = timezone.now()
            cutoff_time = now - timedelta(hours=hours)
            
            # 筛选时间范围内的请求
            recent_requests = [
                req for req in self.request_times
                if datetime.fromisoformat(req['timestamp'].replace('Z', '+00:00')) >= cutoff_time
            ]
            
            if not recent_requests:
                return {
                    'total_requests': 0,
                    'avg_response_time': 0,
                    'slow_requests': 0,
                    'error_rate': 0
                }
            
            # 计算统计数据
            durations = [req['duration'] for req in recent_requests]
            error_requests = [req for req in recent_requests if req['status_code'] >= 400]
            slow_requests = [req for req in recent_requests if req['duration'] > 5000]
            
            return {
                'total_requests': len(recent_requests),
                'avg_response_time': sum(durations) / len(durations),
                'max_response_time': max(durations),
                'min_response_time': min(durations),
                'slow_requests': len(slow_requests),
                'error_rate': len(error_requests) / len(recent_requests) * 100,
                'recent_slow_requests': slow_requests[-10:]
            }


# 全局性能监控实例
performance_monitor = PerformanceMonitor()