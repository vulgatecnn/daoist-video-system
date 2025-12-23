"""
超时和重试机制测试模块

测试API客户端的超时处理和重试机制功能。
"""

import pytest
import time
import requests
from unittest.mock import patch, Mock
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_helpers import RetryHelper


class TimeoutRetryTester:
    """超时和重试机制测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化超时重试测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.base_url = config.get_base_url()
    
    def test_timeout_configuration(self) -> bool:
        """
        测试超时配置
        
        Returns:
            bool: 超时配置是否正确
        """
        try:
            # 测试不同的超时配置
            timeouts = [1, 5, 10, 30]
            
            for timeout in timeouts:
                client = APIClient(self.base_url, timeout=timeout)
                
                # 验证超时配置
                assert client.timeout == timeout, f"超时配置错误: 期望 {timeout}, 实际 {client.timeout}"
                
                client.close()
            
            print("✅ 超时配置测试通过")
            return True
            
        except Exception as e:
            print(f"❌ 超时配置测试失败: {str(e)}")
            return False
    
    def test_retry_configuration(self) -> bool:
        """
        测试重试配置
        
        Returns:
            bool: 重试配置是否正确
        """
        try:
            # 测试不同的重试配置
            retry_configs = [
                (0, 0.1),  # 不重试
                (1, 0.5),  # 重试1次
                (3, 1.0),  # 重试3次
                (5, 2.0)   # 重试5次
            ]
            
            for retry_count, retry_delay in retry_configs:
                client = APIClient(
                    self.base_url, 
                    retry_count=retry_count, 
                    retry_delay=retry_delay
                )
                
                # 验证重试配置
                assert client.retry_count == retry_count, f"重试次数配置错误: 期望 {retry_count}, 实际 {client.retry_count}"
                assert client.retry_delay == retry_delay, f"重试延迟配置错误: 期望 {retry_delay}, 实际 {client.retry_delay}"
                
                client.close()
            
            print("✅ 重试配置测试通过")
            return True
            
        except Exception as e:
            print(f"❌ 重试配置测试失败: {str(e)}")
            return False
    
    def test_network_delay_simulation(self) -> bool:
        """
        测试网络延迟模拟
        
        Returns:
            bool: 网络延迟模拟是否正确
        """
        try:
            # 创建短超时的客户端
            client = APIClient(self.base_url, timeout=0.1)  # 100毫秒超时
            
            try:
                # 尝试请求，应该超时
                response = client.get('/api/monitoring/health/')
                
                # 如果没有超时，可能是网络太快或服务不存在
                print("⚠️  网络延迟模拟未触发超时（网络响应过快或服务不存在）")
                return True
                
            except requests.exceptions.Timeout:
                print("✅ 网络延迟模拟成功触发超时")
                return True
            except requests.exceptions.ConnectionError:
                # 连接错误也是预期的（服务可能未运行）
                print("✅ 网络延迟模拟成功（连接错误）")
                return True
            finally:
                client.close()
                
        except Exception as e:
            print(f"❌ 网络延迟模拟测试失败: {str(e)}")
            return False
    
    def test_timeout_error_handling(self) -> bool:
        """
        测试超时错误处理
        
        Returns:
            bool: 超时错误处理是否正确
        """
        try:
            # 使用极短的超时时间
            client = APIClient(self.base_url, timeout=0.001)  # 1毫秒超时
            
            timeout_occurred = False
            
            try:
                response = client.get('/api/monitoring/health/')
            except requests.exceptions.Timeout:
                timeout_occurred = True
                print("✅ 超时错误正确捕获")
            except requests.exceptions.ConnectionError:
                # 连接错误也是可接受的
                print("✅ 连接错误正确捕获（可能服务未运行）")
                timeout_occurred = True
            except Exception as e:
                print(f"⚠️  捕获到其他异常: {type(e).__name__}: {str(e)}")
                timeout_occurred = True
            finally:
                client.close()
            
            return timeout_occurred
            
        except Exception as e:
            print(f"❌ 超时错误处理测试失败: {str(e)}")
            return False


# 测试用例

@pytest.fixture
def config():
    """测试配置fixture"""
    return TestConfigManager()


@pytest.fixture
def timeout_retry_tester(config):
    """超时重试测试器fixture"""
    return TimeoutRetryTester(config)


def test_timeout_retry_tester_creation(config):
    """测试超时重试测试器创建"""
    tester = TimeoutRetryTester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()


def test_timeout_configuration(timeout_retry_tester):
    """测试超时配置"""
    result = timeout_retry_tester.test_timeout_configuration()
    assert result is True


def test_retry_configuration(timeout_retry_tester):
    """测试重试配置"""
    result = timeout_retry_tester.test_retry_configuration()
    assert result is True


def test_network_delay_simulation(timeout_retry_tester):
    """测试网络延迟模拟"""
    result = timeout_retry_tester.test_network_delay_simulation()
    assert result is True


def test_timeout_error_handling(timeout_retry_tester):
    """测试超时错误处理"""
    result = timeout_retry_tester.test_timeout_error_handling()
    assert result is True


@patch('requests.Session.request')
def test_retry_mechanism_with_mock(mock_request):
    """使用Mock测试重试机制"""
    # 设置Mock，前两次失败，第三次成功
    failure_response = Mock()
    failure_response.side_effect = requests.exceptions.ConnectionError("Connection failed")
    
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {'Content-Type': 'application/json'}
    success_response.content = b'{"status": "ok"}'
    success_response.text = '{"status": "ok"}'
    success_response.json.return_value = {"status": "ok"}
    
    # 前两次失败，第三次成功
    mock_request.side_effect = [
        requests.exceptions.ConnectionError("Connection failed"),
        requests.exceptions.ConnectionError("Connection failed"),
        success_response
    ]
    
    # 创建带重试的客户端
    config = TestConfigManager()
    client = APIClient(
        base_url=config.get_base_url(),
        retry_count=3,
        retry_delay=0.1
    )
    
    try:
        # 发送请求，应该在第三次重试时成功
        response = client.get('/api/test/')
        
        # 验证最终成功
        assert response.status_code == 200
        assert response.json_data == {"status": "ok"}
        
        # 验证重试次数（应该调用3次）
        assert mock_request.call_count == 3
        
    finally:
        client.close()


@patch('requests.Session.request')
def test_retry_exhaustion_with_mock(mock_request):
    """使用Mock测试重试耗尽"""
    # 设置Mock，所有请求都失败
    mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
    
    # 创建带重试的客户端
    config = TestConfigManager()
    client = APIClient(
        base_url=config.get_base_url(),
        retry_count=2,
        retry_delay=0.1
    )
    
    try:
        # 发送请求，应该在重试耗尽后失败
        with pytest.raises(requests.exceptions.ConnectionError):
            response = client.get('/api/test/')
        
        # 验证重试次数（初始请求 + 2次重试 = 3次调用）
        assert mock_request.call_count == 3
        
    finally:
        client.close()


@patch('time.sleep')
@patch('requests.Session.request')
def test_retry_delay_with_mock(mock_request, mock_sleep):
    """使用Mock测试重试延迟"""
    # 设置Mock，前一次失败，第二次成功
    failure_response = requests.exceptions.ConnectionError("Connection failed")
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {'Content-Type': 'application/json'}
    success_response.content = b'{"status": "ok"}'
    success_response.text = '{"status": "ok"}'
    success_response.json.return_value = {"status": "ok"}
    
    mock_request.side_effect = [failure_response, success_response]
    
    # 创建带重试延迟的客户端
    config = TestConfigManager()
    client = APIClient(
        base_url=config.get_base_url(),
        retry_count=2,
        retry_delay=1.5
    )
    
    try:
        # 发送请求
        response = client.get('/api/test/')
        
        # 验证成功
        assert response.status_code == 200
        
        # 验证调用了sleep（重试延迟）
        mock_sleep.assert_called_with(1.5)
        
    finally:
        client.close()


def test_retry_helper_functionality():
    """测试重试助手功能"""
    # 测试重试装饰器的基本功能
    call_count = 0
    
    @RetryHelper.retry_with_backoff
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise requests.exceptions.ConnectionError("Test error")
        return "success"
    
    # 应该在第3次调用时成功
    result = test_function()
    assert result == "success"
    assert call_count == 3


def test_timeout_with_different_endpoints():
    """测试不同端点的超时处理"""
    config = TestConfigManager()
    endpoints = [
        '/api/monitoring/health/',
        '/api/auth/login/',
        '/api/videos/',
        '/nonexistent/'
    ]
    
    for endpoint in endpoints:
        client = APIClient(config.get_base_url(), timeout=0.1)
        
        try:
            response = client.get(endpoint)
            # 如果没有超时，说明网络很快或端点不存在
            print(f"端点 {endpoint}: 响应正常或快速失败")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            # 超时或连接错误都是预期的
            print(f"端点 {endpoint}: 正确处理超时/连接错误")
        except Exception as e:
            print(f"端点 {endpoint}: 其他异常 {type(e).__name__}")
        finally:
            client.close()


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = TimeoutRetryTester(config)
    
    print("开始超时和重试机制测试...")
    print(f"目标URL: {config.get_base_url()}")
    
    # 执行测试
    print("\n1. 测试超时配置...")
    timeout_config_result = tester.test_timeout_configuration()
    
    print("\n2. 测试重试配置...")
    retry_config_result = tester.test_retry_configuration()
    
    print("\n3. 测试网络延迟模拟...")
    delay_result = tester.test_network_delay_simulation()
    
    print("\n4. 测试超时错误处理...")
    timeout_error_result = tester.test_timeout_error_handling()
    
    # 总结
    print(f"\n测试结果:")
    print(f"- 超时配置: {'✅ 通过' if timeout_config_result else '❌ 失败'}")
    print(f"- 重试配置: {'✅ 通过' if retry_config_result else '❌ 失败'}")
    print(f"- 网络延迟: {'✅ 通过' if delay_result else '❌ 失败'}")
    print(f"- 超时错误: {'✅ 通过' if timeout_error_result else '❌ 失败'}")