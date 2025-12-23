"""
API连接性属性测试

使用属性测试验证API连接性的通用正确性属性。
**属性 1: API连接性保证**
**验证需求: 1.1, 1.2, 1.3, 1.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import requests
from unittest.mock import patch, Mock
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse


# 生成策略
valid_url_strategy = st.sampled_from([
    "http://localhost:6000",
    "http://127.0.0.1:6000",
    "http://localhost:8000",
    "https://api.example.com"
])

timeout_strategy = st.integers(min_value=1, max_value=60)

endpoint_strategy = st.sampled_from([
    "/api/monitoring/health/",
    "/api/auth/login/",
    "/api/videos/",
    "/health/",
    "/status/"
])

http_method_strategy = st.sampled_from(["GET", "POST", "PUT", "DELETE"])

status_code_strategy = st.integers(min_value=100, max_value=599)


class TestAPIConnectivityProperties:
    """API连接性属性测试类"""
    
    @given(
        base_url=valid_url_strategy,
        timeout=timeout_strategy
    )
    @settings(max_examples=20, deadline=5000)
    def test_api_client_creation_property(self, base_url, timeout):
        """
        属性测试：API客户端创建的一致性
        
        对于任何有效的URL和超时配置，API客户端应该能够成功创建并具有正确的配置
        **验证需求: 1.1, 1.2**
        """
        # 创建API客户端
        client = APIClient(base_url=base_url, timeout=timeout)
        
        try:
            # 验证客户端属性
            assert client.base_url == base_url.rstrip('/')
            assert client.timeout == timeout
            assert client.session is not None
            assert 'Content-Type' in client.session.headers
            assert 'Accept' in client.session.headers
            assert 'User-Agent' in client.session.headers
            
            # 验证初始认证状态
            assert client.access_token is None
            assert client.refresh_token is None
            assert client.token_expires_at is None
            
        finally:
            client.close()
    
    @given(
        endpoint=endpoint_strategy,
        method=http_method_strategy
    )
    @settings(max_examples=15, deadline=3000)
    def test_url_building_property(self, endpoint, method):
        """
        属性测试：URL构建的一致性
        
        对于任何有效的端点和HTTP方法，URL构建应该产生正确格式的URL
        **验证需求: 1.1**
        """
        config = TestConfigManager()
        client = APIClient(config.get_base_url())
        
        try:
            # 构建URL
            full_url = client._build_url(endpoint)
            
            # 验证URL格式
            assert full_url.startswith(config.get_base_url())
            assert endpoint.lstrip('/') in full_url
            assert not full_url.endswith('//')  # 避免双斜杠
            
            # 验证URL结构
            expected_url = f"{config.get_base_url()}/{endpoint.lstrip('/')}"
            assert full_url == expected_url
            
        finally:
            client.close()
    
    @given(
        status_code=status_code_strategy,
        response_time=st.floats(min_value=0.001, max_value=10.0)
    )
    @settings(max_examples=25, deadline=2000)
    def test_http_response_classification_property(self, status_code, response_time):
        """
        属性测试：HTTP响应分类的正确性
        
        对于任何状态码，HTTPResponse对象应该正确分类响应类型
        **验证需求: 1.3, 1.4**
        """
        # 创建测试响应对象
        response = HTTPResponse(
            status_code=status_code,
            headers={'Content-Type': 'application/json'},
            content=b'{"test": "data"}',
            text='{"test": "data"}',
            json_data={"test": "data"},
            response_time=response_time,
            url="http://test.com/api/"
        )
        
        # 验证响应分类逻辑
        if 200 <= status_code < 300:
            assert response.is_success is True
            assert response.is_client_error is False
            assert response.is_server_error is False
        elif 400 <= status_code < 500:
            assert response.is_success is False
            assert response.is_client_error is True
            assert response.is_server_error is False
        elif 500 <= status_code < 600:
            assert response.is_success is False
            assert response.is_client_error is False
            assert response.is_server_error is True
        else:
            # 其他状态码（1xx, 3xx等）
            assert response.is_success is False
            assert response.is_client_error is False
            assert response.is_server_error is False
        
        # 验证响应时间
        assert response.response_time == response_time
    
    @given(
        access_token=st.text(min_size=10, max_size=100),
        refresh_token=st.text(min_size=10, max_size=100),
        expires_in=st.integers(min_value=60, max_value=86400)
    )
    @settings(max_examples=15, deadline=2000)
    def test_authentication_token_management_property(self, access_token, refresh_token, expires_in):
        """
        属性测试：认证令牌管理的一致性
        
        对于任何有效的令牌，认证设置和清除应该正确管理客户端状态
        **验证需求: 1.2, 1.3**
        """
        config = TestConfigManager()
        client = APIClient(config.get_base_url())
        
        try:
            # 设置认证令牌
            client.set_auth_token(access_token, refresh_token, expires_in)
            
            # 验证令牌设置
            assert client.access_token == access_token
            assert client.refresh_token == refresh_token
            assert client.token_expires_at is not None
            assert 'Authorization' in client.session.headers
            assert client.session.headers['Authorization'] == f'Bearer {access_token}'
            
            # 清除认证
            client.clear_auth()
            
            # 验证令牌清除
            assert client.access_token is None
            assert client.refresh_token is None
            assert client.token_expires_at is None
            assert 'Authorization' not in client.session.headers
            
        finally:
            client.close()
    
    @given(
        retry_count=st.integers(min_value=0, max_value=5),
        retry_delay=st.floats(min_value=0.1, max_value=2.0)
    )
    @settings(max_examples=10, deadline=3000)
    def test_retry_configuration_property(self, retry_count, retry_delay):
        """
        属性测试：重试配置的正确性
        
        对于任何有效的重试配置，客户端应该正确设置重试参数
        **验证需求: 1.4**
        """
        config = TestConfigManager()
        client = APIClient(
            base_url=config.get_base_url(),
            retry_count=retry_count,
            retry_delay=retry_delay
        )
        
        try:
            # 验证重试配置
            assert client.retry_count == retry_count
            assert client.retry_delay == retry_delay
            
            # 验证配置范围
            assert client.retry_count >= 0
            assert client.retry_delay > 0
            
        finally:
            client.close()
    
    @patch('requests.Session.request')
    @given(
        mock_status_code=st.integers(min_value=200, max_value=599),
        mock_response_time=st.floats(min_value=0.001, max_value=5.0)
    )
    @settings(max_examples=20, deadline=3000)
    def test_request_response_consistency_property(self, mock_request, mock_status_code, mock_response_time):
        """
        属性测试：请求响应的一致性
        
        对于任何模拟的HTTP响应，客户端应该正确处理并返回一致的响应对象
        **验证需求: 1.1, 1.2, 1.3, 1.4**
        """
        # 设置Mock响应
        mock_response = Mock()
        mock_response.status_code = mock_status_code
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.content = b'{"status": "test"}'
        mock_response.text = '{"status": "test"}'
        mock_response.json.return_value = {"status": "test"}
        
        # 模拟响应时间
        def mock_request_side_effect(*args, **kwargs):
            import time
            time.sleep(mock_response_time / 1000)  # 转换为毫秒级延迟
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        config = TestConfigManager()
        client = APIClient(config.get_base_url())
        
        try:
            # 发送请求
            response = client.get('/api/test/')
            
            # 验证响应一致性
            assert response.status_code == mock_status_code
            assert response.json_data == {"status": "test"}
            assert response.url.endswith('/api/test/')
            assert response.response_time >= 0
            
            # 验证响应分类与状态码一致
            if 200 <= mock_status_code < 300:
                assert response.is_success is True
            elif 400 <= mock_status_code < 500:
                assert response.is_client_error is True
            elif 500 <= mock_status_code < 600:
                assert response.is_server_error is True
            
        finally:
            client.close()
    
    @given(
        endpoint=endpoint_strategy
    )
    @settings(max_examples=10, deadline=5000)
    def test_connection_error_handling_property(self, endpoint):
        """
        属性测试：连接错误处理的一致性
        
        对于任何端点，当连接到无效URL时，应该抛出适当的异常
        **验证需求: 1.3, 1.4**
        """
        # 使用无效URL
        invalid_client = APIClient("http://invalid-nonexistent-domain-12345.com")
        
        try:
            # 尝试连接应该失败
            with pytest.raises((requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                invalid_client.get(endpoint)
                
        finally:
            invalid_client.close()


# 运行属性测试的辅助函数
def run_connectivity_property_tests():
    """运行连接性属性测试"""
    print("开始运行API连接性属性测试...")
    
    test_class = TestAPIConnectivityProperties()
    
    try:
        print("1. 测试API客户端创建属性...")
        # 这里可以手动调用一些测试用例
        test_class.test_api_client_creation_property("http://localhost:6000", 30)
        print("✅ API客户端创建属性测试通过")
        
        print("2. 测试URL构建属性...")
        test_class.test_url_building_property("/api/test/", "GET")
        print("✅ URL构建属性测试通过")
        
        print("3. 测试HTTP响应分类属性...")
        test_class.test_http_response_classification_property(200, 1.0)
        test_class.test_http_response_classification_property(404, 0.5)
        test_class.test_http_response_classification_property(500, 2.0)
        print("✅ HTTP响应分类属性测试通过")
        
        print("4. 测试认证令牌管理属性...")
        test_class.test_authentication_token_management_property("test_token", "refresh_token", 3600)
        print("✅ 认证令牌管理属性测试通过")
        
        print("5. 测试重试配置属性...")
        test_class.test_retry_configuration_property(3, 1.0)
        print("✅ 重试配置属性测试通过")
        
        print("\n🎉 所有连接性属性测试通过！")
        
    except Exception as e:
        print(f"❌ 属性测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    run_connectivity_property_tests()