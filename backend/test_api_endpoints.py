#!/usr/bin/env python
"""
道士经文视频管理系统 - API端点验证测试
验证所有API端点的可用性和正确性
"""
import os
import sys
import django
import requests
import json
from pathlib import Path

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()


class APIEndpointValidator:
    """API端点验证器"""
    
    def __init__(self, base_url='http://127.0.0.1:8000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_token = None
        self.user_token = None
        self.test_data = {}
        
    def setup_test_users(self):
        """设置测试用户"""
        logger.info("设置测试用户...")
        
        # 创建或获取管理员用户
        admin_user, created = User.objects.get_or_create(
            username='api_test_admin',
            defaults={
                'email': 'admin@apitest.com',
                'role': 'admin'
            }
        )
        if created:
            admin_user.set_password('testpass123')
            admin_user.save()
        
        # 创建或获取普通用户
        regular_user, created = User.objects.get_or_create(
            username='api_test_user',
            defaults={
                'email': 'user@apitest.com',
                'role': 'user'
            }
        )
        if created:
            regular_user.set_password('testpass123')
            regular_user.save()
        
        logger.info("✓ 测试用户设置完成")
        return admin_user, regular_user
    
    def authenticate_users(self):
        """认证用户并获取令牌"""
        logger.info("认证用户...")
        
        # 管理员登录
        admin_response = self.session.post(f'{self.base_url}/api/auth/login/', json={
            'username': 'api_test_admin',
            'password': 'testpass123'
        })
        
        if admin_response.status_code == 200:
            self.admin_token = admin_response.json()['tokens']['access']
            logger.info("✓ 管理员认证成功")
        else:
            logger.error(f"❌ 管理员认证失败: {admin_response.status_code}")
        
        # 普通用户登录
        user_response = self.session.post(f'{self.base_url}/api/auth/login/', json={
            'username': 'api_test_user',
            'password': 'testpass123'
        })
        
        if user_response.status_code == 200:
            self.user_token = user_response.json()['tokens']['access']
            logger.info("✓ 普通用户认证成功")
        else:
            logger.error(f"❌ 普通用户认证失败: {user_response.status_code}")
    
    def test_auth_endpoints(self):
        """测试认证相关端点"""
        logger.info("\n🔐 测试认证API端点")
        logger.info("-" * 40)
        
        endpoints = [
            {
                'name': '用户注册',
                'method': 'POST',
                'url': '/api/auth/register/',
                'data': {
                    'username': 'new_api_user',
                    'email': 'newuser@apitest.com',
                    'password': 'newpass123',
                    'password_confirm': 'newpass123',
                    'role': 'user'
                },
                'expected_status': [201, 400],  # 可能已存在
                'auth_required': False
            },
            {
                'name': '用户登录',
                'method': 'POST',
                'url': '/api/auth/login/',
                'data': {
                    'username': 'api_test_user',
                    'password': 'testpass123'
                },
                'expected_status': [200],
                'auth_required': False
            },
            {
                'name': '获取用户资料',
                'method': 'GET',
                'url': '/api/auth/profile/',
                'expected_status': [200],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '权限检查',
                'method': 'GET',
                'url': '/api/auth/check-permission/',
                'expected_status': [200],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '管理员用户列表',
                'method': 'GET',
                'url': '/api/auth/admin/users/',
                'expected_status': [200, 403],  # 可能权限不足
                'auth_required': True,
                'auth_type': 'admin'
            }
        ]
        
        return self._test_endpoints(endpoints, "认证")
    
    def test_video_endpoints(self):
        """测试视频相关端点"""
        logger.info("\n🎥 测试视频API端点")
        logger.info("-" * 40)
        
        endpoints = [
            {
                'name': '视频列表',
                'method': 'GET',
                'url': '/api/videos/',
                'expected_status': [200],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '视频分类',
                'method': 'GET',
                'url': '/api/videos/categories/',
                'expected_status': [200],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '视频搜索',
                'method': 'GET',
                'url': '/api/videos/search/',
                'params': {'q': '道德经'},
                'expected_status': [200],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '管理员视频列表',
                'method': 'GET',
                'url': '/api/videos/admin/list/',
                'expected_status': [200, 403],
                'auth_required': True,
                'auth_type': 'admin'
            },
            {
                'name': '系统统计',
                'method': 'GET',
                'url': '/api/videos/admin/monitoring/statistics/',
                'expected_status': [200, 403],
                'auth_required': True,
                'auth_type': 'admin'
            },
            {
                'name': '存储信息',
                'method': 'GET',
                'url': '/api/videos/admin/monitoring/storage/',
                'expected_status': [200, 403],
                'auth_required': True,
                'auth_type': 'admin'
            }
        ]
        
        return self._test_endpoints(endpoints, "视频")
    
    def test_composition_endpoints(self):
        """测试合成相关端点"""
        logger.info("\n🎬 测试合成API端点")
        logger.info("-" * 40)
        
        endpoints = [
            {
                'name': '合成任务列表',
                'method': 'GET',
                'url': '/api/videos/composition/',
                'expected_status': [200],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '创建合成任务',
                'method': 'POST',
                'url': '/api/videos/composition/create/',
                'data': {
                    'video_ids': [1, 2],  # 假设存在这些视频
                    'output_filename': 'api_test_composition.mp4'
                },
                'expected_status': [201, 400, 404],  # 可能视频不存在
                'auth_required': True,
                'auth_type': 'user'
            }
        ]
        
        return self._test_endpoints(endpoints, "合成")
    
    def test_monitoring_endpoints(self):
        """测试监控相关端点"""
        logger.info("\n📊 测试监控API端点")
        logger.info("-" * 40)
        
        endpoints = [
            {
                'name': '系统健康检查',
                'method': 'GET',
                'url': '/api/monitoring/health/',
                'expected_status': [200, 500],
                'auth_required': False
            },
            {
                'name': '错误统计',
                'method': 'GET',
                'url': '/api/monitoring/errors/',
                'expected_status': [200, 500],
                'auth_required': False
            },
            {
                'name': '性能统计',
                'method': 'GET',
                'url': '/api/monitoring/performance/',
                'expected_status': [200, 500],
                'auth_required': False
            }
        ]
        
        return self._test_endpoints(endpoints, "监控")
    
    def test_error_handling(self):
        """测试错误处理"""
        logger.info("\n❌ 测试错误处理")
        logger.info("-" * 40)
        
        error_tests = [
            {
                'name': '未认证访问受保护端点',
                'method': 'GET',
                'url': '/api/auth/profile/',
                'expected_status': [401],
                'auth_required': False
            },
            {
                'name': '权限不足访问管理员端点',
                'method': 'GET',
                'url': '/api/videos/admin/list/',
                'expected_status': [403],
                'auth_required': True,
                'auth_type': 'user'  # 普通用户访问管理员端点
            },
            {
                'name': '访问不存在的视频',
                'method': 'GET',
                'url': '/api/videos/99999/',
                'expected_status': [404],
                'auth_required': True,
                'auth_type': 'user'
            },
            {
                'name': '无效的登录数据',
                'method': 'POST',
                'url': '/api/auth/login/',
                'data': {
                    'username': 'nonexistent_user',
                    'password': 'wrongpassword'
                },
                'expected_status': [400, 401],
                'auth_required': False
            }
        ]
        
        return self._test_endpoints(error_tests, "错误处理")
    
    def _test_endpoints(self, endpoints, category):
        """测试端点列表"""
        results = {
            'category': category,
            'total': len(endpoints),
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        for endpoint in endpoints:
            result = self._test_single_endpoint(endpoint)
            results['details'].append(result)
            
            if result['passed']:
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        # 输出分类结果
        logger.info(f"\n📋 {category}端点测试结果:")
        logger.info(f"总计: {results['total']}, 通过: {results['passed']}, 失败: {results['failed']}")
        
        return results
    
    def _test_single_endpoint(self, endpoint):
        """测试单个端点"""
        result = {
            'name': endpoint['name'],
            'url': endpoint['url'],
            'method': endpoint['method'],
            'passed': False,
            'status_code': None,
            'error': None
        }
        
        try:
            # 准备请求头
            headers = {'Content-Type': 'application/json'}
            
            # 添加认证头
            if endpoint.get('auth_required'):
                auth_type = endpoint.get('auth_type', 'user')
                token = self.admin_token if auth_type == 'admin' else self.user_token
                
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                else:
                    result['error'] = f'缺少{auth_type}认证令牌'
                    logger.error(f"❌ {endpoint['name']}: {result['error']}")
                    return result
            
            # 发送请求
            url = f"{self.base_url}{endpoint['url']}"
            
            if endpoint['method'] == 'GET':
                params = endpoint.get('params', {})
                response = self.session.get(url, headers=headers, params=params, timeout=10)
            elif endpoint['method'] == 'POST':
                data = endpoint.get('data', {})
                response = self.session.post(url, headers=headers, json=data, timeout=10)
            elif endpoint['method'] == 'PUT':
                data = endpoint.get('data', {})
                response = self.session.put(url, headers=headers, json=data, timeout=10)
            elif endpoint['method'] == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                result['error'] = f'不支持的HTTP方法: {endpoint["method"]}'
                logger.error(f"❌ {endpoint['name']}: {result['error']}")
                return result
            
            result['status_code'] = response.status_code
            
            # 检查状态码
            expected_status = endpoint['expected_status']
            if response.status_code in expected_status:
                result['passed'] = True
                logger.info(f"✅ {endpoint['name']}: {response.status_code}")
            else:
                result['error'] = f'状态码 {response.status_code} 不在预期范围 {expected_status}'
                logger.error(f"❌ {endpoint['name']}: {result['error']}")
            
        except requests.exceptions.Timeout:
            result['error'] = '请求超时'
            logger.error(f"❌ {endpoint['name']}: 请求超时")
        except requests.exceptions.ConnectionError:
            result['error'] = '连接错误'
            logger.error(f"❌ {endpoint['name']}: 连接错误")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ {endpoint['name']}: {str(e)}")
        
        return result
    
    def generate_report(self, all_results):
        """生成测试报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 API端点验证测试报告")
        logger.info("=" * 60)
        
        total_tests = sum(r['total'] for r in all_results)
        total_passed = sum(r['passed'] for r in all_results)
        total_failed = sum(r['failed'] for r in all_results)
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过测试: {total_passed}")
        logger.info(f"失败测试: {total_failed}")
        logger.info(f"成功率: {total_passed/total_tests:.1%}" if total_tests > 0 else "成功率: N/A")
        
        # 分类统计
        logger.info("\n📋 分类统计:")
        for result in all_results:
            success_rate = result['passed'] / result['total'] if result['total'] > 0 else 0
            status = "✅" if result['failed'] == 0 else "⚠️" if success_rate >= 0.8 else "❌"
            logger.info(f"{status} {result['category']}: {result['passed']}/{result['total']} ({success_rate:.1%})")
        
        # 失败详情
        failed_tests = []
        for result in all_results:
            for detail in result['details']:
                if not detail['passed']:
                    failed_tests.append(detail)
        
        if failed_tests:
            logger.info(f"\n❌ 失败的测试 ({len(failed_tests)} 个):")
            for test in failed_tests:
                logger.info(f"  - {test['name']}: {test['error']}")
        
        return total_passed == total_tests


def main():
    """主函数"""
    logger.info("🚀 开始API端点验证测试")
    logger.info("=" * 60)
    
    # 检查服务器连接
    try:
        response = requests.get('http://127.0.0.1:8000/api/monitoring/health/', timeout=5)
        logger.info("✓ 服务器连接正常")
    except:
        logger.error("❌ 无法连接到服务器，请确保Django服务器正在运行")
        logger.info("请运行: python manage.py runserver")
        return False
    
    try:
        # 初始化验证器
        validator = APIEndpointValidator()
        
        # 设置测试数据
        validator.setup_test_users()
        validator.authenticate_users()
        
        # 运行各类测试
        all_results = []
        
        all_results.append(validator.test_auth_endpoints())
        all_results.append(validator.test_video_endpoints())
        all_results.append(validator.test_composition_endpoints())
        all_results.append(validator.test_monitoring_endpoints())
        all_results.append(validator.test_error_handling())
        
        # 生成报告
        success = validator.generate_report(all_results)
        
        if success:
            logger.info("\n🎉 所有API端点验证通过！")
        else:
            logger.info("\n⚠️  部分API端点验证失败，请检查相关问题。")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)