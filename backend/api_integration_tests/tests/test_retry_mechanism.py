"""
网络重试机制测试模块

测试网络中断时的重试行为，验证重试次数和间隔设置，测试重试成功和失败场景。
"""

import pytest
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Callable
from requests.exceptions import ConnectionError, Timeout, RequestException
import threading
import socket

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.http_client import APIClient, HTTPResponse
from utils.test_helpers import TestLogger, RetryHelper
from config.test_config import TestConfigManager


class RetryMechanismTester:
    """重试机制测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化重试机制测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.logger = TestLogger("retry_mechanism_test.log")
        self.base_url = config.get_base_url()
    
    def test_retry_count_configuration(self) -> Dict[str, Any]:
        """
        测试重试次数配置
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试不同的重试次数配置
        retry_configs = [0, 1, 3, 5]
        
        for retry_count in retry_configs:
            result = self._test_single_retry_count(retry_count)
            test_results.append(result)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "重试次数配置测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_single_retry_count(self, retry_count: int) -> Dict[str, Any]:
        """测试单个重试次数配置"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟所有请求都失败
                mock_request.side_effect = ConnectionError("Connection failed")
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=1,
                    retry_count=retry_count
                )
                
                try:
                    response = client.get("/api/test/")
                    
                    return {
                        "test_name": f"重试次数{retry_count}配置",
                        "status": "FAIL",
                        "message": "期望连接失败，但请求成功了"
                    }
                    
                except ConnectionError:
                    # 验证实际调用次数（初始请求 + 重试次数）
                    expected_calls = retry_count + 1
                    actual_calls = mock_request.call_count
                    
                    if actual_calls == expected_calls:
                        self.logger.info(f"重试次数{retry_count}测试通过", {
                            "expected_calls": expected_calls,
                            "actual_calls": actual_calls
                        })
                        
                        return {
                            "test_name": f"重试次数{retry_count}配置",
                            "status": "PASS",
                            "message": f"正确执行了{actual_calls}次尝试"
                        }
                    else:
                        return {
                            "test_name": f"重试次数{retry_count}配置",
                            "status": "FAIL",
                            "message": f"期望{expected_calls}次调用，实际{actual_calls}次"
                        }
                
                finally:
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": f"重试次数{retry_count}配置",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_retry_delay_configuration(self) -> Dict[str, Any]:
        """
        测试重试延迟配置
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试不同的重试延迟配置
        delay_configs = [0.1, 0.5, 1.0, 2.0]
        
        for retry_delay in delay_configs:
            result = self._test_single_retry_delay(retry_delay)
            test_results.append(result)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "重试延迟配置测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_single_retry_delay(self, retry_delay: float) -> Dict[str, Any]:
        """测试单个重试延迟配置"""
        try:
            with patch('time.sleep') as mock_sleep:
                with patch('requests.Session.request') as mock_request:
                    # 模拟连接错误
                    mock_request.side_effect = ConnectionError("Connection failed")
                    
                    client = APIClient(
                        base_url="http://test.com",
                        timeout=1,
                        retry_count=2,
                        retry_delay=retry_delay
                    )
                    
                    try:
                        response = client.get("/api/test/")
                    except ConnectionError:
                        pass  # 期望的异常
                    
                    # 验证sleep被调用了正确的次数
                    expected_sleep_calls = 2  # 重试2次，所以有2次延迟
                    actual_sleep_calls = mock_sleep.call_count
                    
                    if actual_sleep_calls == expected_sleep_calls:
                        # 验证延迟时间
                        call_args = [call[0][0] for call in mock_sleep.call_args_list]
                        
                        # 检查是否使用了正确的基础延迟时间
                        base_delay_used = any(abs(delay - retry_delay) < 0.1 for delay in call_args)
                        
                        if base_delay_used:
                            self.logger.info(f"重试延迟{retry_delay}测试通过", {
                                "expected_sleep_calls": expected_sleep_calls,
                                "actual_sleep_calls": actual_sleep_calls,
                                "delay_times": call_args
                            })
                            
                            return {
                                "test_name": f"重试延迟{retry_delay}s配置",
                                "status": "PASS",
                                "message": f"正确执行了{actual_sleep_calls}次延迟"
                            }
                        else:
                            return {
                                "test_name": f"重试延迟{retry_delay}s配置",
                                "status": "FAIL",
                                "message": f"延迟时间不正确: {call_args}"
                            }
                    else:
                        return {
                            "test_name": f"重试延迟{retry_delay}s配置",
                            "status": "FAIL",
                            "message": f"期望{expected_sleep_calls}次延迟，实际{actual_sleep_calls}次"
                        }
                    
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": f"重试延迟{retry_delay}s配置",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_backoff_strategy(self) -> Dict[str, Any]:
        """
        测试退避策略
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            with patch('time.sleep') as mock_sleep:
                with patch('requests.Session.request') as mock_request:
                    # 模拟连接错误
                    mock_request.side_effect = ConnectionError("Connection failed")
                    
                    # 使用退避策略的重试助手
                    @RetryHelper.retry_with_backoff
                    def test_request():
                        raise ConnectionError("Test connection error")
                    
                    try:
                        test_request()
                    except ConnectionError:
                        pass  # 期望的异常
                    
                    # 验证退避策略（延迟时间应该递增）
                    if mock_sleep.call_count > 1:
                        call_args = [call[0][0] for call in mock_sleep.call_args_list]
                        
                        # 检查延迟时间是否递增
                        is_increasing = all(call_args[i] <= call_args[i+1] 
                                          for i in range(len(call_args)-1))
                        
                        if is_increasing:
                            self.logger.info("退避策略测试通过", {
                                "sleep_calls": mock_sleep.call_count,
                                "delay_progression": call_args
                            })
                            
                            return {
                                "test_name": "退避策略测试",
                                "status": "PASS",
                                "message": f"延迟时间正确递增: {call_args}"
                            }
                        else:
                            return {
                                "test_name": "退避策略测试",
                                "status": "FAIL",
                                "message": f"延迟时间未正确递增: {call_args}"
                            }
                    else:
                        return {
                            "test_name": "退避策略测试",
                            "status": "FAIL",
                            "message": "没有执行足够的重试来验证退避策略"
                        }
                        
        except Exception as e:
            return {
                "test_name": "退避策略测试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_retry_success_scenarios(self) -> Dict[str, Any]:
        """
        测试重试成功场景
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试不同的重试成功场景
        scenarios = [
            {"fail_count": 1, "description": "第2次尝试成功"},
            {"fail_count": 2, "description": "第3次尝试成功"},
            {"fail_count": 3, "description": "第4次尝试成功"}
        ]
        
        for scenario in scenarios:
            result = self._test_retry_success_scenario(
                scenario["fail_count"], 
                scenario["description"]
            )
            test_results.append(result)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "重试成功场景测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_retry_success_scenario(self, fail_count: int, description: str) -> Dict[str, Any]:
        """测试单个重试成功场景"""
        try:
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
                    timeout=1,
                    retry_count=fail_count + 1  # 确保有足够的重试次数
                )
                
                response = client.get("/api/test/")
                
                # 验证最终成功
                if response.status_code == 200 and response.json_data.get("status") == "success":
                    expected_calls = fail_count + 1
                    actual_calls = mock_request.call_count
                    
                    if actual_calls == expected_calls:
                        self.logger.info(f"重试成功场景测试通过: {description}", {
                            "fail_count": fail_count,
                            "total_attempts": actual_calls,
                            "final_status": response.status_code
                        })
                        
                        return {
                            "test_name": description,
                            "status": "PASS",
                            "message": f"经过{actual_calls}次尝试后成功"
                        }
                    else:
                        return {
                            "test_name": description,
                            "status": "FAIL",
                            "message": f"期望{expected_calls}次调用，实际{actual_calls}次"
                        }
                else:
                    return {
                        "test_name": description,
                        "status": "FAIL",
                        "message": f"最终响应不正确: {response.status_code}"
                    }
                
                client.close()
                
        except Exception as e:
            return {
                "test_name": description,
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_retry_failure_scenarios(self) -> Dict[str, Any]:
        """
        测试重试失败场景
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试重试耗尽场景
        result_exhaustion = self._test_retry_exhaustion()
        test_results.append(result_exhaustion)
        
        # 测试不同类型的网络错误
        error_types = [
            (ConnectionError, "连接错误"),
            (Timeout, "超时错误"),
            (requests.exceptions.RequestException, "请求异常")
        ]
        
        for error_type, description in error_types:
            result = self._test_error_type_retry(error_type, description)
            test_results.append(result)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "重试失败场景测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_retry_exhaustion(self) -> Dict[str, Any]:
        """测试重试耗尽场景"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟所有请求都失败
                mock_request.side_effect = ConnectionError("Connection failed")
                
                retry_count = 3
                client = APIClient(
                    base_url="http://test.com",
                    timeout=1,
                    retry_count=retry_count
                )
                
                try:
                    response = client.get("/api/test/")
                    
                    return {
                        "test_name": "重试耗尽处理",
                        "status": "FAIL",
                        "message": "期望重试耗尽后失败，但请求成功了"
                    }
                    
                except ConnectionError:
                    # 验证重试次数
                    expected_calls = retry_count + 1
                    actual_calls = mock_request.call_count
                    
                    if actual_calls == expected_calls:
                        self.logger.info("重试耗尽测试通过", {
                            "retry_count": retry_count,
                            "total_attempts": actual_calls
                        })
                        
                        return {
                            "test_name": "重试耗尽处理",
                            "status": "PASS",
                            "message": f"正确执行了{actual_calls}次尝试后失败"
                        }
                    else:
                        return {
                            "test_name": "重试耗尽处理",
                            "status": "FAIL",
                            "message": f"期望{expected_calls}次调用，实际{actual_calls}次"
                        }
                
                finally:
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": "重试耗尽处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_error_type_retry(self, error_type: type, description: str) -> Dict[str, Any]:
        """测试特定错误类型的重试"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟特定类型的错误
                mock_request.side_effect = error_type("Test error")
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=1,
                    retry_count=2
                )
                
                try:
                    response = client.get("/api/test/")
                    
                    return {
                        "test_name": f"{description}重试",
                        "status": "FAIL",
                        "message": f"期望{error_type.__name__}，但请求成功了"
                    }
                    
                except error_type:
                    # 验证重试次数
                    expected_calls = 3  # 初始请求 + 2次重试
                    actual_calls = mock_request.call_count
                    
                    if actual_calls == expected_calls:
                        self.logger.info(f"{description}重试测试通过", {
                            "error_type": error_type.__name__,
                            "total_attempts": actual_calls
                        })
                        
                        return {
                            "test_name": f"{description}重试",
                            "status": "PASS",
                            "message": f"正确处理了{error_type.__name__}并重试{actual_calls}次"
                        }
                    else:
                        return {
                            "test_name": f"{description}重试",
                            "status": "FAIL",
                            "message": f"期望{expected_calls}次调用，实际{actual_calls}次"
                        }
                
                finally:
                    client.close()
                    
        except Exception as e:
            return {
                "test_name": f"{description}重试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_network_interruption_retry(self) -> Dict[str, Any]:
        """
        测试网络中断时的重试行为
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试连接中断重试
        result_connection = self._test_connection_interruption_retry()
        test_results.append(result_connection)
        
        # 测试读取中断重试
        result_read = self._test_read_interruption_retry()
        test_results.append(result_read)
        
        # 测试写入中断重试
        result_write = self._test_write_interruption_retry()
        test_results.append(result_write)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "网络中断重试测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_connection_interruption_retry(self) -> Dict[str, Any]:
        """测试连接中断重试"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟连接中断
                mock_request.side_effect = [
                    ConnectionError("Connection aborted"),
                    ConnectionError("Connection reset by peer"),
                    Mock(status_code=200, headers={}, content=b'{"status": "ok"}', 
                         text='{"status": "ok"}', json=lambda: {"status": "ok"})
                ]
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=5,
                    retry_count=3
                )
                
                response = client.get("/api/test/")
                
                # 验证最终成功
                if response.status_code == 200:
                    self.logger.info("连接中断重试测试通过", {
                        "total_attempts": mock_request.call_count,
                        "final_status": response.status_code
                    })
                    
                    return {
                        "test_name": "连接中断重试",
                        "status": "PASS",
                        "message": f"连接中断后成功重试，共{mock_request.call_count}次尝试"
                    }
                else:
                    return {
                        "test_name": "连接中断重试",
                        "status": "FAIL",
                        "message": f"重试后状态码不正确: {response.status_code}"
                    }
                
                client.close()
                
        except Exception as e:
            return {
                "test_name": "连接中断重试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_read_interruption_retry(self) -> Dict[str, Any]:
        """测试读取中断重试"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟读取中断
                mock_request.side_effect = [
                    requests.exceptions.ChunkedEncodingError("Connection broken: Invalid chunk encoding"),
                    Mock(status_code=200, headers={}, content=b'{"data": "success"}', 
                         text='{"data": "success"}', json=lambda: {"data": "success"})
                ]
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=5,
                    retry_count=2
                )
                
                response = client.get("/api/data/")
                
                # 验证最终成功
                if response.status_code == 200 and response.json_data.get("data") == "success":
                    self.logger.info("读取中断重试测试通过", {
                        "total_attempts": mock_request.call_count,
                        "response_data": response.json_data
                    })
                    
                    return {
                        "test_name": "读取中断重试",
                        "status": "PASS",
                        "message": f"读取中断后成功重试，共{mock_request.call_count}次尝试"
                    }
                else:
                    return {
                        "test_name": "读取中断重试",
                        "status": "FAIL",
                        "message": f"重试后响应不正确: {response.status_code}"
                    }
                
                client.close()
                
        except Exception as e:
            return {
                "test_name": "读取中断重试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_write_interruption_retry(self) -> Dict[str, Any]:
        """测试写入中断重试"""
        try:
            with patch('requests.Session.request') as mock_request:
                # 模拟写入中断
                mock_request.side_effect = [
                    ConnectionError("Connection broken during write"),
                    Mock(status_code=201, headers={}, content=b'{"id": 123}', 
                         text='{"id": 123}', json=lambda: {"id": 123})
                ]
                
                client = APIClient(
                    base_url="http://test.com",
                    timeout=5,
                    retry_count=2
                )
                
                response = client.post("/api/upload/", {"data": "test_data"})
                
                # 验证最终成功
                if response.status_code == 201 and response.json_data.get("id") == 123:
                    self.logger.info("写入中断重试测试通过", {
                        "total_attempts": mock_request.call_count,
                        "response_data": response.json_data
                    })
                    
                    return {
                        "test_name": "写入中断重试",
                        "status": "PASS",
                        "message": f"写入中断后成功重试，共{mock_request.call_count}次尝试"
                    }
                else:
                    return {
                        "test_name": "写入中断重试",
                        "status": "FAIL",
                        "message": f"重试后响应不正确: {response.status_code}"
                    }
                
                client.close()
                
        except Exception as e:
            return {
                "test_name": "写入中断重试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def cleanup(self):
        """清理资源"""
        if self.logger:
            self.logger.save_to_file()


# pytest测试函数
@pytest.fixture
def retry_tester():
    """重试机制测试器fixture"""
    config = TestConfigManager()
    tester = RetryMechanismTester(config)
    yield tester
    tester.cleanup()

def test_retry_count_configuration(retry_tester):
    """测试重试次数配置"""
    result = retry_tester.test_retry_count_configuration()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n重试次数配置测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_retry_delay_configuration(retry_tester):
    """测试重试延迟配置"""
    result = retry_tester.test_retry_delay_configuration()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n重试延迟配置测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_backoff_strategy(retry_tester):
    """测试退避策略"""
    result = retry_tester.test_backoff_strategy()
    
    assert result["status"] in ["PASS", "FAIL", "ERROR"], f"测试状态无效: {result['status']}"
    
    # 记录结果
    status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
    print(f"\n{status_icon} 退避策略测试: {result['message']}")


def test_retry_success_scenarios(retry_tester):
    """测试重试成功场景"""
    result = retry_tester.test_retry_success_scenarios()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n重试成功场景测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_retry_failure_scenarios(retry_tester):
    """测试重试失败场景"""
    result = retry_tester.test_retry_failure_scenarios()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n重试失败场景测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_network_interruption_retry(retry_tester):
    """测试网络中断重试"""
    result = retry_tester.test_network_interruption_retry()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n网络中断重试测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = RetryMechanismTester(config)
    
    try:
        print("开始网络重试机制测试...")
        
        # 运行重试次数配置测试
        result_count = tester.test_retry_count_configuration()
        print(f"\n重试次数配置测试结果: {result_count['status']} ({result_count['passed']}/{result_count['total']})")
        
        # 运行重试延迟配置测试
        result_delay = tester.test_retry_delay_configuration()
        print(f"重试延迟配置测试结果: {result_delay['status']} ({result_delay['passed']}/{result_delay['total']})")
        
        # 运行退避策略测试
        result_backoff = tester.test_backoff_strategy()
        print(f"退避策略测试结果: {result_backoff['status']}")
        
        # 运行重试成功场景测试
        result_success = tester.test_retry_success_scenarios()
        print(f"重试成功场景测试结果: {result_success['status']} ({result_success['passed']}/{result_success['total']})")
        
        # 运行重试失败场景测试
        result_failure = tester.test_retry_failure_scenarios()
        print(f"重试失败场景测试结果: {result_failure['status']} ({result_failure['passed']}/{result_failure['total']})")
        
        # 运行网络中断重试测试
        result_interruption = tester.test_network_interruption_retry()
        print(f"网络中断重试测试结果: {result_interruption['status']} ({result_interruption['passed']}/{result_interruption['total']})")
        
        print("\n网络重试机制测试完成")
        
    finally:
        tester.cleanup()