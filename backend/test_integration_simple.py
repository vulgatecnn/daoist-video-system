#!/usr/bin/env python
"""
道士经文视频管理系统 - 简化集成测试
避免Unicode字符问题，专注于核心功能测试
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
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class SimpleIntegrationTest:
    """简化集成测试"""
    
    def __init__(self):
        self.client = APIClient()
        self.admin_user = None
        self.regular_user = None
        self.test_videos = []
        self.test_results = []
        
    def log_result(self, test_name, success, message=""):
        """记录测试结果"""
        status = "PASS" if success else "FAIL"
        log_msg = f"[{status}] {test_name}"
        if message:
            log_msg += f": {message}"
        
        if success:
            logger.info(log_msg)
        else:
            logger.error(log_msg)
        
        self.test_results.append({
            'name': test_name,
            'success': success,
            'message': message
        })
        
        return success
    
    def setup_test_users(self):
        """创建测试用户"""
        try:
            # 创建管理员用户
            self.admin_user, created = User.objects.get_or_create(
                username='test_admin',
                defaults={
                    'email': 'admin@test.com',
                    'role': 'admin'
                }
            )
            if created:
                self.admin_user.set_password('testpass123')
                self.admin_user.save()
            
            # 创建普通用户
            self.regular_user, created = User.objects.get_or_create(
                username='test_user',
                defaults={
                    'email': 'user@test.com',
                    'role': 'user'
                }
            )
            if created:
                self.regular_user.set_password('testpass123')
                self.regular_user.save()
            
            return self.log_result("用户创建", True, f"管理员: {self.admin_user.username}, 普通用户: {self.regular_user.username}")
            
        except Exception as e:
            return self.log_result("用户创建", False, str(e))
    
    def setup_test_videos(self):
        """创建测试视频"""
        try:
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
            
            return self.log_result("测试视频创建", True, f"创建了 {len(self.test_videos)} 个测试视频")
            
        except Exception as e:
            return self.log_result("测试视频创建", False, str(e))
    
    def get_auth_token(self, user):
        """获取用户认证令牌"""
        try:
            response = self.client.post('/api/auth/login/', {
                'username': user.username,
                'password': 'testpass123'
            })
            
            if response.status_code == 200:
                return response.data['tokens']['access']
            return None
        except:
            return None
    
    def authenticate_user(self, user):
        """认证用户"""
        token = self.get_auth_token(user)
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            return True
        return False
    
    def test_user_authentication(self):
        """测试用户认证"""
        try:
            # 测试用户登录
            response = self.client.post('/api/auth/login/', {
                'username': self.regular_user.username,
                'password': 'testpass123'
            })
            
            if response.status_code == 200 and 'tokens' in response.data:
                return self.log_result("用户认证", True, "登录成功，获得令牌")
            else:
                return self.log_result("用户认证", False, f"登录失败，状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("用户认证", False, str(e))
    
    def test_video_list_api(self):
        """测试视频列表API"""
        try:
            # 认证用户
            if not self.authenticate_user(self.regular_user):
                return self.log_result("视频列表API", False, "用户认证失败")
            
            # 获取视频列表
            response = self.client.get('/api/videos/')
            
            if response.status_code == 200:
                data = response.data
                if 'results' in data and len(data['results']) > 0:
                    return self.log_result("视频列表API", True, f"获取到 {len(data['results'])} 个视频")
                else:
                    return self.log_result("视频列表API", True, "API正常，但无视频数据")
            else:
                return self.log_result("视频列表API", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("视频列表API", False, str(e))
    
    def test_video_detail_api(self):
        """测试视频详情API"""
        try:
            if not self.test_videos:
                return self.log_result("视频详情API", False, "无测试视频")
            
            # 认证用户
            if not self.authenticate_user(self.regular_user):
                return self.log_result("视频详情API", False, "用户认证失败")
            
            # 获取视频详情
            video_id = self.test_videos[0].id
            response = self.client.get(f'/api/videos/{video_id}/')
            
            if response.status_code == 200:
                data = response.data
                if data.get('id') == video_id:
                    return self.log_result("视频详情API", True, f"获取视频详情成功，ID: {video_id}")
                else:
                    return self.log_result("视频详情API", False, "返回的视频ID不匹配")
            else:
                return self.log_result("视频详情API", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("视频详情API", False, str(e))
    
    def test_video_search_api(self):
        """测试视频搜索API"""
        try:
            # 认证用户
            if not self.authenticate_user(self.regular_user):
                return self.log_result("视频搜索API", False, "用户认证失败")
            
            # 搜索视频
            response = self.client.get('/api/videos/search/', {'q': '道德经'})
            
            if response.status_code == 200:
                data = response.data
                return self.log_result("视频搜索API", True, f"搜索成功，找到 {len(data.get('results', []))} 个结果")
            else:
                return self.log_result("视频搜索API", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("视频搜索API", False, str(e))
    
    def test_composition_task_creation(self):
        """测试合成任务创建"""
        try:
            if len(self.test_videos) < 2:
                return self.log_result("合成任务创建", False, "测试视频不足")
            
            # 认证用户
            if not self.authenticate_user(self.regular_user):
                return self.log_result("合成任务创建", False, "用户认证失败")
            
            # 创建合成任务
            composition_data = {
                'video_ids': [video.id for video in self.test_videos[:2]],
                'output_filename': '测试合成.mp4'
            }
            
            response = self.client.post('/api/videos/composition/create/', composition_data)
            
            if response.status_code == 201:
                task_id = response.data.get('task_id')
                return self.log_result("合成任务创建", True, f"任务创建成功，ID: {task_id}")
            else:
                return self.log_result("合成任务创建", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("合成任务创建", False, str(e))
    
    def test_admin_video_management(self):
        """测试管理员视频管理"""
        try:
            # 认证管理员
            if not self.authenticate_user(self.admin_user):
                return self.log_result("管理员视频管理", False, "管理员认证失败")
            
            # 获取管理员视频列表
            response = self.client.get('/api/videos/admin/list/')
            
            if response.status_code == 200:
                return self.log_result("管理员视频管理", True, "管理员视频列表获取成功")
            else:
                return self.log_result("管理员视频管理", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("管理员视频管理", False, str(e))
    
    def test_system_monitoring(self):
        """测试系统监控"""
        try:
            # 认证管理员
            if not self.authenticate_user(self.admin_user):
                return self.log_result("系统监控", False, "管理员认证失败")
            
            # 获取系统统计
            response = self.client.get('/api/videos/admin/monitoring/statistics/')
            
            if response.status_code == 200:
                data = response.data
                # 检查返回的数据结构
                if 'videos' in data and 'total' in data['videos']:
                    total_videos = data['videos']['total']
                    return self.log_result("系统监控", True, f"系统统计获取成功，总视频数: {total_videos}")
                else:
                    return self.log_result("系统监控", False, f"统计数据格式错误，实际返回: {list(data.keys())}")
            else:
                return self.log_result("系统监控", False, f"状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("系统监控", False, str(e))
    
    def test_error_handling(self):
        """测试错误处理"""
        try:
            # 测试未认证访问
            self.client.credentials()  # 清除认证
            response = self.client.get('/api/auth/profile/')
            
            if response.status_code == 401:
                return self.log_result("错误处理", True, "未认证访问正确返回401")
            else:
                return self.log_result("错误处理", False, f"未认证访问返回状态码: {response.status_code}")
                
        except Exception as e:
            return self.log_result("错误处理", False, str(e))
    
    def test_database_operations(self):
        """测试数据库操作"""
        try:
            # 统计数据
            total_videos = Video.objects.count()
            total_users = User.objects.count()
            total_tasks = CompositionTask.objects.count()
            
            return self.log_result("数据库操作", True, 
                                 f"视频: {total_videos}, 用户: {total_users}, 任务: {total_tasks}")
                
        except Exception as e:
            return self.log_result("数据库操作", False, str(e))
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始运行简化集成测试...")
        logger.info("=" * 50)
        
        # 运行测试
        tests = [
            self.setup_test_users,
            self.setup_test_videos,
            self.test_user_authentication,
            self.test_video_list_api,
            self.test_video_detail_api,
            self.test_video_search_api,
            self.test_composition_task_creation,
            self.test_admin_video_management,
            self.test_system_monitoring,
            self.test_error_handling,
            self.test_database_operations,
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log_result(test_func.__name__, False, f"测试异常: {str(e)}")
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        logger.info("\n" + "=" * 50)
        logger.info("集成测试报告")
        logger.info("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过测试: {passed_tests}")
        logger.info(f"失败测试: {failed_tests}")
        
        if total_tests > 0:
            success_rate = passed_tests / total_tests
            logger.info(f"成功率: {success_rate:.1%}")
        
        # 失败的测试
        if failed_tests > 0:
            logger.info("\n失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    logger.info(f"  - {result['name']}: {result['message']}")
        
        if failed_tests == 0:
            logger.info("\n所有测试通过！系统运行正常。")
            return True
        else:
            logger.info(f"\n{failed_tests} 个测试失败，请检查相关问题。")
            return False


def main():
    """主函数"""
    try:
        tester = SimpleIntegrationTest()
        success = tester.run_all_tests()
        return success
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)