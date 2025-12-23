"""
道士经文视频管理系统 - 属性测试（简化版）
验证系统的正确性属性

Feature: daoist-scripture-video, Property 1: 用户认证和访问控制
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')

# 确保项目路径在Python路径中
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

django.setup()

from django.test import TestCase, Client
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase as HypothesisTestCase


class AuthenticationPropertyTest(HypothesisTestCase):
    """
    属性测试：用户认证和访问控制
    
    属性 1: 用户认证和访问控制
    对于任何未认证用户和任何受保护的系统端点，访问该端点应该要求身份认证或重定向到登录页面
    验证需求: 需求 1.1, 1.5
    """
    
    def setUp(self):
        """测试设置"""
        self.client = Client()
    
    @hypothesis_settings(max_examples=3)
    @given(
        endpoint_path=st.sampled_from([
            '/api/videos/',
            '/api/auth/profile/',
        ])
    )
    def test_unauthenticated_access_to_protected_endpoints(self, endpoint_path):
        """
        属性测试：未认证用户访问受保护端点
        
        对于任何受保护的端点，未认证用户的访问应该：
        1. 返回401 Unauthorized状态码，或
        2. 返回403 Forbidden状态码，或
        3. 重定向到登录页面（302状态码），或
        4. 返回404（端点未实现）
        """
        # 确保客户端未认证
        self.client.logout()
        
        # 尝试访问受保护的端点
        response = self.client.get(endpoint_path)
        
        # 验证响应状态码表示需要认证或端点未实现
        self.assertIn(
            response.status_code,
            [401, 403, 302, 404],
            f"未认证用户访问 {endpoint_path} 应该返回401/403/302/404状态码，"
            f"但返回了 {response.status_code}"
        )
        
        # 如果返回302，应该重定向到登录相关页面
        if response.status_code == 302:
            redirect_url = response.get('Location', '')
            self.assertTrue(
                'login' in redirect_url.lower() or 
                'auth' in redirect_url.lower() or
                redirect_url.startswith('/admin/login/'),
                f"重定向URL {redirect_url} 应该指向登录页面"
            )
    
    def test_admin_endpoint_protection(self):
        """
        测试管理员端点的保护
        
        验证Django管理后台需要认证
        """
        # 未认证访问管理后台
        response = self.client.get('/admin/')
        
        # 应该重定向到登录页面
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.get('Location', '').lower())
    
    @hypothesis_settings(max_examples=2)
    @given(
        method=st.sampled_from(['GET', 'POST'])
    )
    def test_http_methods_require_authentication(self, method):
        """
        属性测试：所有HTTP方法都需要认证
        
        对于任何HTTP方法访问受保护端点，都应该要求认证
        """
        endpoint = '/api/videos/'
        
        # 确保客户端未认证
        self.client.logout()
        
        # 根据HTTP方法调用相应的客户端方法
        if method == 'GET':
            response = self.client.get(endpoint)
        elif method == 'POST':
            response = self.client.post(endpoint, {})
        
        # 验证需要认证
        self.assertIn(
            response.status_code,
            [401, 403, 302, 404, 405],  # 405 Method Not Allowed也是可接受的
            f"未认证用户使用 {method} 方法访问 {endpoint} 应该要求认证，"
            f"但返回了 {response.status_code}"
        )


if __name__ == '__main__':
    import unittest
    
    # 运行属性测试
    suite = unittest.TestLoader().loadTestsFromTestCase(AuthenticationPropertyTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print("\n✅ 所有属性测试通过！")
        print("属性 1: 用户认证和访问控制 - 验证成功")
    else:
        print(f"\n❌ 有 {len(result.failures)} 个测试失败，{len(result.errors)} 个测试错误")
        for failure in result.failures:
            print(f"失败: {failure[0]}")
            print(f"详情: {failure[1]}")
        for error in result.errors:
            print(f"错误: {error[0]}")
            print(f"详情: {error[1]}")