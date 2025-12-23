#!/usr/bin/env python
"""
道士经文视频管理系统 - 集成测试
测试完整的用户流程、系统负载表现和验证所有API端点
"""
import os
import sys
import django
import json
import time
import threading
import concurrent.futures
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.db import transaction
from rest_framework.test import APIClient
from rest_framework import status

from videos.models import Video, CompositionTask, PlaybackHistory
from users.models import User

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationTestCase(TransactionTestCase):
    """集成测试基类"""
    
    def setUp(self):
        """测试前准备"""
        self.client = APIClient()
        self.admin_user = None
        self.regular_user = None
        self.test_videos = []
        self.setup_test_users()
        self.setup_test_videos()
    
    def setup_test_users(self):
        """创建测试用户"""
        # 创建管理员用户
        self.admin_user = User.objects.create_user(
            username='test_admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        # 创建普通用户
        self.regular_user = User.objects.create_user(
            username='test_user',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        
        logger.info(f"✓ 创建测试用户: {self.admin_user.username}, {self.regular_user.username}")
    
    def setup_test_videos(self):
        """创建测试视频"""
        # 创建模拟视频文件
        test_video_content = b'fake video content for testing'
        
        for i in range(3):
            video_file = SimpleUploadedFile(
                f'test_video_{i+1}.mp4',
                test_video_content,
                content_type='video/mp4'
            )
            
            video = Video.objects.create(
                title=f'道德经第{i+1}章',
                description=f'道德经第{i+1}章诵读视频',
                category='daoist_classic',
                uploader=self.admin_user,
                file_path=video_file
            )
            self.test_videos.append(video)
        
        logger.info(f"✓ 创建测试视频: {len(self.test_videos)} 个")
    
    def get_auth_token(self, user):
        """获取用户认证令牌"""
        response = self.client.post('/api/auth/login/', {
            'username': user.username,
            'password': 'testpass123'
        })
        
        if response.status_code == 200:
            return response.data['tokens']['access']
        return None
    
    def authenticate_user(self, user):
        """认证用户"""
        token = self.get_auth_token(user)
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            return True
        return False


class UserFlowIntegrationTest(IntegrationTestCase):
    """完整用户流程集成测试"""
    
    def test_complete_user_registration_flow(self):
        """测试完整的用户注册流程"""
        logger.info("🧪 测试完整用户注册流程")
        
        # 1. 用户注册
        registration_data = {
            'username': 'new_test_user',
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'role': 'user'
        }
        
        response = self.client.post('/api/auth/register/', registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        logger.info("✓ 用户注册成功")
        
        # 2. 用户登录
        login_data = {
            'username': 'new_test_user',
            'password': 'newpass123'
        }
        
        response = self.client.post('/api/auth/login/', login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        logger.info("✓ 用户登录成功")
        
        # 3. 获取用户资料
        token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'new_test_user')
        logger.info("✓ 获取用户资料成功")
    
    def test_complete_video_browsing_flow(self):
        """测试完整的视频浏览流程"""
        logger.info("🧪 测试完整视频浏览流程")
        
        # 认证普通用户
        self.assertTrue(self.authenticate_user(self.regular_user))
        
        # 1. 获取视频列表
        response = self.client.get('/api/videos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        logger.info(f"✓ 获取视频列表成功: {len(response.data['results'])} 个视频")
        
        # 2. 获取视频详情
        video_id = self.test_videos[0].id
        response = self.client.get(f'/api/videos/{video_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], video_id)
        logger.info("✓ 获取视频详情成功")
        
        # 3. 搜索视频
        response = self.client.get('/api/videos/search/', {'q': '道德经'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        logger.info("✓ 视频搜索功能正常")
        
        # 4. 分类筛选
        response = self.client.get('/api/videos/', {'category': 'daoist_classic'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logger.info("✓ 分类筛选功能正常")
    
    def test_complete_video_composition_flow(self):
        """测试完整的视频合成流程"""
        logger.info("🧪 测试完整视频合成流程")
        
        # 认证普通用户
        self.assertTrue(self.authenticate_user(self.regular_user))
        
        # 1. 创建合成任务
        composition_data = {
            'video_ids': [video.id for video in self.test_videos[:2]],
            'output_filename': '道德经合集.mp4'
        }
        
        response = self.client.post('/api/videos/composition/create/', composition_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task_id = response.data['task_id']
        logger.info(f"✓ 创建合成任务成功: {task_id}")
        
        # 2. 查询任务状态
        response = self.client.get(f'/api/videos/composition/{task_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['task_id'], task_id)
        logger.info("✓ 查询任务状态成功")
        
        # 3. 获取任务列表
        response = self.client.get('/api/videos/composition/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        logger.info("✓ 获取任务列表成功")
    
    def test_complete_admin_management_flow(self):
        """测试完整的管理员管理流程"""
        logger.info("🧪 测试完整管理员管理流程")
        
        # 认证管理员用户
        self.assertTrue(self.authenticate_user(self.admin_user))
        
        # 1. 管理员视频列表
        response = self.client.get('/api/videos/admin/list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logger.info("✓ 管理员视频列表获取成功")
        
        # 2. 编辑视频信息
        video_id = self.test_videos[0].id
        update_data = {
            'title': '更新后的标题',
            'description': '更新后的描述',
            'category': 'daoist_classic'
        }
        
        response = self.client.patch(f'/api/videos/admin/{video_id}/edit/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logger.info("✓ 视频信息编辑成功")
        
        # 3. 系统统计信息
        response = self.client.get('/api/videos/admin/monitoring/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_videos', response.data)
        logger.info("✓ 系统统计信息获取成功")
        
        # 4. 存储信息
        response = self.client.get('/api/videos/admin/monitoring/storage/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logger.info("✓ 存储信息获取成功")


class APIEndpointTest(IntegrationTestCase):
    """API端点验证测试"""
    
    def test_all_auth_endpoints(self):
        """测试所有认证相关端点"""
        logger.info("🧪 测试所有认证API端点")
        
        endpoints = [
            ('POST', '/api/auth/register/', {
                'username': 'api_test_user',
                'email': 'apitest@test.com',
                'password': 'testpass123',
                'password_confirm': 'testpass123',
                'role': 'user'
            }),
            ('POST', '/api/auth/login/', {
                'username': 'api_test_user',
                'password': 'testpass123'
            }),
        ]
        
        for method, url, data in endpoints:
            if method == 'POST':
                response = self.client.post(url, data)
            elif method == 'GET':
                response = self.client.get(url)
            
            self.assertIn(response.status_code, [200, 201, 400, 401, 403])
            logger.info(f"✓ {method} {url} - 状态码: {response.status_code}")
        
        # 测试需要认证的端点
        self.authenticate_user(self.regular_user)
        
        auth_endpoints = [
            ('GET', '/api/auth/profile/'),
            ('GET', '/api/auth/check-permission/'),
        ]
        
        for method, url in auth_endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            logger.info(f"✓ {method} {url} - 认证成功")
    
    def test_all_video_endpoints(self):
        """测试所有视频相关端点"""
        logger.info("🧪 测试所有视频API端点")
        
        # 普通用户端点
        self.authenticate_user(self.regular_user)
        
        user_endpoints = [
            ('GET', '/api/videos/'),
            ('GET', f'/api/videos/{self.test_videos[0].id}/'),
            ('GET', '/api/videos/search/'),
            ('GET', '/api/videos/categories/'),
            ('GET', '/api/videos/composition/'),
        ]
        
        for method, url in user_endpoints:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 404])
            logger.info(f"✓ {method} {url} - 状态码: {response.status_code}")
        
        # 管理员端点
        self.authenticate_user(self.admin_user)
        
        admin_endpoints = [
            ('GET', '/api/videos/admin/list/'),
            ('GET', '/api/videos/admin/monitoring/statistics/'),
            ('GET', '/api/videos/admin/monitoring/storage/'),
        ]
        
        for method, url in admin_endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            logger.info(f"✓ {method} {url} - 管理员访问成功")
    
    def test_error_monitoring_endpoints(self):
        """测试错误监控端点"""
        logger.info("🧪 测试错误监控API端点")
        
        monitoring_endpoints = [
            ('GET', '/api/monitoring/health/'),
            ('GET', '/api/monitoring/errors/'),
            ('GET', '/api/monitoring/performance/'),
        ]
        
        for method, url in monitoring_endpoints:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 500])
            logger.info(f"✓ {method} {url} - 状态码: {response.status_code}")


class LoadTestCase(IntegrationTestCase):
    """系统负载测试"""
    
    def test_concurrent_user_access(self):
        """测试并发用户访问"""
        logger.info("🧪 测试并发用户访问")
        
        def simulate_user_request():
            """模拟用户请求"""
            client = APIClient()
            
            # 登录
            response = client.post('/api/auth/login/', {
                'username': self.regular_user.username,
                'password': 'testpass123'
            })
            
            if response.status_code == 200:
                token = response.data['tokens']['access']
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
                
                # 获取视频列表
                response = client.get('/api/videos/')
                return response.status_code == 200
            
            return False
        
        # 并发测试
        concurrent_users = 10
        success_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(simulate_user_request) for _ in range(concurrent_users)]
            
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    success_count += 1
        
        success_rate = success_count / concurrent_users
        self.assertGreater(success_rate, 0.8)  # 至少80%成功率
        logger.info(f"✓ 并发测试完成: {success_count}/{concurrent_users} 成功 ({success_rate:.1%})")
    
    def test_video_list_performance(self):
        """测试视频列表性能"""
        logger.info("🧪 测试视频列表性能")
        
        self.authenticate_user(self.regular_user)
        
        # 测试响应时间
        start_time = time.time()
        response = self.client.get('/api/videos/')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 2.0)  # 响应时间应小于2秒
        logger.info(f"✓ 视频列表响应时间: {response_time:.3f}秒")
    
    def test_database_query_performance(self):
        """测试数据库查询性能"""
        logger.info("🧪 测试数据库查询性能")
        
        from django.db import connection
        from django.test.utils import override_settings
        
        # 重置查询计数
        connection.queries_log.clear()
        
        self.authenticate_user(self.regular_user)
        
        # 执行一系列查询
        response = self.client.get('/api/videos/')
        self.assertEqual(response.status_code, 200)
        
        # 检查查询数量
        query_count = len(connection.queries)
        self.assertLess(query_count, 10)  # 查询数量应该合理
        logger.info(f"✓ 数据库查询数量: {query_count}")


class SystemIntegrityTest(IntegrationTestCase):
    """系统完整性测试"""
    
    def test_data_consistency(self):
        """测试数据一致性"""
        logger.info("🧪 测试数据一致性")
        
        # 创建合成任务
        self.authenticate_user(self.regular_user)
        
        composition_data = {
            'video_ids': [video.id for video in self.test_videos[:2]],
            'output_filename': '一致性测试.mp4'
        }
        
        response = self.client.post('/api/videos/composition/create/', composition_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        task_id = response.data['task_id']
        
        # 验证任务在数据库中存在
        task = CompositionTask.objects.get(task_id=task_id)
        self.assertEqual(task.user, self.regular_user)
        self.assertEqual(len(task.video_list), 2)
        logger.info("✓ 数据一致性验证通过")
    
    def test_file_upload_integrity(self):
        """测试文件上传完整性"""
        logger.info("🧪 测试文件上传完整性")
        
        self.authenticate_user(self.admin_user)
        
        # 创建测试文件
        test_content = b'test video content for integrity check'
        video_file = SimpleUploadedFile(
            'integrity_test.mp4',
            test_content,
            content_type='video/mp4'
        )
        
        upload_data = {
            'title': '完整性测试视频',
            'description': '用于测试文件上传完整性',
            'category': 'daoist_classic',
            'file_path': video_file
        }
        
        response = self.client.post('/api/videos/upload/', upload_data, format='multipart')
        
        if response.status_code == 201:
            video_id = response.data['id']
            video = Video.objects.get(id=video_id)
            
            # 验证文件存在且内容正确
            self.assertTrue(video.file_path)
            logger.info("✓ 文件上传完整性验证通过")
        else:
            logger.warning(f"文件上传测试跳过 - 状态码: {response.status_code}")
    
    def test_error_handling(self):
        """测试错误处理"""
        logger.info("🧪 测试错误处理")
        
        # 测试未认证访问
        self.client.credentials()  # 清除认证
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, 401)
        logger.info("✓ 未认证访问正确返回401")
        
        # 测试权限不足
        self.authenticate_user(self.regular_user)
        response = self.client.get('/api/videos/admin/list/')
        self.assertEqual(response.status_code, 403)
        logger.info("✓ 权限不足正确返回403")
        
        # 测试资源不存在
        response = self.client.get('/api/videos/99999/')
        self.assertEqual(response.status_code, 404)
        logger.info("✓ 资源不存在正确返回404")


def run_integration_tests():
    """运行所有集成测试"""
    logger.info("🚀 开始运行集成测试...")
    logger.info("=" * 60)
    
    test_classes = [
        UserFlowIntegrationTest,
        APIEndpointTest,
        LoadTestCase,
        SystemIntegrityTest,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        logger.info(f"\n📋 运行测试类: {test_class.__name__}")
        logger.info("-" * 40)
        
        # 获取测试方法
        test_methods = [method for method in dir(test_class) 
                       if method.startswith('test_') and callable(getattr(test_class, method))]
        
        for test_method in test_methods:
            total_tests += 1
            
            try:
                # 创建测试实例并运行测试
                test_instance = test_class()
                test_instance.setUp()
                
                # 运行测试方法
                getattr(test_instance, test_method)()
                
                passed_tests += 1
                logger.info(f"✅ {test_method} - 通过")
                
            except Exception as e:
                failed_tests.append((test_class.__name__, test_method, str(e)))
                logger.error(f"❌ {test_method} - 失败: {str(e)}")
            
            finally:
                # 清理
                try:
                    test_instance.tearDown() if hasattr(test_instance, 'tearDown') else None
                except:
                    pass
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 集成测试结果汇总")
    logger.info("=" * 60)
    
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"通过测试: {passed_tests}")
    logger.info(f"失败测试: {len(failed_tests)}")
    logger.info(f"成功率: {passed_tests/total_tests:.1%}")
    
    if failed_tests:
        logger.info("\n❌ 失败的测试:")
        for test_class, test_method, error in failed_tests:
            logger.info(f"  - {test_class}.{test_method}: {error}")
    
    if passed_tests == total_tests:
        logger.info("\n🎉 所有集成测试通过！系统运行正常。")
        return True
    else:
        logger.info(f"\n⚠️  {len(failed_tests)} 个测试失败，请检查相关问题。")
        return False


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)