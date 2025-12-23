"""
测试框架验证

验证测试基础框架是否正常工作。
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
from api_integration_tests.config.env_config import EnvironmentConfig


def test_config_manager_creation():
    """测试配置管理器创建"""
    config = TestConfigManager()
    assert config is not None
    assert config.get_base_url() == "http://localhost:6000"
    assert config.get_timeout() == 30


def test_http_client_creation():
    """测试HTTP客户端创建"""
    client = APIClient("http://localhost:6000")
    assert client is not None
    assert client.base_url == "http://localhost:6000"
    assert client.timeout == 30


def test_result_manager_creation():
    """测试结果管理器创建"""
    manager = TestResultManager()
    assert manager is not None
    assert manager.output_dir.name == "test_results"


def test_environment_config_creation():
    """测试环境配置创建"""
    env_config = EnvironmentConfig()
    assert env_config is not None
    
    backend_config = env_config.get_backend_config()
    assert backend_config.base_url == "http://localhost:6000"


def test_test_result_operations():
    """测试测试结果操作"""
    manager = TestResultManager()
    
    # 开始测试套件
    suite = manager.start_suite("测试套件")
    assert suite is not None
    assert suite.name == "测试套件"
    
    # 添加测试结果
    result = manager.add_passed_test("测试1", 1.0, "成功")
    assert result.status == TestStatus.PASS
    assert result.duration == 1.0
    
    # 结束测试套件
    completed_suite = manager.end_suite()
    assert completed_suite is not None
    assert completed_suite.total_tests == 1
    assert completed_suite.passed_tests == 1


def test_api_endpoints_config():
    """测试API端点配置"""
    config = TestConfigManager()
    endpoints = config.get_api_endpoints()
    
    assert "auth" in endpoints
    assert "videos" in endpoints
    assert "composition" in endpoints
    assert "monitoring" in endpoints
    
    # 检查登录端点
    login_endpoint = endpoints["auth"]["login"]
    assert login_endpoint.name == "用户登录"
    assert login_endpoint.url == "/api/auth/login/"
    assert login_endpoint.method == "POST"
    assert not login_endpoint.requires_auth


def test_test_data_config():
    """测试测试数据配置"""
    config = TestConfigManager()
    test_data = config.get_test_data()
    
    assert "valid_user" in test_data
    assert "admin_user" in test_data
    assert "invalid_user" in test_data
    assert "test_video" in test_data
    
    valid_user = test_data["valid_user"]
    assert "username" in valid_user
    assert "password" in valid_user
    assert "email" in valid_user