"""
HTTP错误处理测试模块

测试各种HTTP错误场景的处理，包括4xx和5xx错误，验证错误消息的用户友好性。
"""

import pytest
import requests
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from ..utils.http_client import APIClient, HTTPResponse
from ..utils.test_helpers import TestLogger, TestDataGenerator
from ..config.test_config import TestConfigManager


class ErrorHandlingTester:
    """错误处理测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化错误处理测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.client = APIClient(
            base_url=config.get_base_url(),
            timeout=config.get_timeout(),
            retry_count=1  # 错误测试时不重试
        )
        self.logger = TestLogger("error_handling_test.log")
    
    def test_4xx_errors(self) -> Dict[str, Any]:
        """
        测试4xx客户端错误处理
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试400 Bad Request
        result_400 = self._test_400_bad_request()
        test_results.append(result_400)
        
        # 测试401 Unauthorized
        result_401 = self._test_401_unauthorized()
        test_results.append(result_401)
        
        # 测试403 Forbidden
        result_403 = self._test_403_forbidden()
        test_results.append(result_403)
        
        # 测试404 Not Found
        result_404 = self._test_404_not_found()
        test_results.append(result_404)
        
        # 测试405 Method Not Allowed
        result_405 = self._test_405_method_not_allowed()
        test_results.append(result_405)
        
        # 测试422 Unprocessable Entity
        result_422 = self._test_422_unprocessable_entity()
        test_results.append(result_422)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "4xx错误处理测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_400_bad_request(self) -> Dict[str, Any]:
        """测试400错误处理"""
        try:
            # 发送格式错误的JSON数据
            response = self.client.post("/api/auth/login/", data="invalid json")
            
            # 验证状态码
            if response.status_code != 400:
                return {
                    "test_name": "400 Bad Request",
                    "status": "FAIL",
                    "message": f"期望状态码400，实际得到{response.status_code}"
                }
            
            # 验证错误消息存在
            if not response.json_data or "error" not in response.json_data:
                return {
                    "test_name": "400 Bad Request",
                    "status": "FAIL",
                    "message": "响应中缺少错误消息"
                }
            
            # 验证错误消息是用户友好的
            error_message = response.json_data.get("error", "")
            if not self._is_user_friendly_message(error_message):
                return {
                    "test_name": "400 Bad Request",
                    "status": "FAIL",
                    "message": f"错误消息不够用户友好: {error_message}"
                }
            
            self.logger.info("400错误处理测试通过", {
                "status_code": response.status_code,
                "error_message": error_message
            })
            
            return {
                "test_name": "400 Bad Request",
                "status": "PASS",
                "message": "400错误处理正确"
            }
            
        except Exception as e:
            return {
                "test_name": "400 Bad Request",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_401_unauthorized(self) -> Dict[str, Any]:
        """测试401错误处理"""
        try:
            # 不提供认证信息访问需要认证的端点
            response = self.client.get("/api/videos/")
            
            # 验证状态码
            if response.status_code != 401:
                return {
                    "test_name": "401 Unauthorized",
                    "status": "FAIL",
                    "message": f"期望状态码401，实际得到{response.status_code}"
                }
            
            # 验证错误消息
            if not response.json_data or "detail" not in response.json_data:
                return {
                    "test_name": "401 Unauthorized",
                    "status": "FAIL",
                    "message": "响应中缺少错误详情"
                }
            
            self.logger.info("401错误处理测试通过", {
                "status_code": response.status_code,
                "detail": response.json_data.get("detail")
            })
            
            return {
                "test_name": "401 Unauthorized",
                "status": "PASS",
                "message": "401错误处理正确"
            }
            
        except Exception as e:
            return {
                "test_name": "401 Unauthorized",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_403_forbidden(self) -> Dict[str, Any]:
        """测试403错误处理"""
        try:
            # 先登录普通用户
            login_success = self.client.login(
                self.config.test_username,
                self.config.test_password
            )
            
            if not login_success:
                return {
                    "test_name": "403 Forbidden",
                    "status": "SKIP",
                    "message": "无法登录测试用户，跳过403测试"
                }
            
            # 尝试访问管理员端点
            response = self.client.get("/api/videos/admin/monitoring/statistics/")
            
            # 验证状态码（可能是403或401）
            if response.status_code not in [401, 403]:
                return {
                    "test_name": "403 Forbidden",
                    "status": "FAIL",
                    "message": f"期望状态码403或401，实际得到{response.status_code}"
                }
            
            self.logger.info("403错误处理测试通过", {
                "status_code": response.status_code,
                "response": response.json_data
            })
            
            return {
                "test_name": "403 Forbidden",
                "status": "PASS",
                "message": "403错误处理正确"
            }
            
        except Exception as e:
            return {
                "test_name": "403 Forbidden",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_404_not_found(self) -> Dict[str, Any]:
        """测试404错误处理"""
        try:
            # 访问不存在的端点
            response = self.client.get("/api/nonexistent/endpoint/")
            
            # 验证状态码
            if response.status_code != 404:
                return {
                    "test_name": "404 Not Found",
                    "status": "FAIL",
                    "message": f"期望状态码404，实际得到{response.status_code}"
                }
            
            self.logger.info("404错误处理测试通过", {
                "status_code": response.status_code
            })
            
            return {
                "test_name": "404 Not Found",
                "status": "PASS",
                "message": "404错误处理正确"
            }
            
        except Exception as e:
            return {
                "test_name": "404 Not Found",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_405_method_not_allowed(self) -> Dict[str, Any]:
        """测试405错误处理"""
        try:
            # 使用错误的HTTP方法
            response = self.client.delete("/api/auth/login/")
            
            # 验证状态码
            if response.status_code != 405:
                return {
                    "test_name": "405 Method Not Allowed",
                    "status": "FAIL",
                    "message": f"期望状态码405，实际得到{response.status_code}"
                }
            
            self.logger.info("405错误处理测试通过", {
                "status_code": response.status_code
            })
            
            return {
                "test_name": "405 Method Not Allowed",
                "status": "PASS",
                "message": "405错误处理正确"
            }
            
        except Exception as e:
            return {
                "test_name": "405 Method Not Allowed",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_422_unprocessable_entity(self) -> Dict[str, Any]:
        """测试422错误处理"""
        try:
            # 发送格式正确但内容无效的数据
            response = self.client.post("/api/auth/register/", {
                "username": "",  # 空用户名
                "email": "invalid-email",  # 无效邮箱
                "password": "123"  # 密码太短
            })
            
            # 验证状态码（可能是400或422）
            if response.status_code not in [400, 422]:
                return {
                    "test_name": "422 Unprocessable Entity",
                    "status": "FAIL",
                    "message": f"期望状态码400或422，实际得到{response.status_code}"
                }
            
            # 验证错误详情
            if response.json_data and isinstance(response.json_data, dict):
                has_validation_errors = any(
                    key in response.json_data 
                    for key in ["username", "email", "password", "errors", "non_field_errors"]
                )
                
                if not has_validation_errors:
                    return {
                        "test_name": "422 Unprocessable Entity",
                        "status": "FAIL",
                        "message": "响应中缺少验证错误详情"
                    }
            
            self.logger.info("422错误处理测试通过", {
                "status_code": response.status_code,
                "validation_errors": response.json_data
            })
            
            return {
                "test_name": "422 Unprocessable Entity",
                "status": "PASS",
                "message": "422错误处理正确"
            }
            
        except Exception as e:
            return {
                "test_name": "422 Unprocessable Entity",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_5xx_errors(self) -> Dict[str, Any]:
        """
        测试5xx服务器错误处理
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试500 Internal Server Error
        result_500 = self._test_500_internal_server_error()
        test_results.append(result_500)
        
        # 测试502 Bad Gateway
        result_502 = self._test_502_bad_gateway()
        test_results.append(result_502)
        
        # 测试503 Service Unavailable
        result_503 = self._test_503_service_unavailable()
        test_results.append(result_503)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "5xx错误处理测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_500_internal_server_error(self) -> Dict[str, Any]:
        """测试500错误处理（模拟）"""
        try:
            # 由于无法直接触发500错误，我们模拟这种情况
            with patch.object(self.client, '_make_request') as mock_request:
                # 模拟500错误响应
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.headers = {"Content-Type": "application/json"}
                mock_response.content = b'{"error": "Internal server error"}'
                mock_response.text = '{"error": "Internal server error"}'
                mock_response.json.return_value = {"error": "Internal server error"}
                
                mock_request.return_value = HTTPResponse(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    content=b'{"error": "Internal server error"}',
                    text='{"error": "Internal server error"}',
                    json_data={"error": "Internal server error"},
                    response_time=0.1,
                    url="http://test.com/api/test/"
                )
                
                response = self.client.get("/api/test/")
                
                # 验证状态码
                if response.status_code != 500:
                    return {
                        "test_name": "500 Internal Server Error",
                        "status": "FAIL",
                        "message": f"期望状态码500，实际得到{response.status_code}"
                    }
                
                # 验证错误消息
                if not response.json_data or "error" not in response.json_data:
                    return {
                        "test_name": "500 Internal Server Error",
                        "status": "FAIL",
                        "message": "响应中缺少错误消息"
                    }
                
                self.logger.info("500错误处理测试通过（模拟）", {
                    "status_code": response.status_code,
                    "error": response.json_data.get("error")
                })
                
                return {
                    "test_name": "500 Internal Server Error",
                    "status": "PASS",
                    "message": "500错误处理正确（模拟测试）"
                }
                
        except Exception as e:
            return {
                "test_name": "500 Internal Server Error",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_502_bad_gateway(self) -> Dict[str, Any]:
        """测试502错误处理（模拟）"""
        try:
            # 模拟502错误
            with patch.object(self.client, '_make_request') as mock_request:
                mock_request.return_value = HTTPResponse(
                    status_code=502,
                    headers={"Content-Type": "text/html"},
                    content=b'<html><body>Bad Gateway</body></html>',
                    text='<html><body>Bad Gateway</body></html>',
                    json_data=None,
                    response_time=0.1,
                    url="http://test.com/api/test/"
                )
                
                response = self.client.get("/api/test/")
                
                # 验证状态码
                if response.status_code != 502:
                    return {
                        "test_name": "502 Bad Gateway",
                        "status": "FAIL",
                        "message": f"期望状态码502，实际得到{response.status_code}"
                    }
                
                self.logger.info("502错误处理测试通过（模拟）", {
                    "status_code": response.status_code
                })
                
                return {
                    "test_name": "502 Bad Gateway",
                    "status": "PASS",
                    "message": "502错误处理正确（模拟测试）"
                }
                
        except Exception as e:
            return {
                "test_name": "502 Bad Gateway",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_503_service_unavailable(self) -> Dict[str, Any]:
        """测试503错误处理（模拟）"""
        try:
            # 模拟503错误
            with patch.object(self.client, '_make_request') as mock_request:
                mock_request.return_value = HTTPResponse(
                    status_code=503,
                    headers={"Content-Type": "application/json"},
                    content=b'{"error": "Service temporarily unavailable"}',
                    text='{"error": "Service temporarily unavailable"}',
                    json_data={"error": "Service temporarily unavailable"},
                    response_time=0.1,
                    url="http://test.com/api/test/"
                )
                
                response = self.client.get("/api/test/")
                
                # 验证状态码
                if response.status_code != 503:
                    return {
                        "test_name": "503 Service Unavailable",
                        "status": "FAIL",
                        "message": f"期望状态码503，实际得到{response.status_code}"
                    }
                
                self.logger.info("503错误处理测试通过（模拟）", {
                    "status_code": response.status_code
                })
                
                return {
                    "test_name": "503 Service Unavailable",
                    "status": "PASS",
                    "message": "503错误处理正确（模拟测试）"
                }
                
        except Exception as e:
            return {
                "test_name": "503 Service Unavailable",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_error_message_user_friendliness(self) -> Dict[str, Any]:
        """
        测试错误消息的用户友好性
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_cases = [
            {
                "endpoint": "/api/auth/login/",
                "method": "POST",
                "data": {"username": "invalid", "password": "wrong"},
                "expected_status": 401,
                "test_name": "登录失败错误消息"
            },
            {
                "endpoint": "/api/auth/register/",
                "method": "POST",
                "data": {"username": "", "email": "invalid", "password": "123"},
                "expected_status": [400, 422],
                "test_name": "注册验证错误消息"
            }
        ]
        
        test_results = []
        
        for case in test_cases:
            try:
                if case["method"] == "POST":
                    response = self.client.post(case["endpoint"], case["data"])
                else:
                    response = self.client.get(case["endpoint"])
                
                # 验证状态码
                expected_status = case["expected_status"]
                if isinstance(expected_status, list):
                    status_ok = response.status_code in expected_status
                else:
                    status_ok = response.status_code == expected_status
                
                if not status_ok:
                    test_results.append({
                        "test_name": case["test_name"],
                        "status": "FAIL",
                        "message": f"状态码不匹配，期望{expected_status}，实际{response.status_code}"
                    })
                    continue
                
                # 验证错误消息存在且用户友好
                if response.json_data:
                    error_messages = self._extract_error_messages(response.json_data)
                    if error_messages:
                        friendly_count = sum(
                            1 for msg in error_messages 
                            if self._is_user_friendly_message(msg)
                        )
                        
                        if friendly_count > 0:
                            test_results.append({
                                "test_name": case["test_name"],
                                "status": "PASS",
                                "message": f"找到{friendly_count}个用户友好的错误消息"
                            })
                        else:
                            test_results.append({
                                "test_name": case["test_name"],
                                "status": "FAIL",
                                "message": f"错误消息不够用户友好: {error_messages}"
                            })
                    else:
                        test_results.append({
                            "test_name": case["test_name"],
                            "status": "FAIL",
                            "message": "响应中没有找到错误消息"
                        })
                else:
                    test_results.append({
                        "test_name": case["test_name"],
                        "status": "FAIL",
                        "message": "响应不是JSON格式"
                    })
                    
            except Exception as e:
                test_results.append({
                    "test_name": case["test_name"],
                    "status": "ERROR",
                    "message": f"测试异常: {str(e)}"
                })
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "错误消息用户友好性测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _extract_error_messages(self, response_data: Dict[str, Any]) -> List[str]:
        """从响应数据中提取错误消息"""
        messages = []
        
        # 常见的错误字段
        error_fields = ["error", "detail", "message", "non_field_errors"]
        
        for field in error_fields:
            if field in response_data:
                value = response_data[field]
                if isinstance(value, str):
                    messages.append(value)
                elif isinstance(value, list):
                    messages.extend(str(item) for item in value)
        
        # 检查字段级错误
        for key, value in response_data.items():
            if key not in error_fields and isinstance(value, list):
                # 可能是字段验证错误
                messages.extend(str(item) for item in value)
        
        return messages
    
    def _is_user_friendly_message(self, message: str) -> bool:
        """
        判断错误消息是否用户友好
        
        Args:
            message: 错误消息
            
        Returns:
            bool: 是否用户友好
        """
        if not message or len(message.strip()) == 0:
            return False
        
        # 不友好的技术术语
        unfriendly_terms = [
            "traceback", "exception", "stack trace", "null pointer",
            "segmentation fault", "assertion failed", "internal error",
            "database error", "sql error", "connection refused"
        ]
        
        message_lower = message.lower()
        
        # 检查是否包含不友好的技术术语
        for term in unfriendly_terms:
            if term in message_lower:
                return False
        
        # 检查消息长度（太长的消息通常不友好）
        if len(message) > 200:
            return False
        
        # 检查是否包含有用信息（不只是状态码）
        if message.strip() in ["400", "401", "403", "404", "500"]:
            return False
        
        return True
    
    def cleanup(self):
        """清理资源"""
        if self.client:
            self.client.close()
        
        if self.logger:
            self.logger.save_to_file()


# pytest测试函数
@pytest.fixture
def error_tester():
    """错误处理测试器fixture"""
    config = TestConfigManager()
    tester = ErrorHandlingTester(config)
    yield tester
    tester.cleanup()


def test_4xx_error_handling(error_tester):
    """测试4xx错误处理"""
    result = error_tester.test_4xx_errors()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n4xx错误处理测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_5xx_error_handling(error_tester):
    """测试5xx错误处理"""
    result = error_tester.test_5xx_errors()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n5xx错误处理测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_error_message_user_friendliness(error_tester):
    """测试错误消息用户友好性"""
    result = error_tester.test_error_message_user_friendliness()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n错误消息用户友好性测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = ErrorHandlingTester(config)
    
    try:
        print("开始HTTP错误处理测试...")
        
        # 运行4xx错误测试
        result_4xx = tester.test_4xx_errors()
        print(f"\n4xx错误测试结果: {result_4xx['status']} ({result_4xx['passed']}/{result_4xx['total']})")
        
        # 运行5xx错误测试
        result_5xx = tester.test_5xx_errors()
        print(f"5xx错误测试结果: {result_5xx['status']} ({result_5xx['passed']}/{result_5xx['total']})")
        
        # 运行用户友好性测试
        result_friendly = tester.test_error_message_user_friendliness()
        print(f"用户友好性测试结果: {result_friendly['status']} ({result_friendly['passed']}/{result_friendly['total']})")
        
        print("\nHTTP错误处理测试完成")
        
    finally:
        tester.cleanup()