#!/usr/bin/env python
"""
道士经文视频管理系统 - 负载和性能测试
测试系统在高负载下的表现
"""
import os
import sys
import django
import time
import threading
import concurrent.futures
import statistics
from pathlib import Path
import requests
import json

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.test import APIClient

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()


class LoadTestRunner:
    """负载测试运行器"""
    
    def __init__(self, base_url='http://127.0.0.1:8000'):
        self.base_url = base_url
        self.test_users = []
        self.response_times = []
        self.error_count = 0
        
    def setup_test_data(self):
        """准备测试数据"""
        logger.info("准备测试数据...")
        
        # 创建测试用户
        for i in range(20):
            username = f'load_test_user_{i}'
            try:
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@test.com',
                    password='testpass123',
                    role='user'
                )
                self.test_users.append(user)
            except:
                # 用户可能已存在
                try:
                    user = User.objects.get(username=username)
                    self.test_users.append(user)
                except:
                    pass
        
        logger.info(f"✓ 准备了 {len(self.test_users)} 个测试用户")
    
    def cleanup_test_data(self):
        """清理测试数据"""
        logger.info("清理测试数据...")
        User.objects.filter(username__startswith='load_test_user_').delete()
        logger.info("✓ 测试数据清理完成")
    
    def simulate_user_session(self, user_index):
        """模拟用户会话"""
        session_start = time.time()
        session_data = {
            'user_index': user_index,
            'requests': [],
            'errors': [],
            'total_time': 0
        }
        
        try:
            # 创建会话
            session = requests.Session()
            
            # 1. 用户登录
            login_start = time.time()
            login_response = session.post(f'{self.base_url}/api/auth/login/', json={
                'username': f'load_test_user_{user_index}',
                'password': 'testpass123'
            })
            login_time = time.time() - login_start
            
            session_data['requests'].append(('login', login_time, login_response.status_code))
            
            if login_response.status_code != 200:
                session_data['errors'].append(f'登录失败: {login_response.status_code}')
                return session_data
            
            # 获取认证令牌
            token = login_response.json().get('tokens', {}).get('access')
            if not token:
                session_data['errors'].append('未获取到认证令牌')
                return session_data
            
            headers = {'Authorization': f'Bearer {token}'}
            
            # 2. 获取视频列表
            list_start = time.time()
            list_response = session.get(f'{self.base_url}/api/videos/', headers=headers)
            list_time = time.time() - list_start
            
            session_data['requests'].append(('video_list', list_time, list_response.status_code))
            
            if list_response.status_code == 200:
                videos = list_response.json().get('results', [])
                
                # 3. 获取视频详情（如果有视频）
                if videos:
                    video_id = videos[0]['id']
                    detail_start = time.time()
                    detail_response = session.get(f'{self.base_url}/api/videos/{video_id}/', headers=headers)
                    detail_time = time.time() - detail_start
                    
                    session_data['requests'].append(('video_detail', detail_time, detail_response.status_code))
                
                # 4. 搜索视频
                search_start = time.time()
                search_response = session.get(f'{self.base_url}/api/videos/search/', 
                                            params={'q': '道德经'}, headers=headers)
                search_time = time.time() - search_start
                
                session_data['requests'].append(('video_search', search_time, search_response.status_code))
            
            # 5. 获取用户资料
            profile_start = time.time()
            profile_response = session.get(f'{self.base_url}/api/auth/profile/', headers=headers)
            profile_time = time.time() - profile_start
            
            session_data['requests'].append(('user_profile', profile_time, profile_response.status_code))
            
        except Exception as e:
            session_data['errors'].append(f'会话异常: {str(e)}')
        
        session_data['total_time'] = time.time() - session_start
        return session_data
    
    def run_concurrent_load_test(self, concurrent_users=10, duration_seconds=30):
        """运行并发负载测试"""
        logger.info(f"🚀 开始并发负载测试: {concurrent_users} 并发用户, {duration_seconds} 秒")
        
        results = []
        start_time = time.time()
        
        def run_user_load(user_index):
            """运行单个用户的负载测试"""
            user_results = []
            end_time = start_time + duration_seconds
            
            while time.time() < end_time:
                session_result = self.simulate_user_session(user_index % len(self.test_users))
                user_results.append(session_result)
                
                # 短暂休息
                time.sleep(0.1)
            
            return user_results
        
        # 并发执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(run_user_load, i) for i in range(concurrent_users)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    user_results = future.result()
                    results.extend(user_results)
                except Exception as e:
                    logger.error(f"用户负载测试失败: {e}")
        
        return results
    
    def analyze_results(self, results):
        """分析测试结果"""
        logger.info("📊 分析负载测试结果...")
        
        if not results:
            logger.error("没有测试结果可分析")
            return
        
        # 统计请求类型
        request_stats = {}
        total_requests = 0
        total_errors = 0
        
        for session in results:
            total_errors += len(session['errors'])
            
            for req_type, req_time, status_code in session['requests']:
                total_requests += 1
                
                if req_type not in request_stats:
                    request_stats[req_type] = {
                        'times': [],
                        'success_count': 0,
                        'error_count': 0
                    }
                
                request_stats[req_type]['times'].append(req_time)
                
                if 200 <= status_code < 300:
                    request_stats[req_type]['success_count'] += 1
                else:
                    request_stats[req_type]['error_count'] += 1
        
        # 输出统计结果
        logger.info("=" * 50)
        logger.info("📈 负载测试统计结果")
        logger.info("=" * 50)
        
        logger.info(f"总会话数: {len(results)}")
        logger.info(f"总请求数: {total_requests}")
        logger.info(f"总错误数: {total_errors}")
        logger.info(f"错误率: {total_errors/total_requests:.2%}" if total_requests > 0 else "错误率: N/A")
        
        logger.info("\n📋 各类请求统计:")
        for req_type, stats in request_stats.items():
            times = stats['times']
            if times:
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                max_time = max(times)
                min_time = min(times)
                
                success_rate = stats['success_count'] / (stats['success_count'] + stats['error_count'])
                
                logger.info(f"\n{req_type}:")
                logger.info(f"  - 请求数: {len(times)}")
                logger.info(f"  - 成功率: {success_rate:.2%}")
                logger.info(f"  - 平均响应时间: {avg_time:.3f}s")
                logger.info(f"  - 中位数响应时间: {median_time:.3f}s")
                logger.info(f"  - 最大响应时间: {max_time:.3f}s")
                logger.info(f"  - 最小响应时间: {min_time:.3f}s")
        
        # 性能评估
        logger.info("\n🎯 性能评估:")
        
        # 计算整体平均响应时间
        all_times = []
        for stats in request_stats.values():
            all_times.extend(stats['times'])
        
        if all_times:
            overall_avg = statistics.mean(all_times)
            logger.info(f"整体平均响应时间: {overall_avg:.3f}s")
            
            if overall_avg < 0.5:
                logger.info("✅ 性能优秀 (< 0.5s)")
            elif overall_avg < 1.0:
                logger.info("✅ 性能良好 (< 1.0s)")
            elif overall_avg < 2.0:
                logger.info("⚠️  性能一般 (< 2.0s)")
            else:
                logger.info("❌ 性能较差 (>= 2.0s)")
        
        # 错误率评估
        if total_requests > 0:
            error_rate = total_errors / total_requests
            if error_rate < 0.01:
                logger.info("✅ 错误率优秀 (< 1%)")
            elif error_rate < 0.05:
                logger.info("✅ 错误率良好 (< 5%)")
            elif error_rate < 0.10:
                logger.info("⚠️  错误率一般 (< 10%)")
            else:
                logger.info("❌ 错误率较高 (>= 10%)")
    
    def run_stress_test(self):
        """运行压力测试"""
        logger.info("🔥 开始压力测试...")
        
        stress_levels = [
            (5, 10),   # 5并发用户, 10秒
            (10, 15),  # 10并发用户, 15秒
            (20, 20),  # 20并发用户, 20秒
            (30, 10),  # 30并发用户, 10秒
        ]
        
        for concurrent_users, duration in stress_levels:
            logger.info(f"\n📊 压力级别: {concurrent_users} 并发用户, {duration} 秒")
            logger.info("-" * 40)
            
            results = self.run_concurrent_load_test(concurrent_users, duration)
            self.analyze_results(results)
            
            # 休息一下
            time.sleep(2)


