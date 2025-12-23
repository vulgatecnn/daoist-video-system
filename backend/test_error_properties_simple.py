"""
简化的错误处理属性测试

验证核心的错误处理一致性属性
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api_integration_tests'))

from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
import requests

from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.config.test_config import TestConfigManager


@given(status_code=st.integers(min_value=400, max_value=599))
@settings(max_examples=20, deadline=10000)
def test_error_status_code_classification_property(status_code):
    """
    **Feature: api-integration-testing, Property 7: 错误状态码分类一致性**
    
    *对于任何* 4xx或5xx状态码，客户端应该正确分类为客户端错误或服务器错误
    """
    config = TestConfigManager()
    client = APIClient(base_url="http://test.com", timeout=5, retry_count=1)
    
    try:
        with patch.object(client, '_make_request') as mock_request:
            mock_response = HTTPResponse(
                status_code=status_code,
                headers={"Content-Type": "application/json"},
                content=b'{"error": "test error"}',
                text='{"error": "test error"}',
                json_data={"error": "test error"},
                response_time=0.1,
                url="http://test.com/api/test/"
            )
            
            mock_request.return_value = mock_response
            response = client.get("/api/test/")
            
            # 属性验证：状态码正确分类
            if 400 <= status_code <= 499:
                assert response.is_client_error, f"4xx错误{status_code}应该被识别为客户端错误"
                assert not response.is_server_error, f"4xx错误{status_code}不应该被识别为服务器错误"
            elif 500 <= status_code <= 599:
                assert response.is_server_error, f"5xx错误{status_code}应该被识别为服务器错误"
                assert not response.is_client_error, f"5xx错误{status_code}不应该被识别为客户端错误"
            
            # 属性验证：错误响应不被认为是成功
            assert not response.is_success, f"错误状态码{status_code}不应该被认为是成功"
            
            print(f"✅ 状态码 {status_code} 分类正确")
    
    finally:
        client.close()


@given(
    error_type=st.sampled_from([
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException
    ]),
    error_message=st.text(min_size=1, max_size=50)
)
@settings(max_examples=15, deadline=10000)
def test_network_error_exception_handling_property(error_type, error_message):
    """
    **Feature: api-integration-testing, Property 7: 网络错误异常处理一致性**
    
    *对于任何* 网络错误，客户端应该正确抛出相应的异常类型
    """
    config = TestConfigManager()
    client = APIClient(base_url="http://test.com", timeout=5, retry_count=1)
    
    try:
        with patch.object(client.session, 'request') as mock_request:
            mock_request.side_effect = error_type(error_message)
            
            # 执行请求，期望抛出异常
            try:
                client.get("/api/test/")
                assert False, f"期望抛出{error_type.__name__}异常，但没有抛出"
            except error_type as e:
                # 属性验证：异常类型正确
                assert isinstance(e, error_type), f"应该抛出{error_type.__name__}异常"
                assert error_message in str(e), f"异常消息应该包含原始错误信息"
                print(f"✅ {error_type.__name__} 异常处理正确")
            except Exception as e:
                assert False, f"期望抛出{error_type.__name__}，实际抛出{type(e).__name__}: {str(e)}"
    
    finally:
        client.close()


if __name__ == "__main__":
    print("开始简化的错误处理属性测试...")
    
    # 运行属性测试
    try:
        print("\n1. 测试错误状态码分类...")
        test_error_status_code_classification_property()
        
        print("\n2. 测试网络错误异常处理...")
        test_network_error_exception_handling_property()
        
        print("\n✅ 所有错误处理属性测试通过")
        
    except Exception as e:
        print(f"\n❌ 属性测试失败: {str(e)}")
        import traceback
        traceback.print_exc()