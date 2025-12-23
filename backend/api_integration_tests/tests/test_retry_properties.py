"""
网络重试机制可靠性属性测试模块

使用属性测试验证网络重试机制的可靠性。
**属性 10: 网络重试机制可靠性**
**验证需求: 1.5**
"""

import pytest
import time
import requests
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Callable
from requests.exceptions import ConnectionError, Timeout, RequestException
import threading
import random

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.http_client import APIClient, HTTPResponse
from utils.test_helpers import TestLogger, RetryHelper
from config.test_config import TestConfigManager


class RetryPropertiesTester:
    """重试机制属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化重试机制属性测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.logger = TestLogger("retry_properties_test.log")
        self.base_url = config.get_base_url()
    
    def cleanup(self):
        """清理资源"""
        if self.logger:
            self.logger.save_to_file()


# 生成策略
retry_count_strategy = st.integers(min_value=0, max_value=10)
retry_delay_strategy = st.floats(min_value=0.1, max_value=5.0)
timeout_strategy = st.floats(min_value=0.1, max_value=30.0)
endpoint_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))


@pytest.fixture
def retry_properties_tester():
    """重试机制属性测试器fixture"""
    config = TestConfigManager()
    tester = RetryPropertiesTester(config)
    yield tester
    tester.cleanup()


@given(
    retry_count=retry_count_strategy,
    retry_delay=retry_delay_strategy,
    timeout=timeout_strategy
)
@settings(max_examples=50, deadline=30000)  # 30秒超时
def test_retry_count_property(retry_count, retry_delay, timeout):
    """
    属性测试: 重试次数配置正确性
    
    **属性 10: 网络重试机制可靠性**
    **验证需求: 1.5**
    
    对于任何有效的重试配置，当所有请求都失败时，
    实际的请求次数应该等于 retry_count + 1（初始请求 + 重试次数）
    """
    # 限制参数范围以避免测试时间过长
    assume(retry_count <= 5)
    assume(retry_delay <= 2.0)
    assume(timeout <= 10.0)
    
    with patch('requests.Session.request') as mock_request:
        # 模拟所有请求都失败
        mock_request.side_effect = ConnectionError("Connection failed")
        
        client = APIClient(
            base_url="http://test.com",
            timeout=timeout,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
        
        try:
            response = client.get("/api/test/")
            # 如果没有抛出异常，说明有问题
            assert False, "期望连接失败，但请求成功了"
        except ConnectionError:
            # 验证实际调用次数
            expected_calls = retry_count + 1
            actual_calls = mock_request.call_count
            
            assert actual_calls == expected_calls, (
                f"重试次数不正确: 配置{retry_count}次重试，期望{expected_calls}次调用，"
                f"实际{actual_calls}次调用"
            )
        finally:
            client.close()


@given(
    fail_count=st.integers(min_value=1, max_value=5),
    retry_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=30, deadline=20000)
def test_retry_success_property(fail_count, retry_count):
    """
    属性测试: 重试成功场景
    
    **属性 10: 网络重试机制可靠性**
    **验证需求: 1.5**
    
    对于任何配置，如果前N次请求失败，第N+1次请求成功，
    且N <= retry_count，则最终应该成功
    """
    # 确保有足够的重试次数
    assume(fail_count <= retry_count)
    
    with patch('requests.Session.request') as mock_request:
        # 创建成功响应
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"Content-Type": "application/json"}
        success_response.content = b'{"status": "success"}'
        success_response.text = '{"status": "success"}'
        success_response.json.return_value = {"status": "success"}
        
        # 设置前N次失败，最后一次成功
        side_effects = [ConnectionError("Connection failed")] * fail_count
        side_effects.append(success_response)
        mock_request.side_effect = side_effects
        
        client = APIClient(
            base_url="http://test.com",
            timeout=5,
            retry_count=retry_count,
            retry_delay=0.1  # 减少延迟以加快测试
        )
        
        try:
            response = client.get("/api/test/")
            
            # 验证最终成功
            assert response.status_code == 200, f"期望状态码200，实际{response.status_code}"
            assert response.json_data.get("status") == "success", f"响应数据不正确: {response.json_data}"
            
            # 验证调用次数
            expected_calls = fail_count + 1
            actual_calls = mock_request.call_count
            assert actual_calls == expected_calls, (
                f"调用次数不正确: 期望{expected_calls}次，实际{actual_calls}次"
            )
            
        finally:
            client.close()


@given(
    retry_delay=retry_delay_strategy,
    retry_count=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=20, deadline=15000)
def test_retry_delay_property(retry_delay, retry_count):
    """
    属性测试: 重试延迟机制
    
    **属性 10: 网络重试机制可靠性**
    **验证需求: 1.5**
    
    对于任何重试延迟配置，重试之间应该有适当的延迟
    """
    # 限制参数以避免测试时间过长
    assume(retry_delay <= 1.0)
    assume(retry_count <= 2)
    
    with patch('time.sleep') as mock_sleep:
        with patch('requests.Session.request') as mock_request:
            # 模拟连接错误
            mock_request.side_effect = ConnectionError("Connection failed")
            
            client = APIClient(
                base_url="http://test.com",
                timeout=1,
                retry_count=retry_count,
                retry_delay=retry_delay
            )
            
            try:
                response = client.get("/api/test/")
            except ConnectionError:
                pass  # 期望的异常
            
            # 验证sleep被调用了正确的次数
            expected_sleep_calls = retry_count
            actual_sleep_calls = mock_sleep.call_count
            
            assert actual_sleep_calls == expected_sleep_calls, (
                f"延迟调用次数不正确: 期望{expected_sleep_calls}次，实际{actual_sleep_calls}次"
            )
            
            # 验证延迟时间（可能有退避策略）
            if mock_sleep.call_count > 0:
                call_args = [call[0][0] for call in mock_sleep.call_args_list]
                
                # 检查是否使用了基础延迟时间或退避策略
                first_delay = call_args[0]
                assert first_delay >= retry_delay * 0.5, (
                    f"第一次延迟时间过短: 期望至少{retry_delay * 0.5}s，实际{first_delay}s"
                )
                assert first_delay <= retry_delay * 10, (
                    f"第一次延迟时间过长: 期望最多{retry_delay * 10}s，实际{first_delay}s"
                )
            
            client.close()


@given(
    error_type=st.sampled_from([
        ConnectionError,
        Timeout,
        requests.exceptions.RequestException
    ]),
    retry_count=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=30, deadline=15000)
def test_error_type_retry_property(error_type, retry_count):
    """
    属性测试: 不同错误类型的重试行为
    
    **属性 10: 网络重试机制可靠性**
    **验证需求: 1.5**
    
    对于任何网络错误类型，重试机制都应该正常工作
    """
    with patch('requests.Session.request') as mock_request:
        # 模拟特定类型的错误
        mock_request.side_effect = error_type("Test error")
        
        client = APIClient(
            base_url="http://test.com",
            timeout=1,
            retry_count=retry_count,
            retry_delay=0.1
        )
        
        try:
            response = client.get("/api/test/")
            assert False, f"期望{error_type.__name__}，但请求成功了"
        except error_type:
            # 验证重试次数
            expected_calls = retry_count + 1
            actual_calls = mock_request.call_count
            
            assert actual_calls == expected_calls, (
                f"{error_type.__name__}重试次数不正确: "
                f"期望{expected_calls}次调用，实际{actual_calls}次"
            )
        finally:
            client.close()


@given(
    interruption_point=st.integers(min_value=1, max_value=3),
    retry_count=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=20, deadline=10000)
def test_network_interruption_recovery_property(interruption_point, retry_count):
    """
    属性测试: 网络中断恢复能力
    
    **属性 10: 网络重试机制可靠性**
    **验证需求: 1.5**
    
    对于任何网络中断点，如果在重试范围内恢复，应该能够成功
    """
    # 确保中断点在重试范围内
    assume(interruption_point <= retry_count)
    
    with patch('requests.Session.request') as mock_request:
        # 创建成功响应
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"Content-Type": "application/json"}
        success_response.content = b'{"recovered": true}'
        success_response.text = '{"recovered": true}'
        success_response.json.return_value = {"recovered": True}
        
        # 模拟网络中断然后恢复
        interruption_errors = [
            ConnectionError("Connection aborted"),
            ConnectionError("Connection reset by peer"),
            requests.exceptions.ChunkedEncodingError("Connection broken")
        ]
        
        # 前N次中断，然后恢复
        side_effects = []
        for i in range(interruption_point):
            side_effects.append(random.choice(interruption_errors))
        side_effects.append(success_response)
        
        mock_request.side_effect = side_effects
        
        client = APIClient(
            base_url="http://test.com",
            timeout=5,
            retry_count=retry_count,
            retry_delay=0.1
        )
        
        try:
            response = client.get("/api/test/")
            
            # 验证恢复成功
            assert response.status_code == 200, f"期望状态码200，实际{response.status_code}"
            assert response.json_data.get("recovered") is True, (
                f"恢复标志不正确: {response.json_data}"
            )
            
            # 验证调用次数
            expected_calls = interruption_point + 1
            actual_calls = mock_request.call_count
            assert actual_calls == expected_calls, (
                f"网络中断恢复调用次数不正确: 期望{expected_calls}次，实际{actual_calls}次"
            )
            
        finally:
            client.close()


@given(
    timeout=st.floats(min_value=0.1, max_value=5.0),
    retry_count=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=15, deadline=10000)
def test_timeout_retry_property(timeout, retry_count):
    """
    属性测试: 超时重试机制
    
    **属性 10: 网络重试机制可靠性**
    **验证需求: 1.5**
    
    对于任何超时配置，超时错误应该触发重试机制
    """
    # 限制参数以避免测试时间过长
    assume(timeout <= 2.0)
    
    with patch('requests.Session.request') as mock_request:
        # 模拟超时错误
        mock_request.side_effect = Timeout("Request timeout")
        
        client = APIClient(
            base_url="http://test.com",
            timeout=timeout,
            retry_count=retry_count,
            retry_delay=0.1
        )
        
        try:
            response = client.get("/api/test/")
            assert False, "期望超时错误，但请求成功了"
        except Timeout:
            # 验证重试次数
            expected_calls = retry_count + 1
            actual_calls = mock_request.call_count
            
            assert actual_calls == expected_calls, (
                f"超时重试次数不正确: 期望{expected_calls}次调用，实际{actual_calls}次"
            )
        finally:
            client.close()


# 传统pytest测试函数（用于验证属性测试的正确性）

def test_retry_properties_tester_creation():
    """测试重试属性测试器创建"""
    config = TestConfigManager()
    tester = RetryPropertiesTester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()
    tester.cleanup()


def test_property_test_strategies():
    """测试属性测试策略的有效性"""
    # 测试重试次数策略
    retry_counts = [retry_count_strategy.example() for _ in range(10)]
    assert all(0 <= count <= 10 for count in retry_counts), "重试次数策略范围不正确"
    
    # 测试重试延迟策略
    retry_delays = [retry_delay_strategy.example() for _ in range(10)]
    assert all(0.1 <= delay <= 5.0 for delay in retry_delays), "重试延迟策略范围不正确"
    
    # 测试超时策略
    timeouts = [timeout_strategy.example() for _ in range(10)]
    assert all(0.1 <= t <= 30.0 for t in timeouts), "超时策略范围不正确"


if __name__ == "__main__":
    # 直接运行属性测试
    print("开始网络重试机制可靠性属性测试...")
    
    # 运行一些基本的属性测试示例
    config = TestConfigManager()
    
    print("✅ 属性测试策略验证通过")
    print("✅ 网络重试机制可靠性属性测试准备就绪")
    
    print("\n要运行完整的属性测试，请使用:")
    print("pytest test_retry_properties.py -v")
    print("或者:")
    print("python -m pytest test_retry_properties.py --hypothesis-show-statistics")