class DatabasePerformanceTest:
    """数据库性能测试"""
    
    def __init__(self):
        self.query_times = []
    
    def test_query_performance(self):
        """测试查询性能"""
        logger.info("🗄️  测试数据库查询性能...")
        
        from django.db import connection
        from videos.models import Video, CompositionTask
        
        # 测试各种查询
        queries = [
            ("视频列表查询", lambda: list(Video.objects.all()[:20])),
            ("视频搜索查询", lambda: list(Video.objects.filter(title__icontains='道德经'))),
            ("分类筛选查询", lambda: list(Video.objects.filter(category='daoist_classic'))),
            ("合成任务查询", lambda: list(CompositionTask.objects.all()[:10])),
            ("用户视频查询", lambda: list(Video.objects.filter(uploader__role='admin'))),
        ]
        
        for query_name, query_func in queries:
            # 重置查询日志
            connection.queries_log.clear()
            
            start_time = time.time()
            try:
                result = query_func()
                query_time = time.time() - start_time
                query_count = len(connection.queries)
                
                logger.info(f"✓ {query_name}:")
                logger.info(f"  - 执行时间: {query_time:.3f}s")
                logger.info(f"  - SQL查询数: {query_count}")
                logger.info(f"  - 结果数量: {len(result) if hasattr(result, '__len__') else 'N/A'}")
                
                self.query_times.append(query_time)
                
            except Exception as e:
                logger.error(f"❌ {query_name} 失败: {e}")
        
        # 分析查询性能
        if self.query_times:
            avg_time = statistics.mean(self.query_times)
            max_time = max(self.query_times)
            
            logger.info(f"\n📊 数据库性能汇总:")
            logger.info(f"平均查询时间: {avg_time:.3f}s")
            logger.info(f"最慢查询时间: {max_time:.3f}s")
            
            if avg_time < 0.1:
                logger.info("✅ 数据库性能优秀")
            elif avg_time < 0.5:
                logger.info("✅ 数据库性能良好")
            else:
                logger.info("⚠️  数据库性能需要优化")


def main():
    """主函数"""
    logger.info("🚀 开始系统负载和性能测试")
    logger.info("=" * 60)
    
    # 检查服务器是否运行
    try:
        response = requests.get('http://127.0.0.1:8000/api/monitoring/health/', timeout=5)
        logger.info("✓ 服务器连接正常")
    except:
        logger.error("❌ 无法连接到服务器，请确保Django服务器正在运行")
        logger.info("请运行: python manage.py runserver")
        return False
    
    try:
        # 1. 负载测试
        load_tester = LoadTestRunner()
        load_tester.setup_test_data()
        
        # 运行基础负载测试
        logger.info("\n🔄 运行基础负载测试...")
        results = load_tester.run_concurrent_load_test(concurrent_users=5, duration_seconds=15)
        load_tester.analyze_results(results)
        
        # 运行压力测试
        load_tester.run_stress_test()
        
        # 2. 数据库性能测试
        logger.info("\n" + "=" * 60)
        db_tester = DatabasePerformanceTest()
        db_tester.test_query_performance()
        
        # 清理
        load_tester.cleanup_test_data()
        
        logger.info("\n🎉 负载和性能测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)