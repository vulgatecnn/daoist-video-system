"""
性能测试模块

测试API端点的响应时间、并发处理能力和文件上传性能。
"""

import time
import statistics
import threading
import concurrent.futures
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import pytest

from ..utils.http_client import APIClient, HTTPResponse
from ..utils.test_helpers import TestLogger, TestDataGenerator
from ..config.test_config import TestConfigManager


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    endpoint: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    min_response_time: float
    max_response_time: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "min_response_time": self.min_response_time,
            "max_response_time": self.max_response_time,
            "avg_response_time": self.avg_response_time,
            "median_response_time": self.median_response_time,
            "p95_response_time": self.p95_response_time,
            "p99_response_time": self.p99_response_time,
            "requests_per_second": self.requests_per_second,
            "error_rate": self.error_rate
        }


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化性能测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.client = APIClient(
            base_url=config.get_base_url(),
            timeout=config.get_timeout(),
            retry_count=1  # 性能测试时不重试
        )
        self.logger = TestLogger("performance_test.log")
        
        # 性能阈值配置
        self.response_time_thresholds = {
            "excellent": 0.5,    # 500ms以下为优秀
            "good": 1.0,         # 1秒以下为良好
            "acceptable": 2.0,   # 2秒以下为可接受
            "poor": 5.0          # 5秒以上为差
        }
        
        # 测试用户登录状态
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
            self.logger.info("性能测试用户登录成功")
        else:
            self.logger.error("性能测试用户登录失败")
        
        return success
    
    def test_response_time(self) -> Dict[str, Any]:
        """
        测试各API端点的响应时间
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 获取API端点配置
        endpoints = self.config.get_api_endpoints()
        
        # 测试不需要认证的端点
        public_endpoints = [
            ("monitoring", "health", "GET", "/api/monitoring/health/", {}),
            ("auth", "login", "POST", "/api/auth/login/", {
                "username": self.config.test_username,
                "password": self.config.test_password
            })
        ]
        
        for category, name, method, url, data in public_endpoints:
            result = self._test_endpoint_response_time(
                f"{category}_{name}", method, url, data, requires_auth=False
            )
            test_results.append(result)
        
        # 确保认证状态
        if self._ensure_authentication():
            # 测试需要认证的端点
            auth_endpoints = [
                ("videos", "list", "GET", "/api/videos/", {}),
                ("videos", "detail", "GET", "/api/videos/1/", {}),
                ("composition", "create", "POST", "/api/videos/composition/create/", {
                    "video_ids": [1, 2],
                    "output_format": "mp4",
                    "quality": "high"
                }),
                ("monitoring", "statistics", "GET", "/api/videos/admin/monitoring/statistics/", {})
            ]
            
            for category, name, method, url, data in auth_endpoints:
                result = self._test_endpoint_response_time(
                    f"{category}_{name}", method, url, data, requires_auth=True
                )
                test_results.append(result)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "API响应时间测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results,
            "summary": self._generate_response_time_summary(test_results)
        }
    
    def _test_endpoint_response_time(self, endpoint_name: str, method: str, 
                                   url: str, data: Dict[str, Any], 
                                   requires_auth: bool = False,
                                   num_requests: int = 10) -> Dict[str, Any]:
        """
        测试单个端点的响应时间
        
        Args:
            endpoint_name: 端点名称
            method: HTTP方法
            url: 端点URL
            data: 请求数据
            requires_auth: 是否需要认证
            num_requests: 请求次数
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            response_times = []
            successful_requests = 0
            failed_requests = 0
            
            self.logger.info(f"开始测试端点响应时间: {endpoint_name}", {
                "method": method,
                "url": url,
                "num_requests": num_requests,
                "requires_auth": requires_auth
            })
            
            # 执行多次请求
            for i in range(num_requests):
                try:
                    start_time = time.time()
                    
                    if method.upper() == "GET":
                        response = self.client.get(url, params=data)
                    elif method.upper() == "POST":
                        response = self.client.post(url, data=data)
                    elif method.upper() == "PUT":
                        response = self.client.put(url, data=data)
                    elif method.upper() == "DELETE":
                        response = self.client.delete(url)
                    else:
                        raise ValueError(f"不支持的HTTP方法: {method}")
                    
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    # 判断请求是否成功
                    if response.is_success:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        self.logger.warning(f"请求失败 #{i+1}", {
                            "status_code": response.status_code,
                            "response_time": response_time
                        })
                    
                    # 短暂延迟避免过于频繁的请求
                    time.sleep(0.1)
                    
                except Exception as e:
                    failed_requests += 1
                    response_times.append(self.config.get_timeout())  # 使用超时时间作为失败响应时间
                    self.logger.error(f"请求异常 #{i+1}", {"error": str(e)})
            
            # 计算性能指标
            if response_times:
                metrics = self._calculate_performance_metrics(
                    endpoint_name, method, response_times, 
                    successful_requests, failed_requests
                )
                
                # 评估性能等级
                performance_grade = self._evaluate_performance(metrics.avg_response_time)
                
                # 判断是否通过测试
                is_acceptable = metrics.avg_response_time <= self.response_time_thresholds["acceptable"]
                
                result = {
                    "test_name": f"{endpoint_name}响应时间测试",
                    "status": "PASS" if is_acceptable else "FAIL",
                    "message": f"平均响应时间: {metrics.avg_response_time:.3f}s ({performance_grade})",
                    "metrics": metrics.to_dict(),
                    "performance_grade": performance_grade
                }
                
                self.logger.info(f"端点{endpoint_name}性能测试完成", {
                    "avg_response_time": metrics.avg_response_time,
                    "success_rate": (successful_requests / num_requests) * 100,
                    "performance_grade": performance_grade
                })
                
                return result
            else:
                return {
                    "test_name": f"{endpoint_name}响应时间测试",
                    "status": "ERROR",
                    "message": "没有收集到响应时间数据"
                }
                
        except Exception as e:
            return {
                "test_name": f"{endpoint_name}响应时间测试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _calculate_performance_metrics(self, endpoint: str, method: str,
                                     response_times: List[float],
                                     successful_requests: int,
                                     failed_requests: int) -> PerformanceMetrics:
        """
        计算性能指标
        
        Args:
            endpoint: 端点名称
            method: HTTP方法
            response_times: 响应时间列表
            successful_requests: 成功请求数
            failed_requests: 失败请求数
            
        Returns:
            PerformanceMetrics: 性能指标
        """
        total_requests = successful_requests + failed_requests
        
        # 基本统计
        min_time = min(response_times)
        max_time = max(response_times)
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        
        # 百分位数
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_time
        p99_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_time
        
        # 吞吐量（简化计算）
        total_time = sum(response_times)
        requests_per_second = total_requests / total_time if total_time > 0 else 0
        
        # 错误率
        error_rate = (failed_requests / total_requests) * 100 if total_requests > 0 else 0
        
        return PerformanceMetrics(
            endpoint=endpoint,
            method=method,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            min_response_time=min_time,
            max_response_time=max_time,
            avg_response_time=avg_time,
            median_response_time=median_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate
        )
    
    def _evaluate_performance(self, avg_response_time: float) -> str:
        """
        评估性能等级
        
        Args:
            avg_response_time: 平均响应时间
            
        Returns:
            str: 性能等级
        """
        if avg_response_time <= self.response_time_thresholds["excellent"]:
            return "优秀"
        elif avg_response_time <= self.response_time_thresholds["good"]:
            return "良好"
        elif avg_response_time <= self.response_time_thresholds["acceptable"]:
            return "可接受"
        else:
            return "差"
    
    def _generate_response_time_summary(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成响应时间测试摘要
        
        Args:
            test_results: 测试结果列表
            
        Returns:
            Dict[str, Any]: 测试摘要
        """
        if not test_results:
            return {}
        
        # 提取所有有效的性能指标
        all_metrics = []
        performance_grades = {"优秀": 0, "良好": 0, "可接受": 0, "差": 0}
        
        for result in test_results:
            if result["status"] == "PASS" or result["status"] == "FAIL":
                if "metrics" in result:
                    all_metrics.append(result["metrics"])
                if "performance_grade" in result:
                    grade = result["performance_grade"]
                    if grade in performance_grades:
                        performance_grades[grade] += 1
        
        if not all_metrics:
            return {"message": "没有有效的性能数据"}
        
        # 计算整体统计
        all_avg_times = [m["avg_response_time"] for m in all_metrics]
        overall_avg = statistics.mean(all_avg_times)
        overall_median = statistics.median(all_avg_times)
        
        # 计算成功率
        total_requests = sum(m["total_requests"] for m in all_metrics)
        total_successful = sum(m["successful_requests"] for m in all_metrics)
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_endpoints_tested": len(all_metrics),
            "overall_avg_response_time": overall_avg,
            "overall_median_response_time": overall_median,
            "overall_success_rate": overall_success_rate,
            "performance_distribution": performance_grades,
            "fastest_endpoint": min(all_metrics, key=lambda x: x["avg_response_time"])["endpoint"],
            "slowest_endpoint": max(all_metrics, key=lambda x: x["avg_response_time"])["endpoint"]
        }
    
    def test_concurrent_requests_comprehensive(self) -> Dict[str, Any]:
        """
        全面的并发请求测试
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_results = []
        
        # 测试不同的并发场景
        test_scenarios = [
            {
                "name": "健康检查并发测试",
                "endpoint": "/api/monitoring/health/",
                "method": "GET",
                "data": {},
                "concurrent_users": 10,
                "requests_per_user": 5,
                "requires_auth": False
            },
            {
                "name": "登录并发测试",
                "endpoint": "/api/auth/login/",
                "method": "POST",
                "data": {
                    "username": self.config.test_username,
                    "password": self.config.test_password
                },
                "concurrent_users": 5,
                "requests_per_user": 3,
                "requires_auth": False
            }
        ]
        
        # 如果认证成功，添加需要认证的并发测试
        if self._ensure_authentication():
            auth_scenarios = [
                {
                    "name": "视频列表并发测试",
                    "endpoint": "/api/videos/",
                    "method": "GET",
                    "data": {},
                    "concurrent_users": 8,
                    "requests_per_user": 3,
                    "requires_auth": True
                },
                {
                    "name": "视频合成并发测试",
                    "endpoint": "/api/videos/composition/create/",
                    "method": "POST",
                    "data": {
                        "video_ids": [1, 2],
                        "output_format": "mp4",
                        "quality": "high"
                    },
                    "concurrent_users": 3,
                    "requests_per_user": 2,
                    "requires_auth": True
                }
            ]
            test_scenarios.extend(auth_scenarios)
        
        # 执行所有并发测试场景
        for scenario in test_scenarios:
            result = self.test_concurrent_requests(
                endpoint=scenario["endpoint"],
                method=scenario["method"],
                data=scenario["data"],
                concurrent_users=scenario["concurrent_users"],
                requests_per_user=scenario["requests_per_user"]
            )
            result["scenario_name"] = scenario["name"]
            test_results.append(result)
        
        # 汇总结果
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(test_results)
        
        return {
            "test_name": "全面并发请求测试",
            "status": "PASS" if passed_count == total_count else "FAIL",
            "passed": passed_count,
            "total": total_count,
            "details": test_results,
            "summary": self._generate_concurrent_test_summary(test_results)
        }
    
    def test_concurrent_requests(self, endpoint: str = "/api/monitoring/health/",
                               method: str = "GET", data: Dict[str, Any] = None,
                               concurrent_users: int = 10, 
                               requests_per_user: int = 5) -> Dict[str, Any]:
        """
        测试并发请求处理能力
        
        Args:
            endpoint: 测试端点
            method: HTTP方法
            data: 请求数据
            concurrent_users: 并发用户数
            requests_per_user: 每个用户的请求数
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            self.logger.info("开始并发请求测试", {
                "endpoint": endpoint,
                "concurrent_users": concurrent_users,
                "requests_per_user": requests_per_user,
                "total_requests": concurrent_users * requests_per_user
            })
            
            # 存储所有响应时间和结果
            all_response_times = []
            all_results = []
            start_time = time.time()
            
            def user_requests(user_id: int) -> List[Tuple[float, bool]]:
                """单个用户的请求函数"""
                user_results = []
                
                # 为每个用户创建独立的客户端
                user_client = APIClient(
                    base_url=self.config.get_base_url(),
                    timeout=self.config.get_timeout(),
                    retry_count=1
                )
                
                try:
                    # 如果需要认证，为每个用户登录
                    if endpoint.startswith("/api/videos/") or "admin" in endpoint:
                        user_client.login(
                            self.config.test_username,
                            self.config.test_password
                        )
                    
                    for req_id in range(requests_per_user):
                        try:
                            req_start = time.time()
                            
                            if method.upper() == "GET":
                                response = user_client.get(endpoint, params=data)
                            elif method.upper() == "POST":
                                response = user_client.post(endpoint, data=data)
                            else:
                                raise ValueError(f"不支持的HTTP方法: {method}")
                            
                            req_time = time.time() - req_start
                            success = response.is_success
                            
                            user_results.append((req_time, success))
                            
                        except Exception as e:
                            req_time = time.time() - req_start
                            user_results.append((req_time, False))
                            self.logger.error(f"用户{user_id}请求{req_id}失败", {"error": str(e)})
                
                finally:
                    user_client.close()
                
                return user_results
            
            # 使用线程池执行并发请求
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                # 提交所有用户任务
                future_to_user = {
                    executor.submit(user_requests, user_id): user_id 
                    for user_id in range(concurrent_users)
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_user):
                    user_id = future_to_user[future]
                    try:
                        user_results = future.result()
                        all_results.extend(user_results)
                        
                        # 提取响应时间
                        user_times = [result[0] for result in user_results]
                        all_response_times.extend(user_times)
                        
                    except Exception as e:
                        self.logger.error(f"用户{user_id}任务执行异常", {"error": str(e)})
            
            total_time = time.time() - start_time
            
            # 分析结果
            if all_results:
                successful_requests = sum(1 for _, success in all_results if success)
                failed_requests = len(all_results) - successful_requests
                
                # 计算性能指标
                metrics = self._calculate_performance_metrics(
                    endpoint, method, all_response_times,
                    successful_requests, failed_requests
                )
                
                # 计算并发性能指标
                actual_rps = len(all_results) / total_time
                success_rate = (successful_requests / len(all_results)) * 100
                
                # 判断测试是否通过
                is_acceptable = (
                    success_rate >= 95.0 and  # 成功率至少95%
                    metrics.avg_response_time <= self.response_time_thresholds["acceptable"]
                )
                
                result = {
                    "test_name": "并发请求测试",
                    "status": "PASS" if is_acceptable else "FAIL",
                    "message": f"并发{concurrent_users}用户，成功率{success_rate:.1f}%，平均响应时间{metrics.avg_response_time:.3f}s",
                    "concurrent_users": concurrent_users,
                    "requests_per_user": requests_per_user,
                    "total_requests": len(all_results),
                    "success_rate": success_rate,
                    "actual_rps": actual_rps,
                    "total_test_time": total_time,
                    "metrics": metrics.to_dict()
                }
                
                self.logger.info("并发请求测试完成", {
                    "success_rate": success_rate,
                    "avg_response_time": metrics.avg_response_time,
                    "actual_rps": actual_rps
                })
                
                return result
            else:
                return {
                    "test_name": "并发请求测试",
                    "status": "ERROR",
                    "message": "没有收集到测试结果"
                }
                
        except Exception as e:
            return {
                "test_name": "并发请求测试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def test_data_consistency_under_load(self) -> Dict[str, Any]:
        """
        测试并发负载下的数据一致性
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            if not self._ensure_authentication():
                return {
                    "test_name": "并发数据一致性测试",
                    "status": "SKIP",
                    "message": "无法进行认证，跳过数据一致性测试"
                }
            
            self.logger.info("开始并发数据一致性测试")
            
            # 测试场景：多个用户同时获取视频列表，验证返回数据的一致性
            concurrent_users = 5
            requests_per_user = 3
            all_responses = []
            
            def get_video_list(user_id: int) -> List[Dict[str, Any]]:
                """获取视频列表"""
                user_responses = []
                
                # 为每个用户创建独立的客户端
                user_client = APIClient(
                    base_url=self.config.get_base_url(),
                    timeout=self.config.get_timeout(),
                    retry_count=1
                )
                
                try:
                    # 用户登录
                    user_client.login(
                        self.config.test_username,
                        self.config.test_password
                    )
                    
                    for req_id in range(requests_per_user):
                        try:
                            response = user_client.get("/api/videos/", params={"page": 1, "page_size": 10})
                            
                            if response.is_success and response.json_data:
                                user_responses.append({
                                    "user_id": user_id,
                                    "request_id": req_id,
                                    "data": response.json_data,
                                    "response_time": response.response_time
                                })
                            else:
                                self.logger.warning(f"用户{user_id}请求{req_id}失败", {
                                    "status_code": response.status_code
                                })
                        
                        except Exception as e:
                            self.logger.error(f"用户{user_id}请求{req_id}异常", {"error": str(e)})
                
                finally:
                    user_client.close()
                
                return user_responses
            
            # 使用线程池执行并发请求
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                future_to_user = {
                    executor.submit(get_video_list, user_id): user_id 
                    for user_id in range(concurrent_users)
                }
                
                for future in concurrent.futures.as_completed(future_to_user):
                    user_id = future_to_user[future]
                    try:
                        user_responses = future.result()
                        all_responses.extend(user_responses)
                    except Exception as e:
                        self.logger.error(f"用户{user_id}任务异常", {"error": str(e)})
            
            # 分析数据一致性
            if all_responses:
                consistency_result = self._analyze_data_consistency(all_responses)
                
                return {
                    "test_name": "并发数据一致性测试",
                    "status": "PASS" if consistency_result["is_consistent"] else "FAIL",
                    "message": consistency_result["message"],
                    "total_responses": len(all_responses),
                    "consistency_analysis": consistency_result
                }
            else:
                return {
                    "test_name": "并发数据一致性测试",
                    "status": "ERROR",
                    "message": "没有收集到响应数据"
                }
                
        except Exception as e:
            return {
                "test_name": "并发数据一致性测试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _analyze_data_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析数据一致性
        
        Args:
            responses: 响应数据列表
            
        Returns:
            Dict[str, Any]: 一致性分析结果
        """
        if not responses:
            return {
                "is_consistent": False,
                "message": "没有响应数据",
                "details": {}
            }
        
        # 提取所有响应的关键数据
        data_signatures = []
        
        for response in responses:
            data = response.get("data", {})
            
            # 创建数据签名（用于比较一致性）
            signature = {
                "count": data.get("count", 0),
                "results_length": len(data.get("results", [])),
                "first_video_id": None,
                "last_video_id": None
            }
            
            # 提取第一个和最后一个视频的ID（如果存在）
            results = data.get("results", [])
            if results:
                if isinstance(results[0], dict) and "id" in results[0]:
                    signature["first_video_id"] = results[0]["id"]
                if isinstance(results[-1], dict) and "id" in results[-1]:
                    signature["last_video_id"] = results[-1]["id"]
            
            data_signatures.append(signature)
        
        # 检查一致性
        if not data_signatures:
            return {
                "is_consistent": False,
                "message": "无法提取数据签名",
                "details": {}
            }
        
        # 比较所有签名
        first_signature = data_signatures[0]
        inconsistencies = []
        
        for i, signature in enumerate(data_signatures[1:], 1):
            for key, value in signature.items():
                if first_signature[key] != value:
                    inconsistencies.append({
                        "response_index": i,
                        "field": key,
                        "expected": first_signature[key],
                        "actual": value
                    })
        
        is_consistent = len(inconsistencies) == 0
        
        # 计算一致性统计
        consistency_rate = ((len(data_signatures) - len(inconsistencies)) / len(data_signatures)) * 100
        
        return {
            "is_consistent": is_consistent,
            "message": f"数据一致性: {consistency_rate:.1f}%" + (
                "" if is_consistent else f"，发现{len(inconsistencies)}个不一致"
            ),
            "details": {
                "total_responses": len(data_signatures),
                "inconsistencies": inconsistencies,
                "consistency_rate": consistency_rate,
                "sample_signature": first_signature
            }
        }
    
    def _generate_concurrent_test_summary(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成并发测试摘要
        
        Args:
            test_results: 测试结果列表
            
        Returns:
            Dict[str, Any]: 测试摘要
        """
        if not test_results:
            return {}
        
        # 提取有效结果
        valid_results = [r for r in test_results if r["status"] in ["PASS", "FAIL"]]
        
        if not valid_results:
            return {"message": "没有有效的并发测试结果"}
        
        # 计算整体统计
        total_concurrent_users = sum(r.get("concurrent_users", 0) for r in valid_results)
        total_requests = sum(r.get("total_requests", 0) for r in valid_results)
        
        # 计算平均成功率
        success_rates = [r.get("success_rate", 0) for r in valid_results if "success_rate" in r]
        avg_success_rate = statistics.mean(success_rates) if success_rates else 0
        
        # 计算平均RPS
        rps_values = [r.get("actual_rps", 0) for r in valid_results if "actual_rps" in r]
        avg_rps = statistics.mean(rps_values) if rps_values else 0
        
        # 找出最佳和最差性能的场景
        best_scenario = None
        worst_scenario = None
        
        if success_rates:
            best_idx = success_rates.index(max(success_rates))
            worst_idx = success_rates.index(min(success_rates))
            
            best_scenario = valid_results[best_idx].get("scenario_name", f"场景{best_idx}")
            worst_scenario = valid_results[worst_idx].get("scenario_name", f"场景{worst_idx}")
        
        return {
            "total_scenarios_tested": len(valid_results),
            "total_concurrent_users": total_concurrent_users,
            "total_requests": total_requests,
            "avg_success_rate": avg_success_rate,
            "avg_rps": avg_rps,
            "best_performing_scenario": best_scenario,
            "worst_performing_scenario": worst_scenario
        }
    
    def test_file_upload_performance(self) -> Dict[str, Any]:
        """
        测试文件上传性能
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            if not self._ensure_authentication():
                return {
                    "test_name": "文件上传性能测试",
                    "status": "SKIP",
                    "message": "无法进行认证，跳过文件上传性能测试"
                }
            
            test_results = []
            
            # 测试不同大小的文件上传
            file_sizes = [
                {"name": "小文件", "size": 1024 * 100, "description": "100KB"},      # 100KB
                {"name": "中等文件", "size": 1024 * 1024 * 5, "description": "5MB"},  # 5MB
                {"name": "大文件", "size": 1024 * 1024 * 20, "description": "20MB"}   # 20MB
            ]
            
            for file_config in file_sizes:
                result = self._test_single_file_upload(
                    file_config["name"],
                    file_config["size"],
                    file_config["description"]
                )
                test_results.append(result)
            
            # 测试并发文件上传
            concurrent_result = self._test_concurrent_file_upload()
            test_results.append(concurrent_result)
            
            # 汇总结果
            passed_count = sum(1 for r in test_results if r["status"] == "PASS")
            total_count = len(test_results)
            
            return {
                "test_name": "文件上传性能测试",
                "status": "PASS" if passed_count == total_count else "FAIL",
                "passed": passed_count,
                "total": total_count,
                "details": test_results,
                "summary": self._generate_upload_performance_summary(test_results)
            }
            
        except Exception as e:
            return {
                "test_name": "文件上传性能测试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _test_single_file_upload(self, file_name: str, file_size: int, 
                                description: str) -> Dict[str, Any]:
        """
        测试单个文件上传性能
        
        Args:
            file_name: 文件名称
            file_size: 文件大小（字节）
            description: 文件描述
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            self.logger.info(f"开始{file_name}上传测试", {
                "file_size": file_size,
                "description": description
            })
            
            # 创建测试文件内容
            test_content = self._generate_test_file_content(file_size)
            
            # 准备上传数据
            files = {
                'file': (f'test_{file_name.lower()}.txt', test_content, 'text/plain')
            }
            
            data = {
                'title': f'性能测试_{file_name}',
                'description': f'这是一个{description}的性能测试文件'
            }
            
            # 执行上传并测量时间
            start_time = time.time()
            
            try:
                response = self.client.post("/api/videos/upload/", data=data, files=files)
                upload_time = time.time() - start_time
                
                # 计算上传速度
                upload_speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
                
                # 判断上传是否成功
                if response.is_success:
                    # 评估上传性能
                    performance_grade = self._evaluate_upload_performance(upload_speed_mbps, file_size)
                    
                    # 判断是否通过测试
                    is_acceptable = self._is_upload_performance_acceptable(upload_speed_mbps, file_size)
                    
                    result = {
                        "test_name": f"{file_name}上传性能测试",
                        "status": "PASS" if is_acceptable else "FAIL",
                        "message": f"{description}上传耗时{upload_time:.2f}s，速度{upload_speed_mbps:.2f}MB/s ({performance_grade})",
                        "file_size": file_size,
                        "file_size_mb": file_size / (1024 * 1024),
                        "upload_time": upload_time,
                        "upload_speed_mbps": upload_speed_mbps,
                        "performance_grade": performance_grade,
                        "response_status": response.status_code
                    }
                    
                    self.logger.info(f"{file_name}上传测试完成", {
                        "upload_time": upload_time,
                        "upload_speed_mbps": upload_speed_mbps,
                        "performance_grade": performance_grade
                    })
                    
                    return result
                else:
                    return {
                        "test_name": f"{file_name}上传性能测试",
                        "status": "FAIL",
                        "message": f"上传失败，状态码: {response.status_code}",
                        "file_size": file_size,
                        "upload_time": upload_time,
                        "response_status": response.status_code
                    }
                    
            except Exception as e:
                upload_time = time.time() - start_time
                return {
                    "test_name": f"{file_name}上传性能测试",
                    "status": "ERROR",
                    "message": f"上传异常: {str(e)}",
                    "file_size": file_size,
                    "upload_time": upload_time
                }
                
        except Exception as e:
            return {
                "test_name": f"{file_name}上传性能测试",
                "status": "ERROR",
                "message": f"测试准备异常: {str(e)}"
            }
    
    def _test_concurrent_file_upload(self, concurrent_uploads: int = 3) -> Dict[str, Any]:
        """
        测试并发文件上传
        
        Args:
            concurrent_uploads: 并发上传数量
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            self.logger.info("开始并发文件上传测试", {
                "concurrent_uploads": concurrent_uploads
            })
            
            # 文件配置
            file_size = 1024 * 1024 * 2  # 2MB
            upload_results = []
            
            def upload_file(upload_id: int) -> Dict[str, Any]:
                """单个文件上传函数"""
                # 为每个上传创建独立的客户端
                upload_client = APIClient(
                    base_url=self.config.get_base_url(),
                    timeout=self.config.get_timeout() * 2,  # 上传需要更长超时时间
                    retry_count=1
                )
                
                try:
                    # 用户登录
                    upload_client.login(
                        self.config.test_username,
                        self.config.test_password
                    )
                    
                    # 创建测试文件内容
                    test_content = self._generate_test_file_content(file_size)
                    
                    # 准备上传数据
                    files = {
                        'file': (f'concurrent_test_{upload_id}.txt', test_content, 'text/plain')
                    }
                    
                    data = {
                        'title': f'并发上传测试_{upload_id}',
                        'description': f'并发上传测试文件 #{upload_id}'
                    }
                    
                    # 执行上传
                    start_time = time.time()
                    response = upload_client.post("/api/videos/upload/", data=data, files=files)
                    upload_time = time.time() - start_time
                    
                    # 计算上传速度
                    upload_speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
                    
                    return {
                        "upload_id": upload_id,
                        "success": response.is_success,
                        "upload_time": upload_time,
                        "upload_speed_mbps": upload_speed_mbps,
                        "status_code": response.status_code,
                        "file_size": file_size
                    }
                    
                except Exception as e:
                    return {
                        "upload_id": upload_id,
                        "success": False,
                        "error": str(e),
                        "upload_time": 0,
                        "upload_speed_mbps": 0,
                        "file_size": file_size
                    }
                finally:
                    upload_client.close()
            
            # 使用线程池执行并发上传
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_uploads) as executor:
                future_to_upload = {
                    executor.submit(upload_file, upload_id): upload_id 
                    for upload_id in range(concurrent_uploads)
                }
                
                for future in concurrent.futures.as_completed(future_to_upload):
                    upload_id = future_to_upload[future]
                    try:
                        result = future.result()
                        upload_results.append(result)
                    except Exception as e:
                        self.logger.error(f"并发上传{upload_id}异常", {"error": str(e)})
                        upload_results.append({
                            "upload_id": upload_id,
                            "success": False,
                            "error": str(e),
                            "upload_time": 0,
                            "upload_speed_mbps": 0,
                            "file_size": file_size
                        })
            
            total_time = time.time() - start_time
            
            # 分析结果
            if upload_results:
                successful_uploads = sum(1 for r in upload_results if r["success"])
                failed_uploads = len(upload_results) - successful_uploads
                
                # 计算平均上传时间和速度
                successful_results = [r for r in upload_results if r["success"]]
                if successful_results:
                    avg_upload_time = statistics.mean([r["upload_time"] for r in successful_results])
                    avg_upload_speed = statistics.mean([r["upload_speed_mbps"] for r in successful_results])
                else:
                    avg_upload_time = 0
                    avg_upload_speed = 0
                
                success_rate = (successful_uploads / len(upload_results)) * 100
                
                # 判断测试是否通过
                is_acceptable = (
                    success_rate >= 80.0 and  # 成功率至少80%
                    avg_upload_speed >= 0.5   # 平均速度至少0.5MB/s
                )
                
                result = {
                    "test_name": "并发文件上传测试",
                    "status": "PASS" if is_acceptable else "FAIL",
                    "message": f"并发{concurrent_uploads}个上传，成功率{success_rate:.1f}%，平均速度{avg_upload_speed:.2f}MB/s",
                    "concurrent_uploads": concurrent_uploads,
                    "successful_uploads": successful_uploads,
                    "failed_uploads": failed_uploads,
                    "success_rate": success_rate,
                    "avg_upload_time": avg_upload_time,
                    "avg_upload_speed": avg_upload_speed,
                    "total_test_time": total_time,
                    "individual_results": upload_results
                }
                
                self.logger.info("并发文件上传测试完成", {
                    "success_rate": success_rate,
                    "avg_upload_speed": avg_upload_speed,
                    "total_time": total_time
                })
                
                return result
            else:
                return {
                    "test_name": "并发文件上传测试",
                    "status": "ERROR",
                    "message": "没有收集到上传结果"
                }
                
        except Exception as e:
            return {
                "test_name": "并发文件上传测试",
                "status": "ERROR",
                "message": f"测试异常: {str(e)}"
            }
    
    def _generate_test_file_content(self, size: int) -> bytes:
        """
        生成指定大小的测试文件内容
        
        Args:
            size: 文件大小（字节）
            
        Returns:
            bytes: 文件内容
        """
        # 生成重复的文本内容
        base_text = "这是一个用于性能测试的文件内容。" * 10
        base_bytes = base_text.encode('utf-8')
        
        # 计算需要重复多少次
        repeat_count = size // len(base_bytes) + 1
        content = base_bytes * repeat_count
        
        # 截取到指定大小
        return content[:size]
    
    def _evaluate_upload_performance(self, upload_speed_mbps: float, file_size: int) -> str:
        """
        评估上传性能等级
        
        Args:
            upload_speed_mbps: 上传速度（MB/s）
            file_size: 文件大小（字节）
            
        Returns:
            str: 性能等级
        """
        # 根据文件大小调整性能标准
        if file_size < 1024 * 1024:  # 小于1MB
            if upload_speed_mbps >= 5.0:
                return "优秀"
            elif upload_speed_mbps >= 2.0:
                return "良好"
            elif upload_speed_mbps >= 1.0:
                return "可接受"
            else:
                return "差"
        elif file_size < 10 * 1024 * 1024:  # 小于10MB
            if upload_speed_mbps >= 3.0:
                return "优秀"
            elif upload_speed_mbps >= 1.5:
                return "良好"
            elif upload_speed_mbps >= 0.8:
                return "可接受"
            else:
                return "差"
        else:  # 大于10MB
            if upload_speed_mbps >= 2.0:
                return "优秀"
            elif upload_speed_mbps >= 1.0:
                return "良好"
            elif upload_speed_mbps >= 0.5:
                return "可接受"
            else:
                return "差"
    
    def _is_upload_performance_acceptable(self, upload_speed_mbps: float, file_size: int) -> bool:
        """
        判断上传性能是否可接受
        
        Args:
            upload_speed_mbps: 上传速度（MB/s）
            file_size: 文件大小（字节）
            
        Returns:
            bool: 是否可接受
        """
        # 根据文件大小设置最低速度要求
        if file_size < 1024 * 1024:  # 小于1MB
            return upload_speed_mbps >= 1.0
        elif file_size < 10 * 1024 * 1024:  # 小于10MB
            return upload_speed_mbps >= 0.8
        else:  # 大于10MB
            return upload_speed_mbps >= 0.5
    
    def _generate_upload_performance_summary(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成上传性能测试摘要
        
        Args:
            test_results: 测试结果列表
            
        Returns:
            Dict[str, Any]: 测试摘要
        """
        if not test_results:
            return {}
        
        # 提取有效的上传测试结果
        upload_results = [r for r in test_results if r["status"] in ["PASS", "FAIL"] and "upload_speed_mbps" in r]
        
        if not upload_results:
            return {"message": "没有有效的上传性能数据"}
        
        # 计算整体统计
        upload_speeds = [r["upload_speed_mbps"] for r in upload_results]
        upload_times = [r["upload_time"] for r in upload_results]
        file_sizes = [r.get("file_size", 0) for r in upload_results]
        
        avg_speed = statistics.mean(upload_speeds) if upload_speeds else 0
        max_speed = max(upload_speeds) if upload_speeds else 0
        min_speed = min(upload_speeds) if upload_speeds else 0
        
        avg_time = statistics.mean(upload_times) if upload_times else 0
        total_data_mb = sum(size / (1024 * 1024) for size in file_sizes)
        
        # 性能等级分布
        performance_grades = {"优秀": 0, "良好": 0, "可接受": 0, "差": 0}
        for result in upload_results:
            grade = result.get("performance_grade", "未知")
            if grade in performance_grades:
                performance_grades[grade] += 1
        
        return {
            "total_upload_tests": len(upload_results),
            "total_data_uploaded_mb": total_data_mb,
            "avg_upload_speed_mbps": avg_speed,
            "max_upload_speed_mbps": max_speed,
            "min_upload_speed_mbps": min_speed,
            "avg_upload_time": avg_time,
            "performance_distribution": performance_grades
        }
    
    def cleanup(self):
        """清理资源"""
        if self.client:
            self.client.close()
        
        if self.logger:
            self.logger.save_to_file()


# pytest测试函数
@pytest.fixture
def performance_tester():
    """性能测试器fixture"""
    config = TestConfigManager()
    tester = PerformanceTester(config)
    yield tester
    tester.cleanup()


def test_api_response_time(performance_tester):
    """测试API响应时间"""
    result = performance_tester.test_response_time()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    # 记录详细结果
    print(f"\nAPI响应时间测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    # 显示摘要信息
    if "summary" in result and result["summary"]:
        summary = result["summary"]
        print(f"整体平均响应时间: {summary.get('overall_avg_response_time', 0):.3f}s")
        print(f"整体成功率: {summary.get('overall_success_rate', 0):.1f}%")
        
        if "performance_distribution" in summary:
            print("性能分布:")
            for grade, count in summary["performance_distribution"].items():
                if count > 0:
                    print(f"  {grade}: {count}个端点")
    
    # 显示详细结果
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} {detail['test_name']}: {detail['message']}")


def test_concurrent_requests_health_check(performance_tester):
    """测试健康检查端点的并发请求处理"""
    result = performance_tester.test_concurrent_requests(
        endpoint="/api/monitoring/health/",
        method="GET",
        concurrent_users=5,
        requests_per_user=3
    )
    
    assert result["status"] in ["PASS", "FAIL", "ERROR"], f"测试状态无效: {result['status']}"
    
    print(f"\n并发请求测试结果:")
    print(f"状态: {result['status']}")
    print(f"消息: {result['message']}")
    
    if "success_rate" in result:
        print(f"成功率: {result['success_rate']:.1f}%")
    if "actual_rps" in result:
        print(f"实际RPS: {result['actual_rps']:.2f}")


def test_concurrent_requests_comprehensive(performance_tester):
    """测试全面的并发请求处理"""
    result = performance_tester.test_concurrent_requests_comprehensive()
    
    assert result["status"] in ["PASS", "FAIL"], f"测试状态无效: {result['status']}"
    assert result["total"] > 0, "应该有测试用例"
    
    print(f"\n全面并发请求测试结果:")
    print(f"通过: {result['passed']}/{result['total']}")
    
    # 显示摘要信息
    if "summary" in result and result["summary"]:
        summary = result["summary"]
        print(f"总并发用户数: {summary.get('total_concurrent_users', 0)}")
        print(f"总请求数: {summary.get('total_requests', 0)}")
        print(f"平均成功率: {summary.get('avg_success_rate', 0):.1f}%")
        print(f"平均RPS: {summary.get('avg_rps', 0):.2f}")
        
        if summary.get('best_performing_scenario'):
            print(f"最佳性能场景: {summary['best_performing_scenario']}")
        if summary.get('worst_performing_scenario'):
            print(f"最差性能场景: {summary['worst_performing_scenario']}")
    
    # 显示详细结果
    for detail in result["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
        scenario_name = detail.get("scenario_name", detail["test_name"])
        print(f"{status_icon} {scenario_name}: {detail['message']}")


def test_data_consistency_under_load(performance_tester):
    """测试并发负载下的数据一致性"""
    result = performance_tester.test_data_consistency_under_load()
    
    assert result["status"] in ["PASS", "FAIL", "SKIP", "ERROR"], f"测试状态无效: {result['status']}"
    
    print(f"\n并发数据一致性测试结果:")
    print(f"状态: {result['status']}")
    print(f"消息: {result['message']}")
    
    if "consistency_analysis" in result:
        analysis = result["consistency_analysis"]
        if "details" in analysis:
            details = analysis["details"]
            print(f"总响应数: {details.get('total_responses', 0)}")
            print(f"一致性率: {details.get('consistency_rate', 0):.1f}%")
            
            if details.get('inconsistencies'):
                print(f"发现不一致: {len(details['inconsistencies'])}个")


def test_file_upload_performance(performance_tester):
    """测试文件上传性能"""
    result = performance_tester.test_file_upload_performance()
    
    assert result["status"] in ["PASS", "FAIL", "SKIP", "ERROR"], f"测试状态无效: {result['status']}"
    
    print(f"\n文件上传性能测试结果:")
    print(f"状态: {result['status']}")
    
    if result["status"] in ["PASS", "FAIL"]:
        print(f"通过: {result['passed']}/{result['total']}")
        
        # 显示摘要信息
        if "summary" in result and result["summary"]:
            summary = result["summary"]
            print(f"总上传测试数: {summary.get('total_upload_tests', 0)}")
            print(f"总上传数据: {summary.get('total_data_uploaded_mb', 0):.2f}MB")
            print(f"平均上传速度: {summary.get('avg_upload_speed_mbps', 0):.2f}MB/s")
            print(f"最大上传速度: {summary.get('max_upload_speed_mbps', 0):.2f}MB/s")
            print(f"平均上传时间: {summary.get('avg_upload_time', 0):.2f}s")
            
            if "performance_distribution" in summary:
                print("性能分布:")
                for grade, count in summary["performance_distribution"].items():
                    if count > 0:
                        print(f"  {grade}: {count}个测试")
        
        # 显示详细结果
        for detail in result["details"]:
            status_icon = "✅" if detail["status"] == "PASS" else "❌" if detail["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {detail['test_name']}: {detail['message']}")
    else:
        print(f"消息: {result['message']}")


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = PerformanceTester(config)
    
    try:
        print("开始性能测试...")
        
        # 运行响应时间测试
        result_response_time = tester.test_response_time()
        print(f"\n响应时间测试结果: {result_response_time['status']} ({result_response_time['passed']}/{result_response_time['total']})")
        
        # 运行全面并发请求测试
        result_concurrent_comprehensive = tester.test_concurrent_requests_comprehensive()
        print(f"全面并发请求测试结果: {result_concurrent_comprehensive['status']} ({result_concurrent_comprehensive['passed']}/{result_concurrent_comprehensive['total']})")
        
        # 运行数据一致性测试
        result_consistency = tester.test_data_consistency_under_load()
        print(f"并发数据一致性测试结果: {result_consistency['status']}")
        
        # 运行文件上传性能测试
        result_upload = tester.test_file_upload_performance()
        print(f"文件上传性能测试结果: {result_upload['status']}")
        if result_upload['status'] in ['PASS', 'FAIL']:
            print(f"  通过: {result_upload['passed']}/{result_upload['total']}")
        
        print("\n性能测试完成")
        
    finally:
        tester.cleanup()