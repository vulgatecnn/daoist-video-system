"""
性能响应时间保证属性测试模块

使用属性测试验证API性能响应时间保证的正确性属性。
**验证需求: 7.1, 7.2, 7.3**
"""

import pytest
import time
import statistics
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, Any, List, Tuple

from ..utils.http_client import APIClient
from ..utils.test_helpers import TestLogger
from ..config.test_config import TestConfigManager


class PerformancePropertiesTester:
    """性能属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化性能属性测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.client = APIClient(
            base_url=config.get_base_url(),
            timeout=config.get_timeout(),
            retry_count=1
        )
        self.logger = TestLogger("performance_properties_test.log")
        
        # 性能阈值
        self.max_acceptable_response_time = 2.0  # 2秒
        self.max_excellent_response_time = 0.5   # 500ms
        self.min_acceptable_rps = 10             # 最低10 RPS
        
        # 认证状态
        self._authenticated = False
    
    def _ensure_authentication(self) -> bool:
        """确保用户已登录"""
        if self._authenticated:
            return True
        
        success = self.client.login(
            self.config.test_username,
            self.config.test_password
        )
        
        if success:
            self._authenticated = True
            self.logger.info("性能属性测试用户登录成功")
        else:
            self.logger.error("性能属性测试用户登录失败")
        
        return success
    
    def cleanup(self):
        """清理资源"""
        if self.client:
            self.client.close()
        
        if self.logger:
            self.logger.save_to_file()


# 生成测试数据的策略
@st.composite
def api_endpoint_strategy(draw):
    """生成API端点测试数据"""
    endpoints = [
        {"url": "/api/monitoring/health/", "method": "GET", "requires_auth": False, "data": {}},
        {"url": "/api/auth/login/", "method": "POST", "requires_auth": False, "data": {
            "username": "testuser", "password": "testpass123"
        }},
        {"url": "/api/videos/", "method": "GET", "requires_auth": True, "data": {}},
        {"url": "/api/videos/1/", "method": "GET", "requires_auth": True, "data": {}}
    ]
    
    return draw(st.sampled_from(endpoints))


@st.composite
def concurrent_load_strategy(draw):
    """生成并发负载测试数据"""
    concurrent_users = draw(st.integers(min_value=1, max_value=10))
    requests_per_user = draw(st.integers(min_value=1, max_value=5))
    
    return {
        "concurrent_users": concurrent_users,
        "requests_per_user": requests_per_user,
        "total_requests": concurrent_users * requests_per_user
    }


# pytest fixture
@pytest.fixture(scope="module")
def performance_properties_tester():
    """性能属性测试器fixture"""
    config = TestConfigManager()
    tester = PerformancePropertiesTester(config)
    yield tester
    tester.cleanup()


# 属性测试函数

@given(endpoint_data=api_endpoint_strategy())
@settings(max_examples=20, deadline=30000, suppress_health_check=[HealthCheck.too_slow])
def test_property_response_time_guarantee(performance_properties_tester, endpoint_data):
    """
    属性 8: 性能响应时间保证
    
    *对于任何* 正常负载下的API请求，系统应该在规定时间内响应，
    支持大文件的分块上传，并在高负载时返回适当的限流响应
    
    **验证需求: 7.1, 7.2, 7.3**
    """
    tester = performance_properties_tester
    
    # 如果需要认证，先进行认证
    if endpoint_data["requires_auth"]:
        if not tester._ensure_authentication():
            pytest.skip("无法进行认证，跳过需要认证的端点测试")
    
    try:
        # 执行请求并测量响应时间
        start_time = time.time()
        
        if endpoint_data["method"].upper() == "GET":
            response = tester.client.get(endpoint_data["url"], params=endpoint_data["data"])
        elif endpoint_data["method"].upper() == "POST":
            response = tester.client.post(endpoint_data["url"], data=endpoint_data["data"])
        else:
            pytest.skip(f"不支持的HTTP方法: {endpoint_data['method']}")
        
        response_time = time.time() - start_time
        
        # 记录测试信息
        tester.logger.info("响应时间属性测试", {
            "endpoint": endpoint_data["url"],
            "method": endpoint_data["method"],
            "response_time": response_time,
            "status_code": response.status_code,
            "requires_auth": endpoint_data["requires_auth"]
        })
        
        # 属性验证：响应时间应该在可接受范围内
        assert response_time <= tester.max_acceptable_response_time, (
            f"响应时间{response_time:.3f}s超过最大可接受时间{tester.max_acceptable_response_time}s "
            f"(端点: {endpoint_data['url']})"
        )
        
        # 属性验证：成功的请求应该返回2xx状态码
        if response.is_success:
            assert 200 <= response.status_code < 300, (
                f"成功响应的状态码应该在200-299范围内，实际: {response.status_code}"
            )
        
        # 属性验证：如果是健康检查端点，响应时间应该更快
        if endpoint_data["url"] == "/api/monitoring/health/":
            assert response_time <= tester.max_excellent_response_time, (
                f"健康检查端点响应时间{response_time:.3f}s应该小于{tester.max_excellent_response_time}s"
            )
        
        # 属性验证：响应应该包含有效内容
        if response.is_success:
            assert response.content is not None, "成功响应应该包含内容"
            assert len(response.content) > 0, "成功响应内容不应为空"
        
    except Exception as e:
        tester.logger.error("响应时间属性测试异常", {
            "endpoint": endpoint_data["url"],
            "error": str(e)
        })
        raise


@given(load_data=concurrent_load_strategy())
@settings(max_examples=10, deadline=60000, suppress_health_check=[HealthCheck.too_slow])
def test_property_concurrent_performance_consistency(performance_properties_tester, load_data):
    """
    属性 8.1: 并发性能一致性
    
    *对于任何* 并发负载，系统的平均响应时间应该保持在可接受范围内，
    并且成功率应该保持在合理水平
    
    **验证需求: 7.2**
    """
    tester = performance_properties_tester
    
    # 使用健康检查端点进行并发测试（不需要认证）
    endpoint = "/api/monitoring/health/"
    concurrent_users = load_data["concurrent_users"]
    requests_per_user = load_data["requests_per_user"]
    total_requests = load_data["total_requests"]
    
    try:
        import concurrent.futures
        import threading
        
        response_times = []
        success_count = 0
        total_count = 0
        
        def make_request(user_id: int) -> List[Tuple[float, bool]]:
            """执行单个用户的请求"""
            user_results = []
            
            # 为每个用户创建独立的客户端
            user_client = APIClient(
                base_url=tester.config.get_base_url(),
                timeout=tester.config.get_timeout(),
                retry_count=1
            )
            
            try:
                for req_id in range(requests_per_user):
                    start_time = time.time()
                    try:
                        response = user_client.get(endpoint)
                        response_time = time.time() - start_time
                        success = response.is_success
                        user_results.append((response_time, success))
                    except Exception:
                        response_time = time.time() - start_time
                        user_results.append((response_time, False))
            finally:
                user_client.close()
            
            return user_results
        
        # 执行并发请求
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(make_request, user_id): user_id 
                for user_id in range(concurrent_users)
            }
            
            for future in concurrent.futures.as_completed(future_to_user):
                try:
                    user_results = future.result()
                    for response_time, success in user_results:
                        response_times.append(response_time)
                        total_count += 1
                        if success:
                            success_count += 1
                except Exception as e:
                    tester.logger.error("并发请求异常", {"error": str(e)})
        
        total_time = time.time() - start_time
        
        # 计算性能指标
        if response_times:
            avg_response_time = statistics.mean(response_times)
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            actual_rps = total_count / total_time if total_time > 0 else 0
            
            # 记录测试信息
            tester.logger.info("并发性能一致性属性测试", {
                "concurrent_users": concurrent_users,
                "requests_per_user": requests_per_user,
                "total_requests": total_count,
                "avg_response_time": avg_response_time,
                "success_rate": success_rate,
                "actual_rps": actual_rps,
                "total_time": total_time
            })
            
            # 属性验证：平均响应时间应该在可接受范围内
            assert avg_response_time <= tester.max_acceptable_response_time, (
                f"并发负载下平均响应时间{avg_response_time:.3f}s超过最大可接受时间{tester.max_acceptable_response_time}s "
                f"(并发用户: {concurrent_users}, 每用户请求: {requests_per_user})"
            )
            
            # 属性验证：成功率应该保持在合理水平
            min_success_rate = 90.0  # 至少90%成功率
            assert success_rate >= min_success_rate, (
                f"并发负载下成功率{success_rate:.1f}%低于最低要求{min_success_rate}% "
                f"(并发用户: {concurrent_users}, 每用户请求: {requests_per_user})"
            )
            
            # 属性验证：系统应该能够处理合理的请求量
            if concurrent_users <= 5:  # 对于较小的并发量，要求更高的性能
                assert actual_rps >= tester.min_acceptable_rps, (
                    f"实际RPS {actual_rps:.2f}低于最低要求{tester.min_acceptable_rps} "
                    f"(并发用户: {concurrent_users})"
                )
        else:
            pytest.fail("没有收集到响应时间数据")
            
    except Exception as e:
        tester.logger.error("并发性能一致性属性测试异常", {
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "error": str(e)
        })
        raise


@given(file_size=st.integers(min_value=1024, max_value=1024*1024*5))  # 1KB到5MB
@settings(max_examples=5, deadline=120000, suppress_health_check=[HealthCheck.too_slow])
def test_property_upload_performance_scaling(performance_properties_tester, file_size):
    """
    属性 8.2: 文件上传性能扩展性
    
    *对于任何* 合理大小的文件，上传时间应该与文件大小成正比，
    并且上传速度应该保持在可接受范围内
    
    **验证需求: 7.3**
    """
    tester = performance_properties_tester
    
    # 确保认证
    if not tester._ensure_authentication():
        pytest.skip("无法进行认证，跳过文件上传测试")
    
    try:
        # 生成测试文件内容
        test_content = b"A" * file_size
        
        # 准备上传数据
        files = {
            'file': (f'property_test_{file_size}.txt', test_content, 'text/plain')
        }
        
        data = {
            'title': f'属性测试文件_{file_size}',
            'description': f'属性测试文件，大小{file_size}字节'
        }
        
        # 执行上传并测量时间
        start_time = time.time()
        
        try:
            response = tester.client.post("/api/videos/upload/", data=data, files=files)
            upload_time = time.time() - start_time
            
            # 计算上传速度
            upload_speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            
            # 记录测试信息
            tester.logger.info("文件上传性能扩展性属性测试", {
                "file_size": file_size,
                "file_size_mb": file_size / (1024 * 1024),
                "upload_time": upload_time,
                "upload_speed_mbps": upload_speed_mbps,
                "status_code": response.status_code,
                "success": response.is_success
            })
            
            # 属性验证：上传应该在合理时间内完成
            max_upload_time = max(30.0, file_size / (1024 * 1024) * 10)  # 最多每MB 10秒
            assert upload_time <= max_upload_time, (
                f"文件上传时间{upload_time:.2f}s超过最大允许时间{max_upload_time:.2f}s "
                f"(文件大小: {file_size / (1024 * 1024):.2f}MB)"
            )
            
            # 属性验证：上传速度应该在合理范围内
            min_speed_mbps = 0.1  # 最低0.1MB/s
            if file_size >= 1024 * 1024:  # 对于1MB以上的文件
                assert upload_speed_mbps >= min_speed_mbps, (
                    f"上传速度{upload_speed_mbps:.3f}MB/s低于最低要求{min_speed_mbps}MB/s "
                    f"(文件大小: {file_size / (1024 * 1024):.2f}MB)"
                )
            
            # 属性验证：成功的上传应该返回成功状态码
            if response.is_success:
                assert 200 <= response.status_code < 300, (
                    f"成功上传的状态码应该在200-299范围内，实际: {response.status_code}"
                )
                
                # 验证响应包含必要信息
                if response.json_data:
                    # 根据实际API响应格式调整验证逻辑
                    assert isinstance(response.json_data, dict), "上传响应应该是JSON对象"
            
            # 属性验证：上传时间与文件大小的关系应该合理
            # 对于较大的文件，时间增长应该是线性的，而不是指数的
            expected_time_per_mb = 5.0  # 每MB预期最多5秒
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb >= 1.0:
                time_per_mb = upload_time / file_size_mb
                assert time_per_mb <= expected_time_per_mb, (
                    f"每MB上传时间{time_per_mb:.2f}s超过预期{expected_time_per_mb}s "
                    f"(文件大小: {file_size_mb:.2f}MB)"
                )
                
        except Exception as e:
            upload_time = time.time() - start_time
            tester.logger.error("文件上传异常", {
                "file_size": file_size,
                "upload_time": upload_time,
                "error": str(e)
            })
            
            # 对于网络或服务器错误，我们仍然验证时间限制
            max_timeout = tester.config.get_timeout() * 2  # 允许双倍超时时间
            assert upload_time <= max_timeout, (
                f"上传失败时间{upload_time:.2f}s不应超过超时限制{max_timeout}s"
            )
            
            # 重新抛出异常以便进一步处理
            raise
            
    except Exception as e:
        tester.logger.error("文件上传性能扩展性属性测试异常", {
            "file_size": file_size,
            "error": str(e)
        })
        raise


# 运行属性测试的主函数
if __name__ == "__main__":
    # 直接运行属性测试
    import sys
    
    config = TestConfigManager()
    tester = PerformancePropertiesTester(config)
    
    try:
        print("开始性能响应时间保证属性测试...")
        
        # 手动运行一些属性测试示例
        print("\n测试响应时间保证属性...")
        
        # 测试健康检查端点
        endpoint_data = {"url": "/api/monitoring/health/", "method": "GET", "requires_auth": False, "data": {}}
        test_property_response_time_guarantee(tester, endpoint_data)
        print("✅ 健康检查端点响应时间属性测试通过")
        
        # 测试并发性能一致性
        print("\n测试并发性能一致性属性...")
        load_data = {"concurrent_users": 3, "requests_per_user": 2, "total_requests": 6}
        test_property_concurrent_performance_consistency(tester, load_data)
        print("✅ 并发性能一致性属性测试通过")
        
        print("\n性能响应时间保证属性测试完成")
        
    except Exception as e:
        print(f"❌ 属性测试失败: {str(e)}")
        sys.exit(1)
    finally:
        tester.cleanup()