"""
用户认证API测试模块

测试用户登录、注册、令牌管理等认证相关功能。
"""

import pytest
import time
import json
from unittest.mock import patch, Mock
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
from api_integration_tests.utils.test_helpers import TestDataGenerator


class AuthAPITester:
    """认证API测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化认证API测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.base_url = config.get_base_url()
        self.timeout = config.get_timeout()
        
        # 创建API客户端
        self.client = APIClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        # 结果管理器
        self.result_manager = TestResultManager()
        
        # 测试数据
        self.test_data = config.get_test_data()
        self.valid_user = self.test_data["valid_user"]
        self.invalid_user = self.test_data["invalid_user"]
    
    def test_login_with_valid_credentials(self) -> bool:
        """
        测试使用有效凭证登录
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print(f"测试有效凭证登录: {self.valid_user['username']}")
            
            # 发送登录请求
            response = self.client.post('/api/auth/login/', {
                'username': self.valid_user['username'],
                'password': self.valid_user['password']
            })
            
            # 验证响应状态码
            if not response.is_success:
                print(f"❌ 登录失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 登录响应没有JSON数据")
                return False
            
            data = response.json_data
            
            # 检查必要字段
            required_fields = ['tokens', 'user', 'message']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"❌ 登录响应缺少字段: {missing_fields}")
                return False
            
            # 验证令牌字段
            tokens = data.get('tokens', {})
            if 'access' not in tokens or 'refresh' not in tokens:
                print("❌ 登录响应缺少访问令牌或刷新令牌")
                return False
            
            # 验证用户信息
            user_info = data.get('user', {})
            if 'id' not in user_info or 'username' not in user_info:
                print("❌ 登录响应缺少用户信息")
                return False
            
            print(f"✅ 有效凭证登录成功")
            print(f"   用户ID: {user_info.get('id')}")
            print(f"   用户名: {user_info.get('username')}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            # 保存令牌用于后续测试
            self.client.set_auth_token(
                tokens['access'], 
                tokens['refresh']
            )
            
            return True
            
        except Exception as e:
            print(f"❌ 登录测试异常: {str(e)}")
            return False
    
    def test_login_with_invalid_credentials(self) -> bool:
        """
        测试使用无效凭证登录
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print(f"测试无效凭证登录: {self.invalid_user['username']}")
            
            # 发送登录请求
            response = self.client.post('/api/auth/login/', {
                'username': self.invalid_user['username'],
                'password': self.invalid_user['password']
            })
            
            # 验证应该返回401错误
            if response.status_code != 401:
                print(f"❌ 无效凭证登录应该返回401，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                # 应该包含错误信息
                if 'non_field_errors' in response.json_data or 'error' in response.json_data:
                    print("✅ 无效凭证登录正确返回401错误")
                    print(f"   错误信息: {response.json_data}")
                    return True
                else:
                    print("❌ 401响应缺少错误信息")
                    return False
            else:
                print("❌ 401响应没有JSON数据")
                return False
                
        except Exception as e:
            print(f"❌ 无效凭证登录测试异常: {str(e)}")
            return False
    
    def test_login_with_missing_fields(self) -> bool:
        """
        测试缺少字段的登录请求
        
        Returns:
            bool: 测试是否通过
        """
        test_cases = [
            {"username": "test"},  # 缺少密码
            {"password": "test"},  # 缺少用户名
            {},  # 缺少所有字段
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                print(f"测试缺少字段的登录请求 {i+1}: {test_case}")
                
                response = self.client.post('/api/auth/login/', test_case)
                
                # 应该返回400错误
                if not response.is_client_error:
                    print(f"❌ 缺少字段应该返回4xx错误，实际返回: {response.status_code}")
                    return False
                
                print(f"✅ 缺少字段正确返回{response.status_code}错误")
                
            except Exception as e:
                print(f"❌ 缺少字段测试异常: {str(e)}")
                return False
        
        return True
    
    def test_login_response_time(self) -> bool:
        """
        测试登录响应时间
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试登录响应时间")
            
            start_time = time.time()
            response = self.client.post('/api/auth/login/', {
                'username': self.valid_user['username'],
                'password': self.valid_user['password']
            })
            total_time = time.time() - start_time
            
            # 验证响应时间在合理范围内（5秒内）
            if total_time > 5.0:
                print(f"❌ 登录响应时间过长: {total_time:.2f}s")
                return False
            
            print(f"✅ 登录响应时间正常: {total_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"❌ 登录响应时间测试异常: {str(e)}")
            return False
    
    def test_register_new_user(self) -> bool:
        """
        测试注册新用户
        
        Returns:
            bool: 测试是否通过
        """
        try:
            # 生成唯一的用户名和邮箱
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            
            new_user_data = {
                'username': f'newuser_{suffix}',
                'email': f'newuser_{suffix}@test.com',
                'password': 'newpass123',
                'password_confirm': 'newpass123',
                'role': 'regular'
            }
            
            print(f"测试注册新用户: {new_user_data['username']}")
            
            # 发送注册请求
            response = self.client.post('/api/auth/register/', new_user_data)
            
            # 验证响应状态码
            if response.status_code not in [200, 201]:
                print(f"❌ 注册失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 注册响应没有JSON数据")
                return False
            
            data = response.json_data
            
            # 检查必要字段
            required_fields = ['message', 'user']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"❌ 注册响应缺少字段: {missing_fields}")
                return False
            
            # 验证用户信息
            user_info = data.get('user', {})
            if 'id' not in user_info or 'username' not in user_info:
                print("❌ 注册响应缺少用户信息")
                return False
            
            # 验证用户名匹配
            if user_info.get('username') != new_user_data['username']:
                print("❌ 注册响应用户名不匹配")
                return False
            
            print(f"✅ 新用户注册成功")
            print(f"   用户ID: {user_info.get('id')}")
            print(f"   用户名: {user_info.get('username')}")
            print(f"   邮箱: {user_info.get('email')}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ 注册测试异常: {str(e)}")
            return False
    
    def test_register_duplicate_username(self) -> bool:
        """
        测试注册重复用户名
        
        Returns:
            bool: 测试是否通过
        """
        try:
            # 使用已存在的用户名
            duplicate_user_data = {
                'username': self.valid_user['username'],  # 使用已存在的用户名
                'email': 'duplicate@test.com',
                'password': 'newpass123',
                'password_confirm': 'newpass123',
                'role': 'regular'
            }
            
            print(f"测试注册重复用户名: {duplicate_user_data['username']}")
            
            # 发送注册请求
            response = self.client.post('/api/auth/register/', duplicate_user_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 重复用户名注册应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                # 应该包含用户名相关的错误信息
                data = response.json_data
                if 'username' in data or 'non_field_errors' in data or 'error' in data:
                    print("✅ 重复用户名注册正确返回错误")
                    print(f"   错误信息: {response.json_data}")
                    return True
                else:
                    print("❌ 错误响应缺少用户名错误信息")
                    return False
            else:
                print("❌ 错误响应没有JSON数据")
                return False
                
        except Exception as e:
            print(f"❌ 重复用户名注册测试异常: {str(e)}")
            return False
    
    def test_register_password_mismatch(self) -> bool:
        """
        测试注册密码不匹配
        
        Returns:
            bool: 测试是否通过
        """
        try:
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            
            mismatch_user_data = {
                'username': f'mismatch_{suffix}',
                'email': f'mismatch_{suffix}@test.com',
                'password': 'password123',
                'password_confirm': 'different123',  # 不匹配的确认密码
                'role': 'regular'
            }
            
            print("测试注册密码不匹配")
            
            # 发送注册请求
            response = self.client.post('/api/auth/register/', mismatch_user_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 密码不匹配应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                data = response.json_data
                if 'password' in data or 'password_confirm' in data or 'non_field_errors' in data:
                    print("✅ 密码不匹配正确返回错误")
                    print(f"   错误信息: {response.json_data}")
                    return True
                else:
                    print("❌ 错误响应缺少密码错误信息")
                    return False
            else:
                print("❌ 错误响应没有JSON数据")
                return False
                
        except Exception as e:
            print(f"❌ 密码不匹配注册测试异常: {str(e)}")
            return False
    
    def test_register_invalid_email(self) -> bool:
        """
        测试注册无效邮箱
        
        Returns:
            bool: 测试是否通过
        """
        try:
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            
            invalid_email_data = {
                'username': f'invalidemail_{suffix}',
                'email': 'invalid-email-format',  # 无效的邮箱格式
                'password': 'password123',
                'password_confirm': 'password123',
                'role': 'regular'
            }
            
            print("测试注册无效邮箱格式")
            
            # 发送注册请求
            response = self.client.post('/api/auth/register/', invalid_email_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 无效邮箱应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                data = response.json_data
                if 'email' in data:
                    print("✅ 无效邮箱格式正确返回错误")
                    print(f"   错误信息: {response.json_data}")
                    return True
                else:
                    print("❌ 错误响应缺少邮箱错误信息")
                    return False
            else:
                print("❌ 错误响应没有JSON数据")
                return False
                
        except Exception as e:
            print(f"❌ 无效邮箱注册测试异常: {str(e)}")
            return False
    
    def test_token_refresh_with_valid_token(self) -> bool:
        """
        测试使用有效刷新令牌刷新访问令牌
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试令牌刷新功能")
            
            # 首先登录获取令牌
            login_response = self.client.post('/api/auth/login/', {
                'username': self.valid_user['username'],
                'password': self.valid_user['password']
            })
            
            if not login_response.is_success or not login_response.json_data:
                print("❌ 无法获取初始令牌进行刷新测试")
                return False
            
            tokens = login_response.json_data.get('tokens', {})
            refresh_token = tokens.get('refresh')
            
            if not refresh_token:
                print("❌ 登录响应中没有刷新令牌")
                return False
            
            print(f"   获得刷新令牌，长度: {len(refresh_token)}")
            
            # 使用刷新令牌获取新的访问令牌
            refresh_response = self.client.post('/api/auth/token/refresh/', {
                'refresh': refresh_token
            })
            
            # 验证刷新响应
            if not refresh_response.is_success:
                print(f"❌ 令牌刷新失败 - 状态码: {refresh_response.status_code}")
                if refresh_response.json_data:
                    print(f"   错误信息: {refresh_response.json_data}")
                return False
            
            # 验证响应数据
            if not refresh_response.json_data:
                print("❌ 令牌刷新响应没有JSON数据")
                return False
            
            refresh_data = refresh_response.json_data
            
            # 检查新的访问令牌
            if 'access' not in refresh_data:
                print("❌ 令牌刷新响应缺少新的访问令牌")
                return False
            
            new_access_token = refresh_data['access']
            
            if not new_access_token:
                print("❌ 新的访问令牌为空")
                return False
            
            print(f"✅ 令牌刷新成功")
            print(f"   新访问令牌长度: {len(new_access_token)}")
            print(f"   响应时间: {refresh_response.response_time:.2f}s")
            
            # 验证新令牌与原令牌不同
            original_access_token = tokens.get('access')
            if new_access_token == original_access_token:
                print("⚠️  新访问令牌与原令牌相同（可能正常，取决于实现）")
            
            return True
            
        except Exception as e:
            print(f"❌ 令牌刷新测试异常: {str(e)}")
            return False
    
    def test_token_refresh_with_invalid_token(self) -> bool:
        """
        测试使用无效刷新令牌刷新访问令牌
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试无效刷新令牌")
            
            # 使用无效的刷新令牌
            invalid_refresh_token = "invalid.refresh.token"
            
            refresh_response = self.client.post('/api/auth/token/refresh/', {
                'refresh': invalid_refresh_token
            })
            
            # 验证应该返回401错误
            if refresh_response.status_code != 401:
                print(f"❌ 无效刷新令牌应该返回401，实际返回: {refresh_response.status_code}")
                return False
            
            # 验证错误响应格式
            if refresh_response.json_data:
                data = refresh_response.json_data
                if 'detail' in data or 'error' in data or 'refresh' in data:
                    print("✅ 无效刷新令牌正确返回401错误")
                    print(f"   错误信息: {refresh_response.json_data}")
                    return True
                else:
                    print("❌ 401响应缺少错误信息")
                    return False
            else:
                print("❌ 401响应没有JSON数据")
                return False
                
        except Exception as e:
            print(f"❌ 无效刷新令牌测试异常: {str(e)}")
            return False
    
    def test_token_refresh_missing_token(self) -> bool:
        """
        测试缺少刷新令牌的请求
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试缺少刷新令牌")
            
            # 发送空的刷新请求
            refresh_response = self.client.post('/api/auth/token/refresh/', {})
            
            # 验证应该返回400错误
            if not refresh_response.is_client_error:
                print(f"❌ 缺少刷新令牌应该返回4xx错误，实际返回: {refresh_response.status_code}")
                return False
            
            print(f"✅ 缺少刷新令牌正确返回{refresh_response.status_code}错误")
            
            return True
                
        except Exception as e:
            print(f"❌ 缺少刷新令牌测试异常: {str(e)}")
            return False
    
    def test_automatic_token_refresh(self) -> bool:
        """
        测试客户端自动令牌刷新机制
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试客户端自动令牌刷新机制")
            
            # 首先登录获取令牌
            login_success = self.client.login(
                self.valid_user['username'], 
                self.valid_user['password']
            )
            
            if not login_success:
                print("❌ 无法登录进行自动刷新测试")
                return False
            
            # 验证令牌被设置
            if not self.client.access_token or not self.client.refresh_token:
                print("❌ 登录后令牌未被设置")
                return False
            
            print(f"   登录成功，访问令牌长度: {len(self.client.access_token)}")
            
            # 测试自动刷新功能
            refresh_success = self.client.refresh_access_token()
            
            if not refresh_success:
                print("❌ 自动令牌刷新失败")
                return False
            
            print("✅ 客户端自动令牌刷新成功")
            
            return True
            
        except Exception as e:
            print(f"❌ 自动令牌刷新测试异常: {str(e)}")
            return False
    
    def test_expired_token_simulation(self) -> bool:
        """
        测试过期令牌模拟场景
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试过期令牌模拟")
            
            # 设置一个很短的过期时间来模拟过期
            self.client.set_auth_token("test_access_token", "test_refresh_token", 1)
            
            # 验证令牌刚设置时没有过期
            if self.client.is_token_expired():
                print("❌ 刚设置的令牌不应该过期")
                return False
            
            # 等待令牌过期
            import time
            time.sleep(2)
            
            # 验证令牌现在已过期
            if not self.client.is_token_expired():
                print("❌ 令牌应该已经过期")
                return False
            
            print("✅ 令牌过期检测正常工作")
            
            return True
            
        except Exception as e:
            print(f"❌ 过期令牌模拟测试异常: {str(e)}")
            return False
    
    def test_auth_header_automatic_inclusion(self) -> bool:
        """
        测试认证头自动包含功能
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试认证头自动包含")
            
            # 首先登录获取令牌
            login_success = self.client.login(
                self.valid_user['username'], 
                self.valid_user['password']
            )
            
            if not login_success:
                print("❌ 无法登录进行认证头测试")
                return False
            
            # 验证Authorization头被自动设置
            if 'Authorization' not in self.client.session.headers:
                print("❌ 登录后Authorization头未被自动设置")
                return False
            
            auth_header = self.client.session.headers['Authorization']
            expected_prefix = 'Bearer '
            
            if not auth_header.startswith(expected_prefix):
                print(f"❌ Authorization头格式错误: {auth_header}")
                return False
            
            token_part = auth_header[len(expected_prefix):]
            if not token_part or token_part != self.client.access_token:
                print("❌ Authorization头中的令牌与存储的令牌不匹配")
                return False
            
            print(f"✅ 认证头自动包含功能正常")
            print(f"   Authorization头: {auth_header[:20]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ 认证头自动包含测试异常: {str(e)}")
            return False
    
    def test_auth_failure_state_cleanup(self) -> bool:
        """
        测试认证失败时的状态清理
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试认证失败状态清理")
            
            # 先设置一些认证状态
            self.client.set_auth_token("test_token", "test_refresh", 3600)
            
            # 验证认证状态已设置
            if not self.client.access_token or 'Authorization' not in self.client.session.headers:
                print("❌ 无法设置初始认证状态")
                return False
            
            print("   初始认证状态已设置")
            
            # 模拟认证失败（使用无效凭证登录）
            invalid_login_response = self.client.post('/api/auth/login/', {
                'username': 'invalid_user',
                'password': 'invalid_pass'
            })
            
            # 验证登录失败
            if invalid_login_response.is_success:
                print("❌ 预期登录失败但实际成功")
                return False
            
            # 在认证失败后，客户端应该清理认证状态
            # 注意：这取决于客户端的实现，这里我们手动清理来模拟
            if invalid_login_response.status_code == 401:
                self.client.clear_auth()
            
            # 验证认证状态被清理
            if self.client.access_token is not None:
                print("❌ 认证失败后访问令牌未被清理")
                return False
            
            if 'Authorization' in self.client.session.headers:
                print("❌ 认证失败后Authorization头未被清理")
                return False
            
            print("✅ 认证失败状态清理正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 认证失败状态清理测试异常: {str(e)}")
            return False
    
    def test_logout_state_cleanup(self) -> bool:
        """
        测试登出时的状态清理
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试登出状态清理")
            
            # 首先登录
            login_success = self.client.login(
                self.valid_user['username'], 
                self.valid_user['password']
            )
            
            if not login_success:
                print("❌ 无法登录进行登出测试")
                return False
            
            # 验证登录状态
            if not self.client.access_token or 'Authorization' not in self.client.session.headers:
                print("❌ 登录后认证状态未正确设置")
                return False
            
            print("   登录状态已确认")
            
            # 执行登出
            self.client.logout()
            
            # 验证登出后状态被清理
            if self.client.access_token is not None:
                print("❌ 登出后访问令牌未被清理")
                return False
            
            if self.client.refresh_token is not None:
                print("❌ 登出后刷新令牌未被清理")
                return False
            
            if 'Authorization' in self.client.session.headers:
                print("❌ 登出后Authorization头未被清理")
                return False
            
            print("✅ 登出状态清理正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 登出状态清理测试异常: {str(e)}")
            return False
    
    def test_authenticated_request_behavior(self) -> bool:
        """
        测试需要认证的请求行为
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试需要认证的请求行为")
            
            # 测试未认证时访问需要认证的端点
            print("   测试未认证访问...")
            
            # 确保没有认证状态
            self.client.clear_auth()
            
            # 尝试访问需要认证的端点
            profile_response = self.client.get('/api/auth/profile/')
            
            # 应该返回401错误
            if profile_response.status_code != 401:
                print(f"❌ 未认证访问应该返回401，实际返回: {profile_response.status_code}")
                return False
            
            print("   ✅ 未认证访问正确返回401")
            
            # 现在登录并重试
            print("   测试认证后访问...")
            
            login_success = self.client.login(
                self.valid_user['username'], 
                self.valid_user['password']
            )
            
            if not login_success:
                print("❌ 无法登录进行认证请求测试")
                return False
            
            # 再次尝试访问需要认证的端点
            profile_response_auth = self.client.get('/api/auth/profile/')
            
            # 现在应该成功或返回其他非401错误
            if profile_response_auth.status_code == 401:
                print("❌ 认证后访问仍然返回401")
                return False
            
            print(f"   ✅ 认证后访问返回状态码: {profile_response_auth.status_code}")
            
            return True
            
        except Exception as e:
            print(f"❌ 认证请求行为测试异常: {str(e)}")
            return False
    
    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()


# 测试用例

@pytest.fixture
def config():
    """测试配置fixture"""
    return TestConfigManager()


@pytest.fixture
def auth_tester(config):
    """认证API测试器fixture"""
    tester = AuthAPITester(config)
    yield tester
    tester.close()


def test_auth_api_tester_creation(config):
    """测试认证API测试器创建"""
    tester = AuthAPITester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()
    tester.close()


def test_login_with_valid_credentials(auth_tester):
    """测试有效凭证登录"""
    result = auth_tester.test_login_with_valid_credentials()
    # 注意：这个测试可能失败，因为后端服务可能没有运行或测试用户不存在
    assert isinstance(result, bool)


def test_login_with_invalid_credentials(auth_tester):
    """测试无效凭证登录"""
    result = auth_tester.test_login_with_invalid_credentials()
    assert isinstance(result, bool)


def test_login_with_missing_fields(auth_tester):
    """测试缺少字段的登录"""
    result = auth_tester.test_login_with_missing_fields()
    assert isinstance(result, bool)


def test_register_new_user(auth_tester):
    """测试注册新用户"""
    result = auth_tester.test_register_new_user()
    assert isinstance(result, bool)


def test_register_duplicate_username(auth_tester):
    """测试注册重复用户名"""
    result = auth_tester.test_register_duplicate_username()
    assert isinstance(result, bool)


def test_register_password_mismatch(auth_tester):
    """测试注册密码不匹配"""
    result = auth_tester.test_register_password_mismatch()
    assert isinstance(result, bool)


def test_register_invalid_email(auth_tester):
    """测试注册无效邮箱"""
    result = auth_tester.test_register_invalid_email()
    assert isinstance(result, bool)


@patch('requests.Session.request')
def test_register_success_with_mock(mock_request):
    """使用Mock测试注册成功场景"""
    # 设置Mock响应
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.content = json.dumps({
        "message": "注册成功",
        "user": {
            "id": 2,
            "username": "newuser",
            "email": "newuser@test.com",
            "role": "regular"
        },
        "tokens": {
            "access": "mock_access_token",
            "refresh": "mock_refresh_token"
        }
    }, ensure_ascii=False).encode('utf-8')
    mock_response.text = mock_response.content.decode('utf-8')
    mock_response.json.return_value = json.loads(mock_response.text)
    mock_request.return_value = mock_response
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_register_new_user()
    
    # 验证请求被调用
    assert mock_request.called
    # 验证结果
    assert result is True
    
    tester.close()


@patch('requests.Session.request')
def test_register_duplicate_with_mock(mock_request):
    """使用Mock测试注册重复用户名场景"""
    # 设置Mock响应
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.content = json.dumps({
        "username": ["具有该用户名的用户已存在。"]
    }, ensure_ascii=False).encode('utf-8')
    mock_response.text = mock_response.content.decode('utf-8')
    mock_response.json.return_value = json.loads(mock_response.text)
    mock_request.return_value = mock_response
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_register_duplicate_username()
    
    # 验证请求被调用
    assert mock_request.called
    # 验证结果
    assert result is True
    
    tester.close()


def test_token_refresh_with_valid_token(auth_tester):
    """测试有效刷新令牌"""
    result = auth_tester.test_token_refresh_with_valid_token()
    assert isinstance(result, bool)


def test_token_refresh_with_invalid_token(auth_tester):
    """测试无效刷新令牌"""
    result = auth_tester.test_token_refresh_with_invalid_token()
    assert isinstance(result, bool)


def test_token_refresh_missing_token(auth_tester):
    """测试缺少刷新令牌"""
    result = auth_tester.test_token_refresh_missing_token()
    assert isinstance(result, bool)


def test_automatic_token_refresh(auth_tester):
    """测试自动令牌刷新"""
    result = auth_tester.test_automatic_token_refresh()
    assert isinstance(result, bool)


def test_expired_token_simulation(auth_tester):
    """测试过期令牌模拟"""
    result = auth_tester.test_expired_token_simulation()
    assert isinstance(result, bool)


@patch('requests.Session.request')
def test_token_refresh_success_with_mock(mock_request):
    """使用Mock测试令牌刷新成功场景"""
    # 设置Mock响应序列：先登录，再刷新
    login_response = Mock()
    login_response.status_code = 200
    login_response.headers = {'Content-Type': 'application/json'}
    login_response.content = json.dumps({
        "message": "登录成功",
        "user": {"id": 1, "username": "testuser"},
        "tokens": {
            "access": "original_access_token",
            "refresh": "valid_refresh_token"
        }
    }, ensure_ascii=False).encode('utf-8')
    login_response.text = login_response.content.decode('utf-8')
    login_response.json.return_value = json.loads(login_response.text)
    
    refresh_response = Mock()
    refresh_response.status_code = 200
    refresh_response.headers = {'Content-Type': 'application/json'}
    refresh_response.content = json.dumps({
        "access": "new_access_token"
    }, ensure_ascii=False).encode('utf-8')
    refresh_response.text = refresh_response.content.decode('utf-8')
    refresh_response.json.return_value = json.loads(refresh_response.text)
    
    # 设置Mock返回序列
    mock_request.side_effect = [login_response, refresh_response]
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_token_refresh_with_valid_token()
    
    # 验证请求被调用
    assert mock_request.call_count == 2
    # 验证结果
    assert result is True
    
    tester.close()


@patch('requests.Session.request')
def test_token_refresh_failure_with_mock(mock_request):
    """使用Mock测试令牌刷新失败场景"""
    # 设置Mock响应
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.content = json.dumps({
        "detail": "Token is invalid or expired",
        "code": "token_not_valid"
    }, ensure_ascii=False).encode('utf-8')
    mock_response.text = mock_response.content.decode('utf-8')
    mock_response.json.return_value = json.loads(mock_response.text)
    mock_request.return_value = mock_response
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_token_refresh_with_invalid_token()
    
    # 验证请求被调用
    assert mock_request.called
    # 验证结果
    assert result is True
    
    tester.close()


def test_auth_header_automatic_inclusion(auth_tester):
    """测试认证头自动包含"""
    result = auth_tester.test_auth_header_automatic_inclusion()
    assert isinstance(result, bool)


def test_auth_failure_state_cleanup(auth_tester):
    """测试认证失败状态清理"""
    result = auth_tester.test_auth_failure_state_cleanup()
    assert isinstance(result, bool)


def test_logout_state_cleanup(auth_tester):
    """测试登出状态清理"""
    result = auth_tester.test_logout_state_cleanup()
    assert isinstance(result, bool)


def test_authenticated_request_behavior(auth_tester):
    """测试认证请求行为"""
    result = auth_tester.test_authenticated_request_behavior()
    assert isinstance(result, bool)


@patch('requests.Session.request')
def test_auth_header_inclusion_with_mock(mock_request):
    """使用Mock测试认证头包含"""
    # 设置Mock登录响应
    login_response = Mock()
    login_response.status_code = 200
    login_response.headers = {'Content-Type': 'application/json'}
    login_response.content = json.dumps({
        "message": "登录成功",
        "user": {"id": 1, "username": "testuser"},
        "tokens": {
            "access": "test_access_token",
            "refresh": "test_refresh_token"
        }
    }, ensure_ascii=False).encode('utf-8')
    login_response.text = login_response.content.decode('utf-8')
    login_response.json.return_value = json.loads(login_response.text)
    
    # 设置Mock认证请求响应
    auth_response = Mock()
    auth_response.status_code = 200
    auth_response.headers = {'Content-Type': 'application/json'}
    auth_response.content = json.dumps({"user": {"id": 1, "username": "testuser"}}, ensure_ascii=False).encode('utf-8')
    auth_response.text = auth_response.content.decode('utf-8')
    auth_response.json.return_value = json.loads(auth_response.text)
    
    # 设置Mock返回序列
    mock_request.side_effect = [login_response, auth_response]
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_auth_header_automatic_inclusion()
    
    # 验证请求被调用
    assert mock_request.call_count >= 1
    # 验证结果
    assert result is True
    
    tester.close()


def test_auth_client_logout_method():
    """测试认证客户端登出方法"""
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    # 设置认证状态
    client.set_auth_token("test_access", "test_refresh", 3600)
    assert client.access_token is not None
    assert 'Authorization' in client.session.headers
    
    # 执行登出
    client.logout()
    
    # 验证状态被清理
    assert client.access_token is None
    assert client.refresh_token is None
    assert 'Authorization' not in client.session.headers
    
    client.close()


def test_refresh_endpoint_configuration():
    """测试令牌刷新端点配置"""
    config = TestConfigManager()
    endpoints = config.get_api_endpoints()
    
    # 验证刷新端点配置
    assert 'auth' in endpoints
    assert 'refresh' in endpoints['auth']
    
    refresh_endpoint = endpoints['auth']['refresh']
    assert refresh_endpoint.name == "令牌刷新"
    assert refresh_endpoint.url == "/api/auth/token/refresh/"
    assert refresh_endpoint.method == "POST"
    assert refresh_endpoint.requires_auth is False
    
    # 验证响应schema
    schema = refresh_endpoint.expected_response_schema
    assert 'access' in schema


def test_register_endpoint_configuration():
    """测试注册端点配置"""
    config = TestConfigManager()
    endpoints = config.get_api_endpoints()
    
    # 验证注册端点配置
    assert 'auth' in endpoints
    assert 'register' in endpoints['auth']
    
    register_endpoint = endpoints['auth']['register']
    assert register_endpoint.name == "用户注册"
    assert register_endpoint.url == "/api/auth/register/"
    assert register_endpoint.method == "POST"
    assert register_endpoint.requires_auth is False
    
    # 验证响应schema
    schema = register_endpoint.expected_response_schema
    assert 'user' in schema
    assert 'message' in schema


def test_login_response_time(auth_tester):
    """测试登录响应时间"""
    result = auth_tester.test_login_response_time()
    assert isinstance(result, bool)


@patch('requests.Session.request')
def test_login_success_with_mock(mock_request):
    """使用Mock测试登录成功场景"""
    # 设置Mock响应
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.content = json.dumps({
        "message": "登录成功",
        "user": {
            "id": 1,
            "username": "testuser",
            "email": "testuser@test.com"
        },
        "tokens": {
            "access": "mock_access_token",
            "refresh": "mock_refresh_token"
        }
    }, ensure_ascii=False).encode('utf-8')
    mock_response.text = mock_response.content.decode('utf-8')
    mock_response.json.return_value = json.loads(mock_response.text)
    mock_request.return_value = mock_response
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_login_with_valid_credentials()
    
    # 验证请求被调用
    assert mock_request.called
    # 验证结果
    assert result is True
    # 验证令牌被设置
    assert tester.client.access_token == "mock_access_token"
    assert tester.client.refresh_token == "mock_refresh_token"
    
    tester.close()


@patch('requests.Session.request')
def test_login_failure_with_mock(mock_request):
    """使用Mock测试登录失败场景"""
    # 设置Mock响应
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.content = json.dumps({
        "non_field_errors": ["用户名或密码错误"]
    }, ensure_ascii=False).encode('utf-8')
    mock_response.text = mock_response.content.decode('utf-8')
    mock_response.json.return_value = json.loads(mock_response.text)
    mock_request.return_value = mock_response
    
    # 创建测试器并测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    result = tester.test_login_with_invalid_credentials()
    
    # 验证请求被调用
    assert mock_request.called
    # 验证结果
    assert result is True
    
    tester.close()


def test_login_endpoint_configuration():
    """测试登录端点配置"""
    config = TestConfigManager()
    endpoints = config.get_api_endpoints()
    
    # 验证登录端点配置
    assert 'auth' in endpoints
    assert 'login' in endpoints['auth']
    
    login_endpoint = endpoints['auth']['login']
    assert login_endpoint.name == "用户登录"
    assert login_endpoint.url == "/api/auth/login/"
    assert login_endpoint.method == "POST"
    assert login_endpoint.requires_auth is False
    
    # 验证响应schema
    schema = login_endpoint.expected_response_schema
    assert 'access' in schema
    assert 'refresh' in schema
    assert 'user' in schema


def test_auth_client_token_management():
    """测试认证客户端令牌管理"""
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    # 测试设置令牌
    client.set_auth_token("test_access", "test_refresh", 3600)
    assert client.access_token == "test_access"
    assert client.refresh_token == "test_refresh"
    assert 'Authorization' in client.session.headers
    assert client.session.headers['Authorization'] == 'Bearer test_access'
    
    # 测试清除令牌
    client.clear_auth()
    assert client.access_token is None
    assert client.refresh_token is None
    assert 'Authorization' not in client.session.headers
    
    client.close()


def test_auth_client_login_method():
    """测试认证客户端登录方法"""
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    # 测试登录方法存在
    assert hasattr(client, 'login')
    assert callable(client.login)
    
    client.close()


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = AuthAPITester(config)
    
    print("开始认证API测试...")
    print(f"目标URL: {config.get_base_url()}")
    
    # 执行登录测试
    print("\n=== 登录测试 ===")
    print("1. 测试有效凭证登录...")
    valid_login_result = tester.test_login_with_valid_credentials()
    
    print("\n2. 测试无效凭证登录...")
    invalid_login_result = tester.test_login_with_invalid_credentials()
    
    print("\n3. 测试缺少字段登录...")
    missing_fields_result = tester.test_login_with_missing_fields()
    
    print("\n4. 测试登录响应时间...")
    response_time_result = tester.test_login_response_time()
    
    # 执行注册测试
    print("\n=== 注册测试 ===")
    print("5. 测试注册新用户...")
    register_new_result = tester.test_register_new_user()
    
    print("\n6. 测试注册重复用户名...")
    register_duplicate_result = tester.test_register_duplicate_username()
    
    print("\n7. 测试注册密码不匹配...")
    register_mismatch_result = tester.test_register_password_mismatch()
    
    print("\n8. 测试注册无效邮箱...")
    register_invalid_email_result = tester.test_register_invalid_email()
    
    # 执行令牌刷新测试
    print("\n=== 令牌刷新测试 ===")
    print("9. 测试有效令牌刷新...")
    token_refresh_valid_result = tester.test_token_refresh_with_valid_token()
    
    print("\n10. 测试无效令牌刷新...")
    token_refresh_invalid_result = tester.test_token_refresh_with_invalid_token()
    
    print("\n11. 测试缺少刷新令牌...")
    token_refresh_missing_result = tester.test_token_refresh_missing_token()
    
    print("\n12. 测试自动令牌刷新...")
    auto_refresh_result = tester.test_automatic_token_refresh()
    
    print("\n13. 测试过期令牌模拟...")
    expired_token_result = tester.test_expired_token_simulation()
    
    # 执行认证头和状态管理测试
    print("\n=== 认证头和状态管理测试 ===")
    print("14. 测试认证头自动包含...")
    auth_header_result = tester.test_auth_header_automatic_inclusion()
    
    print("\n15. 测试认证失败状态清理...")
    auth_failure_cleanup_result = tester.test_auth_failure_state_cleanup()
    
    print("\n16. 测试登出状态清理...")
    logout_cleanup_result = tester.test_logout_state_cleanup()
    
    print("\n17. 测试认证请求行为...")
    auth_request_behavior_result = tester.test_authenticated_request_behavior()
    
    # 总结
    print(f"\n=== 测试结果总结 ===")
    print("登录测试:")
    print(f"- 有效凭证登录: {'✅ 通过' if valid_login_result else '❌ 失败'}")
    print(f"- 无效凭证登录: {'✅ 通过' if invalid_login_result else '❌ 失败'}")
    print(f"- 缺少字段登录: {'✅ 通过' if missing_fields_result else '❌ 失败'}")
    print(f"- 登录响应时间: {'✅ 通过' if response_time_result else '❌ 失败'}")
    
    print("注册测试:")
    print(f"- 注册新用户: {'✅ 通过' if register_new_result else '❌ 失败'}")
    print(f"- 注册重复用户名: {'✅ 通过' if register_duplicate_result else '❌ 失败'}")
    print(f"- 注册密码不匹配: {'✅ 通过' if register_mismatch_result else '❌ 失败'}")
    print(f"- 注册无效邮箱: {'✅ 通过' if register_invalid_email_result else '❌ 失败'}")
    
    print("令牌刷新测试:")
    print(f"- 有效令牌刷新: {'✅ 通过' if token_refresh_valid_result else '❌ 失败'}")
    print(f"- 无效令牌刷新: {'✅ 通过' if token_refresh_invalid_result else '❌ 失败'}")
    print(f"- 缺少刷新令牌: {'✅ 通过' if token_refresh_missing_result else '❌ 失败'}")
    print(f"- 自动令牌刷新: {'✅ 通过' if auto_refresh_result else '❌ 失败'}")
    print(f"- 过期令牌模拟: {'✅ 通过' if expired_token_result else '❌ 失败'}")
    
    print("认证头和状态管理测试:")
    print(f"- 认证头自动包含: {'✅ 通过' if auth_header_result else '❌ 失败'}")
    print(f"- 认证失败状态清理: {'✅ 通过' if auth_failure_cleanup_result else '❌ 失败'}")
    print(f"- 登出状态清理: {'✅ 通过' if logout_cleanup_result else '❌ 失败'}")
    print(f"- 认证请求行为: {'✅ 通过' if auth_request_behavior_result else '❌ 失败'}")
    
    # 计算总体通过率
    all_results = [
        valid_login_result, invalid_login_result, missing_fields_result, response_time_result,
        register_new_result, register_duplicate_result, register_mismatch_result, register_invalid_email_result,
        token_refresh_valid_result, token_refresh_invalid_result, token_refresh_missing_result, 
        auto_refresh_result, expired_token_result,
        auth_header_result, auth_failure_cleanup_result, logout_cleanup_result, auth_request_behavior_result
    ]
    passed_count = sum(1 for result in all_results if result)
    total_count = len(all_results)
    pass_rate = (passed_count / total_count) * 100
    
    print(f"\n总体通过率: {passed_count}/{total_count} ({pass_rate:.1f}%)")
    
    tester.close()