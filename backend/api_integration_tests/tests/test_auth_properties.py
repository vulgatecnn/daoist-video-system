"""
认证API属性测试模块

使用属性测试验证认证系统的正确性属性。
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import json
import time
from unittest.mock import patch, Mock
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_helpers import TestDataGenerator


# 测试数据生成策略
username_strategy = st.text(
    min_size=3, 
    max_size=20, 
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))
).filter(lambda x: x.isalnum() or '_' in x)

password_strategy = st.text(min_size=8, max_size=50)

# JWT令牌策略
jwt_token_strategy = st.text(
    min_size=50, 
    max_size=200,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_chars='.-_')
)


class AuthPropertiesTester:
    """认证属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """初始化认证属性测试器"""
        self.config = config
        self.base_url = config.get_base_url()
        self.client = APIClient(self.base_url)
    
    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()


@pytest.fixture
def config():
    """测试配置fixture"""
    return TestConfigManager()


@pytest.fixture
def auth_properties_tester(config):
    """认证属性测试器fixture"""
    tester = AuthPropertiesTester(config)
    yield tester
    tester.close()


# 属性 2: 认证令牌管理一致性
# 验证需求: 2.1, 2.2, 2.3, 2.6

@given(access_token=jwt_token_strategy, refresh_token=jwt_token_strategy)
@settings(max_examples=10, deadline=5000)
def test_property_token_management_consistency(access_token, refresh_token):
    """
    属性测试：认证令牌管理一致性
    
    **验证需求: 2.1, 2.2, 2.3, 2.6**
    
    对于任何有效的JWT令牌，当设置到客户端后，所有需要认证的请求
    都应该自动包含Authorization头，并且令牌应该能够正确管理。
    """
    # 创建API客户端
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    try:
        # 设置令牌
        client.set_auth_token(access_token, refresh_token, 3600)
        
        # 验证令牌被正确设置
        assert client.access_token == access_token
        assert client.refresh_token == refresh_token
        
        # 验证Authorization头被自动添加
        assert 'Authorization' in client.session.headers
        assert client.session.headers['Authorization'] == f'Bearer {access_token}'
        
        # 验证令牌过期检查功能
        assert not client.is_token_expired()  # 刚设置的令牌不应该过期
        
        # 清除令牌
        client.clear_auth()
        
        # 验证令牌被正确清除
        assert client.access_token is None
        assert client.refresh_token is None
        assert 'Authorization' not in client.session.headers
        
    finally:
        client.close()


def test_property_token_expiration_detection():
    """
    属性测试：令牌过期检测
    
    **验证需求: 2.4**
    
    令牌过期检测应该能够正确识别过期的令牌。
    """
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    try:
        # 测试没有令牌的情况
        assert client.is_token_expired() is True
        
        # 设置一个很短的过期时间（1秒）
        client.set_auth_token("test_token", "test_refresh", 1)
        
        # 立即检查应该没有过期
        assert client.is_token_expired() is False
        
        # 等待2秒后应该过期
        time.sleep(2)
        assert client.is_token_expired() is True
        
    finally:
        client.close()


def test_property_token_refresh_mechanism():
    """
    属性测试：令牌刷新机制可靠性
    
    **验证需求: 2.4, 2.5**
    
    令牌刷新机制应该能够可靠地工作。
    """
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    try:
        # 测试刷新方法存在
        assert hasattr(client, 'refresh_access_token')
        assert callable(client.refresh_access_token)
        
        # 测试没有刷新令牌时的行为
        client.clear_auth()
        result = client.refresh_access_token()
        assert result is False  # 没有刷新令牌应该返回False
        
    finally:
        client.close()


# 运行属性测试的主函数
if __name__ == "__main__":
    print("开始认证令牌管理属性测试...")
    
    # 运行基本的属性测试
    config = TestConfigManager()
    
    print("\n1. 测试令牌管理一致性...")
    try:
        # 手动运行一个简单的令牌管理测试
        client = APIClient(config.get_base_url())
        
        # 测试令牌设置和清除
        client.set_auth_token("test_access", "test_refresh", 3600)
        assert client.access_token == "test_access"
        assert 'Authorization' in client.session.headers
        
        client.clear_auth()
        assert client.access_token is None
        assert 'Authorization' not in client.session.headers
        
        print("✅ 令牌管理一致性测试通过")
        client.close()
        
    except Exception as e:
        print(f"❌ 令牌管理一致性测试失败: {str(e)}")
    
    print("\n2. 测试令牌过期检测...")
    try:
        client = APIClient(config.get_base_url())
        
        # 测试过期检测
        assert client.is_token_expired() is True  # 没有令牌应该返回True
        
        client.set_auth_token("test", "test", 3600)
        assert client.is_token_expired() is False  # 有效令牌应该返回False
        
        print("✅ 令牌过期检测测试通过")
        client.close()
        
    except Exception as e:
        print(f"❌ 令牌过期检测测试失败: {str(e)}")
    
    print("\n3. 测试令牌刷新机制...")
    try:
        client = APIClient(config.get_base_url())
        
        # 测试刷新机制
        assert hasattr(client, 'refresh_access_token')
        result = client.refresh_access_token()
        assert result is False  # 没有刷新令牌应该返回False
        
        print("✅ 令牌刷新机制测试通过")
        client.close()
        
    except Exception as e:
        print(f"❌ 令牌刷新机制测试失败: {str(e)}")
    
    print("\n属性测试完成。运行 'pytest test_auth_properties.py' 进行完整的属性测试。")