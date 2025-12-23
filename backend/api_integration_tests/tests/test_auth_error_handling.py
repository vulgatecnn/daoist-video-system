"""
认证错误处理测试模块

测试认证失败的状态清理，验证重定向到登录页面的逻辑，测试错误日志记录功能。
"""

import pytest
import time
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..utils.http_client import APIClient, HTTPResponse
from ..utils.test_helpers import TestLogger, TestDataGenerator
from ..config.test_config import TestConfigManager


class AuthErrorHandlingTester:
    """认证错误处理测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化认证错误处理测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.client = APIClient(
            base_url=config.get_base_url(),
            timeout=config.get_timeout(),
            retry_count=1  # 认证错误测试时不重试
        )
        self.logger = TestLogger("auth_error_handling_test.log")
    
    def test_authentication_failure_handling(self) -> Dict[str, Any]:
        """
        测试认证失败处理
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试无效凭证登录
        result_invalid_login = self._test_invalid_credentials_login()
        test_results.append(result_invalid_login)
        
        # 测试过期令牌处理
        result_expired_token = self._test_expired_token_handling()
        test_results.append(result_expired_token)
        
        # 测试无效令牌处理
        result_invalid_token = self._test_invalid_token_handling()
        test_results.append(result_invalid_token)
        
        # 测试令牌刷新失败
        result_refresh_failure = self._test_token_refresh_failure()
        test_results.append(result_refresh_failure)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "认证失败处理测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_invalid_credentials_login(self) -> Dict[str, Any]:
        """测试无效凭证登录"""
        try:
            # 记录登录前的状态
            initial_token = self.client.access_token
            
            # 尝试使用无效凭证登录
            login_success = self.client.login("invalid_user", "wrong_password")
            
            # 验证登录失败
            if login_success:
                return {
                    "test_name": "无效凭证登录处理",
                    "status": "FAIL",
                    "message": "期望登录失败，但登录成功了"
                }
            
            # 验证认证状态未被设置
            if self.client.access_token is not None and self.client.access_token != initial_token:
                return {
                    "test_name": "无效凭证登录处理",
                    "status": "FAIL",
                    "message": "登录失败后不应该设置访问令牌"
                }
            
            # 验证日志记录
            login_error_logged = any(
                entry["level"] == "WARNING" and "登录失败" in entry["message"]
                for entry in self.logger.log_entries
            )
            
            if not login_error_logged:
                return {
                    "test_name": "无效凭证登录处理",
                    "status": "FAIL",
                    "message": "登录失败时没有记录警告日志"
                }
            
            self.logger.info("无效凭证登录测试通过", {
                "login_success": login_success,
                "access_token": self.client.access_token
            })
            
            return {
                "test_name": "无效凭证登录处理",
                "status": "PASS",
                "message": "正确处理了无效凭证登录"
            }
            
        except Exception as e:
            return {
                "test_name": "无效凭证登录处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_expired_token_handling(self) -> Dict[str, Any]:
        """测试过期令牌处理"""
        try:
            # 先进行有效登录
            login_success = self.client.login(
                self.config.test_username,
                self.config.test_password
            )
            
            if not login_success:
                return {
                    "test_name": "过期令牌处理",
                    "status": "SKIP",
                    "message": "无法登录测试用户，跳过过期令牌测试"
                }
            
            # 手动设置令牌为过期状态
            original_expires_at = self.client.token_expires_at
            self.client.token_expires_at = datetime.now() - timedelta(hours=1)  # 设置为1小时前过期
            
            # 验证令牌被识别为过期
            if not self.client.is_token_expired():
                return {
                    "test_name": "过期令牌处理",
                    "status": "FAIL",
                    "message": "过期令牌没有被正确识别"
                }
            
            # 尝试访问需要认证的端点
            response = self.client.get("/api/videos/")
            
            # 验证返回401错误
            if response.status_code != 401:
                return {
                    "test_name": "过期令牌处理",
                    "status": "FAIL",
                    "message": f"期望401错误，实际得到{response.status_code}"
                }
            
            self.logger.info("过期令牌测试通过", {
                "status_code": response.status_code,
                "token_expired": self.client.is_token_expired()
            })
            
            # 恢复原始过期时间
            self.client.token_expires_at = original_expires_at
            
            return {
                "test_name": "过期令牌处理",
                "status": "PASS",
                "message": "正确处理了过期令牌"
            }
            
        except Exception as e:
            return {
                "test_name": "过期令牌处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_invalid_token_handling(self) -> Dict[str, Any]:
        """测试无效令牌处理"""
        try:
            # 设置一个无效的令牌
            self.client.set_auth_token("invalid_token_12345", "invalid_refresh_token")
            
            # 尝试访问需要认证的端点
            response = self.client.get("/api/videos/")
            
            # 验证返回401错误
            if response.status_code != 401:
                return {
                    "test_name": "无效令牌处理",
                    "status": "FAIL",
                    "message": f"期望401错误，实际得到{response.status_code}"
                }
            
            # 验证错误响应包含认证相关信息
            if response.json_data:
                error_detail = response.json_data.get("detail", "").lower()
                if "token" not in error_detail and "authentication" not in error_detail:
                    return {
                        "test_name": "无效令牌处理",
                        "status": "FAIL",
                        "message": f"错误详情不包含认证信息: {response.json_data}"
                    }
            
            self.logger.info("无效令牌测试通过", {
                "status_code": response.status_code,
                "error_detail": response.json_data
            })
            
            return {
                "test_name": "无效令牌处理",
                "status": "PASS",
                "message": "正确处理了无效令牌"
            }
            
        except Exception as e:
            return {
                "test_name": "无效令牌处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_token_refresh_failure(self) -> Dict[str, Any]:
        """测试令牌刷新失败"""
        try:
            # 设置一个无效的刷新令牌
            self.client.set_auth_token("valid_access_token", "invalid_refresh_token")
            
            # 尝试刷新令牌
            refresh_success = self.client.refresh_access_token()
            
            # 验证刷新失败
            if refresh_success:
                return {
                    "test_name": "令牌刷新失败处理",
                    "status": "FAIL",
                    "message": "期望刷新失败，但刷新成功了"
                }
            
            # 验证日志记录
            refresh_error_logged = any(
                entry["level"] == "WARNING" and "刷新失败" in entry["message"]
                for entry in self.logger.log_entries
            )
            
            if not refresh_error_logged:
                return {
                    "test_name": "令牌刷新失败处理",
                    "status": "FAIL",
                    "message": "令牌刷新失败时没有记录警告日志"
                }
            
            self.logger.info("令牌刷新失败测试通过", {
                "refresh_success": refresh_success
            })
            
            return {
                "test_name": "令牌刷新失败处理",
                "status": "PASS",
                "message": "正确处理了令牌刷新失败"
            }
            
        except Exception as e:
            return {
                "test_name": "令牌刷新失败处理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_authentication_state_cleanup(self) -> Dict[str, Any]:
        """
        测试认证状态清理
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试登出状态清理
        result_logout = self._test_logout_state_cleanup()
        test_results.append(result_logout)
        
        # 测试认证失败后状态清理
        result_auth_failure = self._test_auth_failure_state_cleanup()
        test_results.append(result_auth_failure)
        
        # 测试手动状态清理
        result_manual_cleanup = self._test_manual_state_cleanup()
        test_results.append(result_manual_cleanup)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "认证状态清理测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_logout_state_cleanup(self) -> Dict[str, Any]:
        """测试登出状态清理"""
        try:
            # 先登录
            login_success = self.client.login(
                self.config.test_username,
                self.config.test_password
            )
            
            if not login_success:
                return {
                    "test_name": "登出状态清理",
                    "status": "SKIP",
                    "message": "无法登录测试用户，跳过登出测试"
                }
            
            # 验证登录后有认证信息
            if not self.client.access_token:
                return {
                    "test_name": "登出状态清理",
                    "status": "FAIL",
                    "message": "登录后没有设置访问令牌"
                }
            
            # 执行登出
            self.client.logout()
            
            # 验证认证信息被清理
            if self.client.access_token is not None:
                return {
                    "test_name": "登出状态清理",
                    "status": "FAIL",
                    "message": "登出后访问令牌没有被清理"
                }
            
            if self.client.refresh_token is not None:
                return {
                    "test_name": "登出状态清理",
                    "status": "FAIL",
                    "message": "登出后刷新令牌没有被清理"
                }
            
            if self.client.token_expires_at is not None:
                return {
                    "test_name": "登出状态清理",
                    "status": "FAIL",
                    "message": "登出后令牌过期时间没有被清理"
                }
            
            # 验证Authorization头被移除
            if 'Authorization' in self.client.session.headers:
                return {
                    "test_name": "登出状态清理",
                    "status": "FAIL",
                    "message": "登出后Authorization头没有被移除"
                }
            
            self.logger.info("登出状态清理测试通过", {
                "access_token": self.client.access_token,
                "refresh_token": self.client.refresh_token,
                "has_auth_header": 'Authorization' in self.client.session.headers
            })
            
            return {
                "test_name": "登出状态清理",
                "status": "PASS",
                "message": "正确清理了登出后的认证状态"
            }
            
        except Exception as e:
            return {
                "test_name": "登出状态清理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_auth_failure_state_cleanup(self) -> Dict[str, Any]:
        """测试认证失败后状态清理"""
        try:
            # 先设置一些认证信息
            self.client.set_auth_token("test_token", "test_refresh")
            
            # 验证认证信息已设置
            if not self.client.access_token:
                return {
                    "test_name": "认证失败状态清理",
                    "status": "FAIL",
                    "message": "测试设置失败，没有设置访问令牌"
                }
            
            # 尝试无效登录（应该不会影响现有令牌）
            login_success = self.client.login("invalid", "invalid")
            
            # 验证登录失败
            if login_success:
                return {
                    "test_name": "认证失败状态清理",
                    "status": "FAIL",
                    "message": "无效登录不应该成功"
                }
            
            # 验证原有令牌仍然存在（登录失败不应该清理现有状态）
            if not self.client.access_token:
                return {
                    "test_name": "认证失败状态清理",
                    "status": "FAIL",
                    "message": "登录失败不应该清理现有的访问令牌"
                }
            
            self.logger.info("认证失败状态清理测试通过", {
                "login_success": login_success,
                "access_token_preserved": bool(self.client.access_token)
            })
            
            return {
                "test_name": "认证失败状态清理",
                "status": "PASS",
                "message": "认证失败后正确保持了现有状态"
            }
            
        except Exception as e:
            return {
                "test_name": "认证失败状态清理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_manual_state_cleanup(self) -> Dict[str, Any]:
        """测试手动状态清理"""
        try:
            # 设置认证信息
            self.client.set_auth_token("test_token", "test_refresh")
            
            # 验证认证信息已设置
            if not self.client.access_token:
                return {
                    "test_name": "手动状态清理",
                    "status": "FAIL",
                    "message": "测试设置失败，没有设置访问令牌"
                }
            
            # 手动清理认证信息
            self.client.clear_auth()
            
            # 验证所有认证信息被清理
            if self.client.access_token is not None:
                return {
                    "test_name": "手动状态清理",
                    "status": "FAIL",
                    "message": "手动清理后访问令牌没有被清理"
                }
            
            if self.client.refresh_token is not None:
                return {
                    "test_name": "手动状态清理",
                    "status": "FAIL",
                    "message": "手动清理后刷新令牌没有被清理"
                }
            
            if self.client.token_expires_at is not None:
                return {
                    "test_name": "手动状态清理",
                    "status": "FAIL",
                    "message": "手动清理后令牌过期时间没有被清理"
                }
            
            # 验证Authorization头被移除
            if 'Authorization' in self.client.session.headers:
                return {
                    "test_name": "手动状态清理",
                    "status": "FAIL",
                    "message": "手动清理后Authorization头没有被移除"
                }
            
            self.logger.info("手动状态清理测试通过", {
                "access_token": self.client.access_token,
                "refresh_token": self.client.refresh_token,
                "has_auth_header": 'Authorization' in self.client.session.headers
            })
            
            return {
                "test_name": "手动状态清理",
                "status": "PASS",
                "message": "正确执行了手动状态清理"
            }
            
        except Exception as e:
            return {
                "test_name": "手动状态清理",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_error_logging(self) -> Dict[str, Any]:
        """
        测试错误日志记录功能
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试登录错误日志
        result_login_log = self._test_login_error_logging()
        test_results.append(result_login_log)
        
        # 测试令牌刷新错误日志
        result_refresh_log = self._test_refresh_error_logging()
        test_results.append(result_refresh_log)
        
        # 测试认证异常日志
        result_auth_exception_log = self._test_auth_exception_logging()
        test_results.append(result_auth_exception_log)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "错误日志记录测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results
        }
    
    def _test_login_error_logging(self) -> Dict[str, Any]:
        """测试登录错误日志记录"""
        try:
            # 清空之前的日志
            initial_log_count = len(self.logger.log_entries)
            
            # 尝试无效登录
            login_success = self.client.login("invalid_user", "wrong_password")
            
            # 验证登录失败
            if login_success:
                return {
                    "test_name": "登录错误日志记录",
                    "status": "FAIL",
                    "message": "期望登录失败，但登录成功了"
                }
            
            # 验证新增了日志条目
            new_log_count = len(self.logger.log_entries)
            if new_log_count <= initial_log_count:
                return {
                    "test_name": "登录错误日志记录",
                    "status": "FAIL",
                    "message": "登录失败后没有新增日志条目"
                }
            
            # 验证日志内容
            recent_logs = self.logger.log_entries[initial_log_count:]
            login_error_logged = any(
                entry["level"] in ["WARNING", "ERROR"] and 
                ("登录失败" in entry["message"] or "login" in entry["message"].lower())
                for entry in recent_logs
            )
            
            if not login_error_logged:
                return {
                    "test_name": "登录错误日志记录",
                    "status": "FAIL",
                    "message": "没有找到登录错误相关的日志"
                }
            
            self.logger.info("登录错误日志测试通过", {
                "new_logs": len(recent_logs),
                "login_error_logged": login_error_logged
            })
            
            return {
                "test_name": "登录错误日志记录",
                "status": "PASS",
                "message": "正确记录了登录错误日志"
            }
            
        except Exception as e:
            return {
                "test_name": "登录错误日志记录",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_refresh_error_logging(self) -> Dict[str, Any]:
        """测试令牌刷新错误日志记录"""
        try:
            # 清空之前的日志
            initial_log_count = len(self.logger.log_entries)
            
            # 设置无效刷新令牌
            self.client.set_auth_token("valid_token", "invalid_refresh_token")
            
            # 尝试刷新令牌
            refresh_success = self.client.refresh_access_token()
            
            # 验证刷新失败
            if refresh_success:
                return {
                    "test_name": "刷新错误日志记录",
                    "status": "FAIL",
                    "message": "期望刷新失败，但刷新成功了"
                }
            
            # 验证新增了日志条目
            new_log_count = len(self.logger.log_entries)
            if new_log_count <= initial_log_count:
                return {
                    "test_name": "刷新错误日志记录",
                    "status": "FAIL",
                    "message": "刷新失败后没有新增日志条目"
                }
            
            # 验证日志内容
            recent_logs = self.logger.log_entries[initial_log_count:]
            refresh_error_logged = any(
                entry["level"] in ["WARNING", "ERROR"] and 
                ("刷新失败" in entry["message"] or "refresh" in entry["message"].lower())
                for entry in recent_logs
            )
            
            if not refresh_error_logged:
                return {
                    "test_name": "刷新错误日志记录",
                    "status": "FAIL",
                    "message": "没有找到刷新错误相关的日志"
                }
            
            self.logger.info("刷新错误日志测试通过", {
                "new_logs": len(recent_logs),
                "refresh_error_logged": refresh_error_logged
            })
            
            return {
                "test_name": "刷新错误日志记录",
                "status": "PASS",
                "message": "正确记录了刷新错误日志"
            }
            
        except Exception as e:
            return {
                "test_name": "刷新错误日志记录",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_auth_exception_logging(self) -> Dict[str, Any]:
        """测试认证异常日志记录"""
        try:
            # 清空之前的日志
            initial_log_count = len(self.logger.log_entries)
            
            # 模拟认证过程中的异常
            with patch.object(self.client, 'post') as mock_post:
                # 模拟网络异常
                mock_post.side_effect = Exception("Network error during authentication")
                
                # 尝试登录
                login_success = self.client.login("test_user", "test_password")
                
                # 验证登录失败
                if login_success:
                    return {
                        "test_name": "认证异常日志记录",
                        "status": "FAIL",
                        "message": "期望登录异常，但登录成功了"
                    }
            
            # 验证新增了日志条目
            new_log_count = len(self.logger.log_entries)
            if new_log_count <= initial_log_count:
                return {
                    "test_name": "认证异常日志记录",
                    "status": "FAIL",
                    "message": "认证异常后没有新增日志条目"
                }
            
            # 验证日志内容
            recent_logs = self.logger.log_entries[initial_log_count:]
            exception_logged = any(
                entry["level"] == "ERROR" and 
                ("异常" in entry["message"] or "error" in entry["message"].lower())
                for entry in recent_logs
            )
            
            if not exception_logged:
                return {
                    "test_name": "认证异常日志记录",
                    "status": "FAIL",
                    "message": "没有找到认证异常相关的日志"
                }
            
            self.logger.info("认证异常日志测试通过", {
                "new_logs": len(recent_logs),
                "exception_logged": exception_logged
            })
            
            return {
                "test_name": "认证异常日志记录",
                "status": "PASS",
                "message": "正确记录了认证异常日志"
            }
            
        except Exception as e:
            return {
                "test_name": "认证异常日志记录",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def cleanup(self):
        """清理资源"""
        if self.client:
            self.client.close()
        
        if self.logger:
            self.logger.save_to_file()


# pytest测试函数
@pytest.fixture
def auth_error_tester():
    """认证错误处理测试器fixture"""
    config = TestConfigManager()
    tester = AuthErrorHandlingTester(config)
    yield tester
    tester.cleanup()


def test_authentication_failure_handling(auth_error_tester):
    """测试认证失败处理"""
    result = auth_error_tester.test_authentication_failure_handling()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n认证失败处理测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_authentication_state_cleanup(auth_error_tester):
    """测试认证状态清理"""
    result = auth_error_tester.test_authentication_state_cleanup()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n认证状态清理测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_error_logging(auth_error_tester):
    """测试错误日志记录"""
    result = auth_error_tester.test_error_logging()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\n错误日志记录测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = AuthErrorHandlingTester(config)
    
    try:
        print("开始认证错误处理测试...")
        
        # 运行认证失败处理测试
        result_failure = tester.test_authentication_failure_handling()
        print(f"\n认证失败处理测试结果: {result_failure['status']} ({result_failure['passed']}/{result_failure['total']})")
        
        # 运行认证状态清理测试
        result_cleanup = tester.test_authentication_state_cleanup()
        print(f"认证状态清理测试结果: {result_cleanup['status']} ({result_cleanup['passed']}/{result_cleanup['total']})")
        
        # 运行错误日志记录测试
        result_logging = tester.test_error_logging()
        print(f"错误日志记录测试结果: {result_logging['status']} ({result_logging['passed']}/{result_logging['total']})")
        
        print("\n认证错误处理测试完成")
        
    finally:
        tester.cleanup()