#!/usr/bin/env python
"""
验证API集成测试框架

简单验证脚本，确保所有组件都能正常工作。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试导入"""
    print("🔍 测试模块导入...")
    
    try:
        from api_integration_tests.config.test_config import TestConfigManager
        print("✅ TestConfigManager 导入成功")
        
        from api_integration_tests.utils.http_client import APIClient
        print("✅ APIClient 导入成功")
        
        from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
        print("✅ TestResultManager 导入成功")
        
        from api_integration_tests.config.env_config import EnvironmentConfig
        print("✅ EnvironmentConfig 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_config_manager():
    """测试配置管理器"""
    print("\n🔍 测试配置管理器...")
    
    try:
        from api_integration_tests.config.test_config import TestConfigManager
        
        config = TestConfigManager()
        assert config.get_base_url() == "http://localhost:6000"
        assert config.get_timeout() == 30
        
        endpoints = config.get_api_endpoints()
        assert "auth" in endpoints
        assert "videos" in endpoints
        
        test_data = config.get_test_data()
        assert "valid_user" in test_data
        
        print("✅ 配置管理器测试通过")
        return True
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

def test_http_client():
    """测试HTTP客户端"""
    print("\n🔍 测试HTTP客户端...")
    
    try:
        from api_integration_tests.utils.http_client import APIClient
        
        client = APIClient("http://localhost:6000")
        assert client.base_url == "http://localhost:6000"
        assert client.timeout == 30
        
        # 测试URL构建
        url = client._build_url("/api/test")
        assert url == "http://localhost:6000/api/test"
        
        print("✅ HTTP客户端测试通过")
        return True
    except Exception as e:
        print(f"❌ HTTP客户端测试失败: {e}")
        return False

def test_result_manager():
    """测试结果管理器"""
    print("\n🔍 测试结果管理器...")
    
    try:
        from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
        
        manager = TestResultManager()
        
        # 开始测试套件
        suite = manager.start_suite("测试套件")
        assert suite.name == "测试套件"
        
        # 添加测试结果
        result = manager.add_passed_test("测试1", 1.0, "成功")
        assert result.status == TestStatus.PASS
        
        # 结束测试套件
        completed_suite = manager.end_suite()
        assert completed_suite.total_tests == 1
        assert completed_suite.passed_tests == 1
        
        print("✅ 结果管理器测试通过")
        return True
    except Exception as e:
        print(f"❌ 结果管理器测试失败: {e}")
        return False

def test_environment_config():
    """测试环境配置"""
    print("\n🔍 测试环境配置...")
    
    try:
        from api_integration_tests.config.env_config import EnvironmentConfig
        
        env_config = EnvironmentConfig()
        
        backend_config = env_config.get_backend_config()
        assert backend_config.base_url == "http://localhost:6000"
        
        api_config = env_config.get_api_config()
        assert api_config["timeout"] == 30
        
        print("✅ 环境配置测试通过")
        return True
    except Exception as e:
        print(f"❌ 环境配置测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始验证API集成测试框架")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_manager,
        test_http_client,
        test_result_manager,
        test_environment_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！API集成测试框架搭建成功！")
        return 0
    else:
        print("❌ 部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())