"""
pytest配置文件

定义测试夹具(fixtures)和全局配置。
"""

import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.test_helpers import (
    TestDataGenerator, TestFileManager, TestLogger
)


@pytest.fixture(scope="session")
def test_config():
    """测试配置夹具"""
    return TestConfigManager()


@pytest.fixture(scope="session")
def test_logger():
    """测试日志记录器夹具"""
    logger = TestLogger("api_integration_test.log")
    yield logger
    # 测试结束后保存日志
    logger.save_to_file()


@pytest.fixture(scope="function")
def test_data_generator():
    """测试数据生成器夹具"""
    return TestDataGenerator()


@pytest.fixture(scope="function")
def test_file_manager():
    """测试文件管理器夹具"""
    manager = TestFileManager()
    yield manager
    # 测试结束后清理文件
    manager.cleanup_test_files()


@pytest.fixture(scope="session")
def api_endpoints(test_config):
    """API端点配置夹具"""
    return test_config.get_api_endpoints()


@pytest.fixture(scope="session")
def test_data(test_config):
    """测试数据夹具"""
    return test_config.get_test_data()


@pytest.fixture(scope="session")
def base_url(test_config):
    """API基础URL夹具"""
    return test_config.get_base_url()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """自动设置测试环境"""
    # 设置测试环境变量
    os.environ["DJANGO_SETTINGS_MODULE"] = "daoist_video_system.settings"
    os.environ["TESTING"] = "1"
    
    yield
    
    # 测试后清理（如果需要）
    pass


def pytest_configure(config):
    """pytest配置钩子"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "api: API相关测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "property: 属性测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集项"""
    # 为没有标记的测试添加默认标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


def pytest_runtest_setup(item):
    """测试运行前的设置"""
    # 检查网络标记的测试是否需要跳过
    if item.get_closest_marker("network"):
        # 这里可以添加网络连接检查逻辑
        pass


def pytest_runtest_teardown(item, nextitem):
    """测试运行后的清理"""
    # 这里可以添加测试后的清理逻辑
    pass


@pytest.fixture(scope="session")
def django_setup():
    """Django环境设置夹具"""
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daoist_video_system.settings")
        django.setup()
    
    # 创建测试数据库
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
    
    yield
    
    # 清理测试数据库（如果需要）
    pass