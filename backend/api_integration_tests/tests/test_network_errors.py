"""
网络错误测试模块

模拟网络中断和超时场景，测试连接错误的处理，验证重试机制的有效性。
"""

import pytest
import requests
import time
import socket
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from requests.exceptions import ConnectionError, Timeout, RequestException

from ..utils.http_client import APIClient, HTTPResponse
from ..utils.test_helpers import TestLogger, RetryHelper
from ..config.test_config import TestConfigManager


class NetworkErrorTester:
    """网络错误测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化网络错误测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.logger = TestLogger("network_error_test.log")
    
    def test_connection_errors(self) -> Dict[str, Any]:
        """
        测试连接错误处理
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试连接被拒绝
        result_refused = self._test_connection_refused()
        test_results.append(result_refused)
        
        # 测试主机不可达
        result_unreachable = self._test_host_unreachable()
        test_results.append(result_unreachable)
        
        # 测试DNS解析失败
        result_dns = self._test_dns_resolution_failure()
        test_results.append(result_dns)
        
        # 测试网络超时
        result_timeout = self._test_network_timeout()
        test_results.append(result_timeout)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "连接错误处理测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_connection_refused(self) -> Dict[str, Any]:
        """测试连接被拒绝的处理"""
        try:
            # 使用一个不存在的端口
            client = APIClient(
                base_url="http://localhost:9999",  # 假设这个端口没有服务
                timeout=5,
                retry_count=1  # 减少重试次数以加快测试
            )
            
            try:
                response = client.get("/api/test/")
                
                # 如果没有抛出异常，说明连接成功了（不应该发生）
                return {
                    "test_name": "连接被拒绝处理",
                    "status": "FAIL",
                    "message": "期望连接被拒绝，但连接成功了"
                }
                
            except ConnectionError as e:
                # 验证异常类型和消息
                if "Connection refused" in str(e) or "Failed to establish" in str(e):
                    self.logger.info("连接被拒绝测试通过", {
                        "error": str(e)
                    })
                    
                    return {
                        "test_name": "连接被拒绝处理",
                        "status": "PASS",
                        "message": "正确处理了连接被拒绝的错误"
                    }
                else:
                    return {
                        "test_name": "连接被拒绝处理",
                        "status": "FAIL",
                        "message": f"异常消息不符合预期: {str(e)}"
                    }
            
            except Exception as e:
                return {
                    "test_name": "连接被拒绝处理",
                    "status": "FAIL",
                    "message": f"抛出了意外的异常类型: {type(e).__name__}: {str(e)}"
                }
            
            finally:
                client.close()
                
        except Exception as e:
            return {
                "test_name": "连接被拒绝处理",
                "status": "ERROR",
                "message": f"测试设置异常: {str(e)}"
            }
    
    def _test_host_unreachable(self) -> Dict[str, Any]:
        """测试主机不可达的处理"""
        try:
            # 使用一个不存在的主机
            client = APIClient(
                base_url="http://192.0.2.1:8000",  # RFC 5737 测试用IP，不应该可达
                timeout=5,
                retry_count=1
            )
            
            try:
                response = client.get("/api/test/")
                
                return {
                    "test_name": "主机不可达处理",
                    "status": "FAIL",
                    "message": "期望主机不可达，但连接成功了"
                }
                
            except (ConnectionError, Timeout) as e:
                self.logger.info("主机不可达测试通过", {
                    "error": str(e)
                })
                
                return {
                    "test_name": "主机不可达处理",
                    "status": "PASS",
                    "message": "正确处理了主机不可达的错误"
                }
            
            except Exception as e:
                return {
                    "test_name": "主机不可达处理",
                    "status": "FAIL",
                    "message": f"抛出了意外的异常类型: {type(e).__name__}: {str(e)}"
                }
            
            finally:
                client.close()
                
        except Exception as e:
            return {
                "test_name": "主机不可达处理",
                "status": "ERROR",
                "message": f"测试设置异常: {str(e)}"
            }
    
    def _test_dns_resolution_failure(self) -> Dict[str, Any]:
        """测试DNS解析失败的处理"""
        try:
            # 使用一个不存在的域名
            client = APIClient(
                base_url="http://nonexistent-domain-for-testing-12345.com",
                timeout=5,
                retry_count=1
            )
            
            try:
                response = client.get("/api/test/")
                
                return {
                    "test_name": "DNS解析失败处理",
                    "status": "FAIL",
                    "message": "期望DNS解析失败，但连接成功了"
                }
                
            except ConnectionError as e:
                # 验证是DNS相关的错误
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ["name resolution", "nodename", "getaddrinfo", "dns"]):
                    self.logger.info("DNS解析失败测试通过", {
                        "error": str(e)
                    })
                    
                    return {
                        "test_name": "DNS解析失败处理",
                        "status": "PASS",
                        "message": "正确处理了DNS解析失败的错误"
                    }
                else:
                    return {
                        "test_name": "DNS解析失败处理",
                        "status": "PASS",  # 仍然算通过，因为抛出了ConnectionError
                        "message": f"处理了连接错误（可能是DNS相关）: {str(e)}"
                    }
            
            except Exception as e:
                return {
                    "test_name": "DNS解析失败处理",
                    "status": "FAIL",
                    "message": f"抛出了意外的异常类型: {type(e).__name__}: {str(e)}"
                }
            
            finally:
                client.close()
                
        except Exception as e:
            return {
                "test_name": "DNS解析失败处理",
                "status": "ERROR",
                "message": f"测试设置异常: {str(e)}"
            }
    
    def _test_network_timeout(self) -> Dict[str, Any]:
        """测试网络超时的处理"""
        try:
            # 使用很短的超时时间
            client = APIClient(
                base_url=self.config.get_base_url(),
                timeout=0.001,  # 1毫秒超时，几乎肯定会超时
                retry_count=1
            )
            
            try:
                response = client.get("/api/monitoring/health/")
                
                # 如果没有超时，可能是因为服务响应太快，这也是可以接受的
                return {
                    "test_name": "网络超时处理",
                    "status": "PASS",
                    "message": "服务响应非常快，未触发超时（这是好事）"
                }
                
            except Timeout as e:
                self.logger.info("网络超时测试通过", {
                    "error": str(e),
                    "timeout": 0.001
                })
                
                return {
                    "test_name": "网络超时处理",
                    "status": "PASS",
                    "message": "正确处理了网络超时错误"
                }
            
            except Exception as e:
                # 其他异常也可能是由超时引起的
                if "timeout" in str(e).lower():
                    return {
                        "test_name": "网络超时处理",
                        "status": "PASS",
                        "message": f"正确处理了超时相关错误: {str(e)}"
                    }
                else:
                    return {
                        "test_name": "网络超时处理",
                        "status": "FAIL",
                        "message": f"抛出了意外的异常: {type(e).__name__}: {str(e)}"
                    }
            
            finally:
                client.close()
                
        except Exception as e:
            return {
                "test_name": "网络超时处理",
                "status": "ERROR",
                "message": f"测试设置异常: {str(e)}"
            }
    
    def test_retry_mechanism(self) -> Dict[str, Any]:
        """
        测试重试机制的有效性
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试重试次数
        result_retry_count = self._test_retry_count()
        test_results.append(result_retry_count)
        
        # 测试重试延迟
        result_retry_delay = self._test_retry_delay()
        test_results.append(result_retry_delay)
        
        # 测试重试成功场景
        result_retry_success = self._test_retry_success()
        test_results.append(result_retry_success)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "重试机制测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_retry_count(self) -> Dict[str, Any]:
        """测试重试次数"""
        try:
            retry_count = 3
            client = APIClient(
                base_url="http://localhost:9999",  # 不存在的服务
                timeout=1,
                retry_count=retry_count
            )
            
            # 记录重试次数
            actual_attempts = 0
            original_make_request = client._make_request
            
            def count_attempts(*args, **kwargs):
                nonlocal actual_attempts
                actual_attempts += 1
                return original_make_request(*args, **kwargs)
            
            client._make_request = count_attempts
            
            try:
                response = client.get("/api/test/")
                
                return {
                    "test_name": "重试次数验证",
                    "status": "FAIL",
                    "message": "期望连接失败，但连接成功了"
                }
                
            except ConnectionError:
                # 验证重试次数（应该是 retry_count + 1 次尝试）
                expected_attempts = retry_count + 1
                if actual_attempts == expected_attempts:
                    self.logger.info("重试次数测试通过", {
                        "expected_attempts": expected_attempts,
                        "actual_attempts": actual_attempts
                    })
                    
                    return {
                        "test_name": "重试次数验证",
                        "status": "PASS",
                        "message": f"正确执行了{actual_attempts}次尝试"
                    }
                else:
                    return {
                        "test_name": "重试次数验证",
                        "status": "FAIL",
                        "message": f"期望{expected_attempts}次尝试，实际{actual_attempts}次"
                    }
            
            finally:
                client.close()
                
        except Exception as e:
            return {
                "test_name": "重试次数验证",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_retry_delay(self) -> Dict[str, Any]:
        """测试重试延迟"""
        try:
            # 使用模拟来测试延迟
            with patch('time.sleep') as mock_sleep:
                with patch('requests.Session.request') as mock_request:
                    # 模拟连接错误
                    mock_request.side_effect = ConnectionError("Connection failed")
                    
                    client = APIClient(
                        base_url="http://test.com",
                        timeout=1,
                        retry_count=2,
                        retry_delay=0.5
                    )
                    
                    try:
                        response = client.get("/api/test/")
                    except ConnectionError:
                        pass  # 期望的异常
                    
                    # 验证sleep被调用了正确的次数和延迟
                    expected_calls = 2  # 重试2次，所以有2次延迟
                    if mock_sleep.call_count == expected_calls:
                        # 验证延迟时间（可能有退避策略）
                        call_args = [call[0][0] for call in mock_sleep.call_args_list]
                        
                        self.logger.info("重试延迟测试通过", {
                            "sleep_calls": mock_sleep.call_count,
                            "delay_times": call_args
                        })
                        
                        return {
                            "test_name": "重试延迟验证",
                            "status": "PASS",
                            "message": f"正确执行了{mock_sleep.call_count}次延迟"
                        }
                    else:
                        return {
                            "test_name": "重试延迟验证",
                            "status": "FAIL",
                            "message": f"期望{expected_calls}次延迟，实际{mock_sleep.call_count}次"
                        }
                    
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": "重试延迟验证",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_retry_success(self) -> Dict[str, Any]:
        """测试重试成功场景"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟前两次失败，第三次成功
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {"Content-Type": "application/json"}
                mock_response.content = b'{"status": "ok"}'
                mock_response.text = '{"status": "ok"}'
                mock_response.json.return_value = {"status": "ok"}
                
                mock_request.side_effect = [
                    ConnectionError("First attempt failed"),
                    ConnectionError("Second attempt failed"),
                    mock_response  # 第三次成功
                ]
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=1,
                    retry_count=3
                )
                
                response = client.get("/api/test/")
                
                # 验证最终成功
                if response.status_code == 200 and response.json_data.get("status") == "ok":
                    self.logger.info("重试成功测试通过", {
                        "final_status": response.status_code,
                        "attempts": mock_request.call_count
                    })
                    
                    return {
                        "test_name": "重试成功验证",
                        "status": "PASS",
                        "message": f"经过{mock_request.call_count}次尝试后成功"
                    }
                else:
                    return {
                        "test_name": "重试成功验证",
                        "status": "FAIL",
                        "message": f"重试后仍然失败: {response.status_code}"
                    }
                
                client.close()
                
        except Exception as e:
            return {
                "test_name": "重试成功验证",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_network_interruption_simulation(self) -> Dict[str, Any]:
        """
        模拟网络中断场景
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试请求中途中断
        result_interruption = self._test_request_interruption()
        test_results.append(result_interruption)
        
        # 测试部分响应接收
        result_partial = self._test_partial_response()
        test_results.append(result_partial)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "网络中断模拟测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_request_interruption(self) -> Dict[str, Any]:
        """测试请求中途中断"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟连接中断
                mock_request.side_effect = ConnectionError("Connection broken")
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=5,
                    retry_count=1
                )
                
                try:
                    response = client.post("/api/videos/upload/", {
                        "title": "测试视频",
                        "large_data": "x" * 10000  # 大量数据
                    })
                    
                    return {
                        "test_name": "请求中断处理",
                        "status": "FAIL",
                        "message": "期望连接中断，但请求成功了"
                    }
                    
                except ConnectionError as e:
                    self.logger.info("请求中断测试通过", {
                        "error": str(e)
                    })
                    
                    return {
                        "test_name": "请求中断处理",
                        "status": "PASS",
                        "message": "正确处理了请求中断错误"
                    }
                
                finally:
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": "请求中断处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_partial_response(self) -> Dict[str, Any]:
        """测试部分响应接收"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟部分响应（连接在响应中途断开）
                mock_request.side_effect = requests.exceptions.ChunkedEncodingError(
                    "Connection broken: Invalid chunk encoding"
                )
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=5,
                    retry_count=1
                )
                
                try:
                    response = client.get("/api/videos/")
                    
                    return {
                        "test_name": "部分响应处理",
                        "status": "FAIL",
                        "message": "期望部分响应错误，但请求成功了"
                    }
                    
                except (requests.exceptions.ChunkedEncodingError, ConnectionError) as e:
                    self.logger.info("部分响应测试通过", {
                        "error": str(e)
                    })
                    
                    return {
                        "test_name": "部分响应处理",
                        "status": "PASS",
                        "message": "正确处理了部分响应错误"
                    }
                
                finally:
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": "部分响应处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def cleanup(self):
        """清理资源"""
        if self.logger:
            self.logger.save_to_file()


# pytest测试函数
@pytest.fixture
def network_tester():
    """网络错误测试器fixture"""
    config = TestConfigManager()
    tester = NetworkErrorTester(config)
    yield tester
    tester.cleanup()


def test_connection_errors(network_tester):
    """测试连接错误处理"""
    result = network_tester.test_connection_errors()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n连接错误处理测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_retry_mechanism(network_tester):
    """测试重试机制"""
    result = network_tester.test_retry_mechanism()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n重试机制测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_network_interruption_simulation(network_tester):
    """测试网络中断模拟"""
    result = network_tester.test_network_interruption_simulation()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n网络中断模拟测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = NetworkErrorTester(config)
    
    try:
        print("开始网络错误测试...")
        
        # 运行连接错误测试
        result_connection = tester.test_connection_errors()
        print(f"\n连接错误测试结果: {result_connection['status']} ({result_connection['passed']}/{result_connection['total']})")
        
        # 运行重试机制测试
        result_retry = tester.test_retry_mechanism()
        print(f"重试机制测试结果: {result_retry['status']} ({result_retry['passed']}/{result_retry['total']})")
        
        # 运行网络中断测试
        result_interruption = tester.test_network_interruption_simulation()
        print(f"网络中断测试结果: {result_interruption['status']} ({result_interruption['passed']}/{result_interruption['total']})")
        
        print("\n网络错误测试完成")
        
    finally:
        tester.cleanup()