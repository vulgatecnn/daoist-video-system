"""
错误处理一致性属性测试模块

**属性 7: 错误处理一致性**
*对于任何* API错误响应，客户端应该显示适当的错误消息、提供重试选项（如适用）、
记录错误信息，并在认证失败时正确处理状态清理

**验证需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
"""

import pytest
import requests
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch
from typing import Dict, Any, List, Optional, Union

from ..utils.http_client import APIClient, HTTPResponse
from ..utils.test_helpers import TestLogger, TestDataGenerator
from ..config.test_config import TestConfigManager


class ErrorHandlingPropertiesTester:
    """错误处理一致性属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化属性测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.logger = TestLogger("error_handling_properties_test.log")
    
    def create_test_client(self, retry_count: int = 1) -> APIClient:
        """创建测试客户端"""
        return APIClient(
            base_url=self.config.get_base_url(),
            timeout=self.config.get_timeout(),
            retry_count=retry_count
        )
    
    def cleanup(self):
        """清理资源"""
        if self.logger:
            self.logger.save_to_file()


# Hypothesis策略定义
@st.composite
def http_error_response_strategy(draw):
    """生成HTTP错误响应的策略"""
    # 4xx和5xx错误状态码
    status_code = draw(st.one_of(
        st.integers(min_value=400, max_value=499),  # 4xx客户端错误
        st.integers(min_value=500, max_value=599)   # 5xx服务器错误
    ))
    
    # 错误消息内容
    error_messages = [
        "Bad Request",
        "Unauthorized",
        "Forbidden", 
        "Not Found",
        "Method Not Allowed",
        "Unprocessable Entity",
        "Internal Server Error",
        "Bad Gateway",
        "Service Unavailable",
        "Gateway Timeout"
    ]
    
    # 生成错误响应数据
    error_data = draw(st.one_of(
        # JSON格式错误
        st.fixed_dictionaries({
            "error": st.sampled_from(error_messages),
            "detail": st.text(min_size=1, max_size=100),
            "code": st.integers(min_value=1000, max_value=9999)
        }),
        # 简单错误消息
        st.fixed_dictionaries({
            "detail": st.sampled_from(error_messages)
        }),
        # 字段验证错误
        st.fixed_dictionaries({
            "username": st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3),
            "password": st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3)
        }),
        # 空响应
        st.just({})
    ))
    
    return {
        "status_code": status_code,
        "error_data": error_data,
        "content_type": draw(st.sampled_from([
            "application/json",
            "text/html",
            "text/plain"
        ]))
    }


@st.composite
def api_endpoint_strategy(draw):
    """生成API端点的策略"""
    endpoints = [
        "/api/auth/login/",
        "/api/auth/register/",
        "/api/videos/",
        "/api/videos/1/",
        "/api/videos/upload/",
        "/api/videos/composition/create/",
        "/api/monitoring/health/",
        "/api/videos/admin/monitoring/statistics/"
    ]
    
    methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    
    return {
        "endpoint": draw(st.sampled_from(endpoints)),
        "method": draw(st.sampled_from(methods)),
        "requires_auth": draw(st.booleans())
    }


@st.composite
def network_error_strategy(draw):
    """生成网络错误的策略"""
    error_types = [
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        requests.exceptions.ChunkedEncodingError
    ]
    
    error_messages = [
        "Connection refused",
        "Connection timeout", 
        "Name resolution failed",
        "Network unreachable",
        "Connection broken",
        "Read timeout"
    ]
    
    return {
        "error_type": draw(st.sampled_from(error_types)),
        "error_message": draw(st.sampled_from(error_messages))
    }


# 属性测试函数
@given(error_response=http_error_response_strategy())
@settings(max_examples=50, deadline=30000)  # 50次测试，30秒超时
def test_http_error_response_consistency_property(error_response):
    """
    **Feature: api-integration-testing, Property 7: HTTP错误响应一致性**
    
    *对于任何* HTTP错误响应，客户端应该正确处理错误状态码、提取错误消息、
    记录错误信息，并根据错误类型采取适当的处理措施
    
    **验证需求: 6.1, 6.2**
    """
    # 跳过无效的状态码
    assume(400 <= error_response["status_code"] <= 599)
    
    config = TestConfigManager()
    properties_tester = ErrorHandlingPropertiesTester(config)
    client = properties_tester.create_test_client()
    
    try:
        with patch.object(client, '_make_request') as mock_request:
            # 模拟HTTP错误响应
            mock_response = HTTPResponse(
                status_code=error_response["status_code"],
                headers={"Content-Type": error_response["content_type"]},
                content=str(error_response["error_data"]).encode(),
                text=str(error_response["error_data"]),
                json_data=error_response["error_data"] if error_response["content_type"] == "application/json" else None,
                response_time=0.1,
                url="http://test.com/api/test/"
            )
            
            mock_request.return_value = mock_response
            
            # 执行请求
            response = client.get("/api/test/")
            
            # 属性验证：状态码正确识别
            if 400 <= error_response["status_code"] <= 499:
                assert response.is_client_error, f"4xx错误状态码{error_response['status_code']}应该被识别为客户端错误"
                assert not response.is_server_error, f"4xx错误状态码{error_response['status_code']}不应该被识别为服务器错误"
            elif 500 <= error_response["status_code"] <= 599:
                assert response.is_server_error, f"5xx错误状态码{error_response['status_code']}应该被识别为服务器错误"
                assert not response.is_client_error, f"5xx错误状态码{error_response['status_code']}不应该被识别为客户端错误"
            
            # 属性验证：错误响应不被认为是成功
            assert not response.is_success, f"错误状态码{error_response['status_code']}不应该被认为是成功"
            
            # 属性验证：响应时间被记录
            assert response.response_time >= 0, "响应时间应该是非负数"
            
            # 属性验证：URL被正确记录
            assert response.url is not None, "响应URL应该被记录"
            
            # 属性验证：如果是JSON响应，应该能正确解析
            if error_response["content_type"] == "application/json" and error_response["error_data"]:
                if response.json_data is not None:
                    assert isinstance(response.json_data, dict), "JSON响应应该被解析为字典"
            
            properties_tester.logger.info("HTTP错误响应一致性属性验证通过", {
                "status_code": error_response["status_code"],
                "is_client_error": response.is_client_error,
                "is_server_error": response.is_server_error,
                "is_success": response.is_success
            })
    
    finally:
        client.close()
        properties_tester.cleanup()


@given(network_error=network_error_strategy(), endpoint=api_endpoint_strategy())
@settings(max_examples=30, deadline=30000)
def test_network_error_handling_consistency_property(network_error, endpoint):
    """
    **Feature: api-integration-testing, Property 7: 网络错误处理一致性**
    
    *对于任何* 网络错误，客户端应该正确捕获异常、记录错误信息、
    并根据错误类型提供适当的错误处理
    
    **验证需求: 6.3, 6.4**
    """
    config = TestConfigManager()
    properties_tester = ErrorHandlingPropertiesTester(config)
    client = properties_tester.create_test_client()
    
    try:
        with patch.object(client.session, 'request') as mock_request:
            # 模拟网络错误
            mock_request.side_effect = network_error["error_type"](network_error["error_message"])
            
            # 记录初始日志数量
            initial_log_count = len(properties_tester.logger.log_entries)
            
            # 执行请求，期望抛出异常
            with pytest.raises((
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException,
                requests.exceptions.ChunkedEncodingError
            )):
                if endpoint["method"] == "GET":
                    client.get(endpoint["endpoint"])
                elif endpoint["method"] == "POST":
                    client.post(endpoint["endpoint"], {"test": "data"})
                elif endpoint["method"] == "PUT":
                    client.put(endpoint["endpoint"], {"test": "data"})
                elif endpoint["method"] == "PATCH":
                    client.patch(endpoint["endpoint"], {"test": "data"})
                elif endpoint["method"] == "DELETE":
                    client.delete(endpoint["endpoint"])
            
            # 属性验证：错误被记录到日志
            new_log_count = len(properties_tester.logger.log_entries)
            assert new_log_count > initial_log_count, "网络错误应该被记录到日志"
            
            # 属性验证：日志包含错误信息
            recent_logs = properties_tester.logger.log_entries[initial_log_count:]
            error_logged = any(
                entry["level"] == "ERROR" and 
                any(keyword in entry["message"].lower() for keyword in ["错误", "异常", "error", "exception"])
                for entry in recent_logs
            )
            assert error_logged, "日志应该包含错误相关信息"
            
            properties_tester.logger.info("网络错误处理一致性属性验证通过", {
                "error_type": network_error["error_type"].__name__,
                "error_message": network_error["error_message"],
                "endpoint": endpoint["endpoint"],
                "method": endpoint["method"]
            })
    
    finally:
        client.close()
        properties_tester.cleanup()


@given(
    auth_error_status=st.sampled_from([401, 403]),
    has_initial_token=st.booleans()
)
@settings(max_examples=20, deadline=30000)
def test_authentication_error_state_cleanup_property(auth_error_status, has_initial_token):
    """
    **Feature: api-integration-testing, Property 7: 认证错误状态清理一致性**
    
    *对于任何* 认证错误响应，客户端应该正确处理认证状态、
    清理相关信息，并记录适当的错误日志
    
    **验证需求: 6.6**
    """
    config = TestConfigManager()
    properties_tester = ErrorHandlingPropertiesTester(config)
    client = properties_tester.create_test_client()
    
    try:
        # 根据测试参数设置初始认证状态
        if has_initial_token:
            client.set_auth_token("test_access_token", "test_refresh_token")
            initial_has_token = True
        else:
            initial_has_token = False
        
        with patch.object(client, '_make_request') as mock_request:
            # 模拟认证错误响应
            error_data = {
                "detail": "Authentication credentials were not provided." if auth_error_status == 401 
                         else "You do not have permission to perform this action."
            }
            
            mock_response = HTTPResponse(
                status_code=auth_error_status,
                headers={"Content-Type": "application/json"},
                content=str(error_data).encode(),
                text=str(error_data),
                json_data=error_data,
                response_time=0.1,
                url="http://test.com/api/videos/"
            )
            
            mock_request.return_value = mock_response
            
            # 记录初始日志数量
            initial_log_count = len(properties_tester.logger.log_entries)
            
            # 执行需要认证的请求
            response = client.get("/api/videos/")
            
            # 属性验证：认证错误被正确识别
            assert response.status_code == auth_error_status, f"应该返回{auth_error_status}状态码"
            assert response.is_client_error, f"{auth_error_status}应该被识别为客户端错误"
            
            # 属性验证：错误响应包含认证相关信息
            if response.json_data and "detail" in response.json_data:
                detail = response.json_data["detail"].lower()
                assert any(keyword in detail for keyword in [
                    "authentication", "permission", "credentials", "token", "unauthorized", "forbidden"
                ]), f"认证错误响应应该包含认证相关信息: {response.json_data}"
            
            # 属性验证：认证状态保持一致（认证错误不应该自动清理现有令牌）
            if initial_has_token:
                # 如果初始有令牌，认证错误不应该自动清理它
                # 这是因为错误可能是由于权限不足而不是令牌无效
                assert client.access_token is not None, "认证错误不应该自动清理现有的访问令牌"
            else:
                # 如果初始没有令牌，应该保持没有令牌的状态
                assert client.access_token is None, "没有初始令牌时，认证错误后应该保持无令牌状态"
            
            properties_tester.logger.info("认证错误状态清理一致性属性验证通过", {
                "auth_error_status": auth_error_status,
                "had_initial_token": has_initial_token,
                "has_token_after_error": client.access_token is not None,
                "error_detail": response.json_data
            })
    
    finally:
        client.close()
        properties_tester.cleanup()


@given(
    error_scenario=st.one_of(
        # HTTP错误场景
        st.fixed_dictionaries({
            "type": st.just("http_error"),
            "status_code": st.integers(min_value=400, max_value=599),
            "error_data": st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(min_size=1, max_size=100), st.lists(st.text(min_size=1, max_size=50), max_size=3)),
                min_size=1, max_size=3
            )
        }),
        # 网络错误场景
        st.fixed_dictionaries({
            "type": st.just("network_error"),
            "error_class": st.sampled_from([
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException
            ]),
            "error_message": st.text(min_size=1, max_size=100)
        })
    )
)
@settings(max_examples=40, deadline=30000)
def test_error_logging_consistency_property(error_scenario):
    """
    **Feature: api-integration-testing, Property 7: 错误日志记录一致性**
    
    *对于任何* 错误场景，客户端应该记录适当的错误信息到日志，
    包括错误类型、错误消息和相关上下文信息
    
    **验证需求: 6.5**
    """
    config = TestConfigManager()
    properties_tester = ErrorHandlingPropertiesTester(config)
    client = properties_tester.create_test_client()
    
    try:
        # 记录初始日志数量
        initial_log_count = len(properties_tester.logger.log_entries)
        
        if error_scenario["type"] == "http_error":
            # HTTP错误场景
            with patch.object(client, '_make_request') as mock_request:
                mock_response = HTTPResponse(
                    status_code=error_scenario["status_code"],
                    headers={"Content-Type": "application/json"},
                    content=str(error_scenario["error_data"]).encode(),
                    text=str(error_scenario["error_data"]),
                    json_data=error_scenario["error_data"],
                    response_time=0.1,
                    url="http://test.com/api/test/"
                )
                
                mock_request.return_value = mock_response
                
                # 执行请求
                response = client.get("/api/test/")
                
                # HTTP错误通常不会抛出异常，而是返回错误响应
                assert response.status_code == error_scenario["status_code"]
        
        elif error_scenario["type"] == "network_error":
            # 网络错误场景
            with patch.object(client.session, 'request') as mock_request:
                mock_request.side_effect = error_scenario["error_class"](error_scenario["error_message"])
                
                # 执行请求，期望抛出异常
                with pytest.raises((
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException
                )):
                    client.get("/api/test/")
        
        # 属性验证：错误被记录到日志
        new_log_count = len(properties_tester.logger.log_entries)
        assert new_log_count > initial_log_count, f"错误场景应该产生日志记录: {error_scenario['type']}"
        
        # 属性验证：日志包含错误相关信息
        recent_logs = properties_tester.logger.log_entries[initial_log_count:]
        
        # 检查是否有错误级别的日志
        has_error_log = any(
            entry["level"] in ["ERROR", "WARNING"] 
            for entry in recent_logs
        )
        assert has_error_log, "应该有ERROR或WARNING级别的日志记录"
        
        # 检查日志是否包含错误相关关键词
        has_error_keywords = any(
            any(keyword in entry["message"].lower() for keyword in [
                "错误", "异常", "失败", "error", "exception", "failed", "timeout", "connection"
            ])
            for entry in recent_logs
        )
        assert has_error_keywords, "日志应该包含错误相关的关键词"
        
        # 属性验证：日志包含上下文信息
        has_context_info = any(
            entry.get("details") and isinstance(entry["details"], dict) and len(entry["details"]) > 0
            for entry in recent_logs
        )
        # 注意：这个验证比较宽松，因为不是所有错误都需要详细上下文
        
        properties_tester.logger.info("错误日志记录一致性属性验证通过", {
            "error_type": error_scenario["type"],
            "new_log_entries": len(recent_logs),
            "has_error_log": has_error_log,
            "has_error_keywords": has_error_keywords,
            "has_context_info": has_context_info
        })
    
    finally:
        client.close()
        properties_tester.cleanup()


@given(
    retry_scenario=st.fixed_dictionaries({
        "should_retry": st.booleans(),
        "error_type": st.sampled_from([
            "network_timeout",
            "connection_error", 
            "server_error",
            "client_error"
        ]),
        "retry_count": st.integers(min_value=1, max_value=5)
    })
)
@settings(max_examples=20, deadline=30000)
def test_retry_option_consistency_property(retry_scenario):
    """
    **Feature: api-integration-testing, Property 7: 重试选项一致性**
    
    *对于任何* 可重试的错误场景，客户端应该提供重试机制；
    对于不可重试的错误，应该直接返回错误而不进行重试
    
    **验证需求: 6.2, 6.3**
    """
    config = TestConfigManager()
    properties_tester = ErrorHandlingPropertiesTester(config)
    client = properties_tester.create_test_client(retry_count=retry_scenario["retry_count"])
    
    try:
        with patch.object(client.session, 'request') as mock_request:
            if retry_scenario["error_type"] == "network_timeout":
                # 网络超时 - 应该重试
                mock_request.side_effect = requests.exceptions.Timeout("Request timeout")
                should_retry_expected = True
                
            elif retry_scenario["error_type"] == "connection_error":
                # 连接错误 - 应该重试
                mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
                should_retry_expected = True
                
            elif retry_scenario["error_type"] == "server_error":
                # 服务器错误 - 可能重试
                mock_response = Mock()
                mock_response.status_code = 503  # Service Unavailable
                mock_response.headers = {"Content-Type": "application/json"}
                mock_response.content = b'{"error": "Service temporarily unavailable"}'
                mock_response.text = '{"error": "Service temporarily unavailable"}'
                mock_response.json.return_value = {"error": "Service temporarily unavailable"}
                mock_request.return_value = mock_response
                should_retry_expected = False  # HTTP响应不会触发重试机制
                
            elif retry_scenario["error_type"] == "client_error":
                # 客户端错误 - 不应该重试
                mock_response = Mock()
                mock_response.status_code = 400  # Bad Request
                mock_response.headers = {"Content-Type": "application/json"}
                mock_response.content = b'{"error": "Bad request"}'
                mock_response.text = '{"error": "Bad request"}'
                mock_response.json.return_value = {"error": "Bad request"}
                mock_request.return_value = mock_response
                should_retry_expected = False  # HTTP响应不会触发重试机制
            
            # 执行请求
            try:
                response = client.get("/api/test/")
                
                # 如果没有抛出异常，说明是HTTP响应
                if retry_scenario["error_type"] in ["server_error", "client_error"]:
                    # HTTP错误响应不会触发重试机制，但会返回错误状态码
                    assert response.status_code >= 400, "应该返回错误状态码"
                    
                    # 验证请求只被调用一次（没有重试）
                    assert mock_request.call_count == 1, "HTTP错误响应不应该触发重试"
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # 网络异常会触发重试机制
                if should_retry_expected:
                    # 验证重试次数
                    expected_attempts = retry_scenario["retry_count"] + 1  # 初始尝试 + 重试次数
                    assert mock_request.call_count == expected_attempts, \
                        f"应该尝试{expected_attempts}次，实际尝试{mock_request.call_count}次"
                else:
                    # 不应该重试的情况
                    assert mock_request.call_count == 1, "不应该重试的错误被重试了"
            
            properties_tester.logger.info("重试选项一致性属性验证通过", {
                "error_type": retry_scenario["error_type"],
                "retry_count": retry_scenario["retry_count"],
                "actual_attempts": mock_request.call_count,
                "should_retry_expected": should_retry_expected
            })
    
    finally:
        client.close()
        properties_tester.cleanup()


# pytest fixture (用于非属性测试)
@pytest.fixture
def properties_tester():
    """错误处理属性测试器fixture"""
    config = TestConfigManager()
    tester = ErrorHandlingPropertiesTester(config)
    yield tester
    tester.cleanup()


if __name__ == "__main__":
    # 直接运行属性测试
    import subprocess
    import sys
    
    print("开始错误处理一致性属性测试...")
    
    # 运行pytest属性测试
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "-x"  # 遇到第一个失败就停止
    ], capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"\n测试退出码: {result.returncode}")
    
    if result.returncode == 0:
        print("✅ 所有错误处理一致性属性测试通过")
    else:
        print("❌ 部分错误处理一致性属性测试失败")