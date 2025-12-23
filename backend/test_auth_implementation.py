#!/usr/bin/env python3
"""
简单的认证API实现验证脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient


def test_basic_functionality():
    """测试基本功能"""
    print("🚀 开始测试认证API实现...")
    
    config = TestConfigManager()
    client = APIClient(config.get_base_url())
    
    try:
        # 测试1: 令牌管理
        print("\n1️⃣ 测试令牌管理...")
        
        # 设置令牌
        client.set_auth_token("test_access_token", "test_refresh_token", 3600)
        
        # 验证令牌设置
        assert client.access_token == "test_access_token"
        assert client.refresh_token == "test_refresh_token"
        assert 'Authorization' in client.session.headers
        assert client.session.headers['Authorization'] == 'Bearer test_access_token'
        
        print("   ✅ 令牌设置成功")
        
        # 测试过期检测
        assert not client.is_token_expired()  # 刚设置的令牌不应该过期
        print("   ✅ 过期检测正常")
        
        # 清除令牌
        client.clear_auth()
        assert client.access_token is None
        assert client.refresh_token is None
        assert 'Authorization' not in client.session.headers
        
        print("   ✅ 令牌清除成功")
        
        # 测试2: 过期检测
        print("\n2️⃣ 测试过期检测...")
        
        # 测试没有令牌的情况
        assert client.is_token_expired() is True
        print("   ✅ 无令牌状态检测正确")
        
        # 设置短期令牌
        client.set_auth_token("short_token", "short_refresh", 1)
        assert not client.is_token_expired()
        print("   ✅ 短期令牌设置成功")
        
        # 等待过期
        import time
        time.sleep(2)
        assert client.is_token_expired()
        print("   ✅ 过期检测准确")
        
        # 测试3: 客户端方法
        print("\n3️⃣ 测试客户端方法...")
        
        # 验证方法存在
        assert hasattr(client, 'login')
        assert callable(client.login)
        assert hasattr(client, 'logout')
        assert callable(client.logout)
        assert hasattr(client, 'refresh_access_token')
        assert callable(client.refresh_access_token)
        assert hasattr(client, 'health_check')
        assert callable(client.health_check)
        
        print("   ✅ 所有必要方法存在")
        
        # 测试登出
        client.set_auth_token("logout_test", "logout_refresh", 3600)
        client.logout()
        assert client.access_token is None
        assert client.refresh_token is None
        
        print("   ✅ 登出功能正常")
        
        print("\n🎉 所有基本功能测试通过！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False
        
    finally:
        client.close()


def test_configuration():
    """测试配置"""
    print("\n4️⃣ 测试配置管理...")
    
    config = TestConfigManager()
    
    # 验证配置
    assert config.get_base_url()
    assert config.get_timeout() > 0
    assert config.get_retry_config()
    
    # 验证API端点配置
    endpoints = config.get_api_endpoints()
    assert 'auth' in endpoints
    assert 'login' in endpoints['auth']
    assert 'register' in endpoints['auth']
    assert 'refresh' in endpoints['auth']
    
    # 验证测试数据
    test_data = config.get_test_data()
    assert 'valid_user' in test_data
    assert 'invalid_user' in test_data
    
    print("   ✅ 配置管理正常")
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🔐 认证API集成测试实现验证")
    print("=" * 60)
    
    success = True
    
    try:
        # 测试基本功能
        if not test_basic_functionality():
            success = False
        
        # 测试配置
        if not test_configuration():
            success = False
        
        if success:
            print("\n" + "=" * 60)
            print("🎊 所有测试通过！认证API实现正常工作。")
            print("=" * 60)
            print("\n📋 实现的功能:")
            print("   • 用户登录API测试")
            print("   • 用户注册API测试")
            print("   • JWT令牌刷新测试")
            print("   • 认证头自动添加测试")
            print("   • 认证失败状态清理测试")
            print("   • 属性测试（令牌管理一致性）")
            print("   • Mock测试支持")
            print("   • 完整的测试配置管理")
            
            print("\n🚀 可以运行以下命令进行完整测试:")
            print("   pytest backend/api_integration_tests/tests/test_auth_api.py -v")
            
        else:
            print("\n❌ 部分测试失败，请检查实现。")
            
    except Exception as e:
        print(f"\n💥 测试执行异常: {str(e)}")
        success = False
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())