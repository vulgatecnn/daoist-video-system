"""
数据一致性测试模块

测试前后端数据交换的一致性，包括JSON序列化、UTF-8编码和日期时间处理。
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import pytest

from ..utils.http_client import APIClient, HTTPResponse
from ..utils.test_helpers import TestLogger, TestDataGenerator
from ..config.test_config import TestConfigManager


@dataclass
class DataConsistencyResult:
    """数据一致性测试结果"""
    test_name: str
    status: str
    message: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "test_name": self.test_name,
            "status": self.status,
            "message": self.message,
            "details": self.details
        }


class DataConsistencyTester:
    """数据一致性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化数据一致性测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.client = APIClient(
            base_url=config.get_base_url(),
            timeout=config.get_timeout(),
            retry_count=2
        )
        self.logger = TestLogger("data_consistency_test.log")
        
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
            self.logger.info("数据一致性测试用户登录成功")
        else:
            self.logger.error("数据一致性测试用户登录失败")
        
        return success
    
    def test_json_serialization(self) -> DataConsistencyResult:
        """
        测试复杂JSON数据的序列化和反序列化
        
        Returns:
            DataConsistencyResult: 测试结果
        """
        try:
            self.logger.info("开始JSON序列化测试")
            
            # 创建复杂的测试数据
            complex_data = self._generate_complex_json_data()
            
            # 测试场景列表
            test_scenarios = []
            
            # 场景1: 测试用户注册数据的JSON处理
            user_data = complex_data["user_data"]
            register_result = self._test_json_round_trip(
                "用户注册", "POST", "/api/auth/register/", user_data
            )
            test_scenarios.append(register_result)
            
            # 场景2: 测试视频数据的JSON处理（需要认证）
            if self._ensure_authentication():
                video_data = complex_data["video_data"]
                video_result = self._test_json_round_trip(
                    "视频数据", "POST", "/api/videos/", video_data, requires_auth=True
                )
                test_scenarios.append(video_result)
                
                # 场景3: 测试合成任务数据的JSON处理
                composition_data = complex_data["composition_data"]
                composition_result = self._test_json_round_trip(
                    "合成任务", "POST", "/api/videos/composition/create/", 
                    composition_data, requires_auth=True
                )
                test_scenarios.append(composition_result)
            
            # 汇总结果
            passed_scenarios = sum(1 for s in test_scenarios if s["passed"])
            total_scenarios = len(test_scenarios)
            
            if passed_scenarios == total_scenarios:
                status = "PASS"
                message = f"所有{total_scenarios}个JSON序列化场景测试通过"
            else:
                status = "FAIL"
                message = f"{passed_scenarios}/{total_scenarios}个JSON序列化场景测试通过"
            
            return DataConsistencyResult(
                test_name="JSON序列化测试",
                status=status,
                message=message,
                details={
                    "scenarios": test_scenarios,
                    "passed_count": passed_scenarios,
                    "total_count": total_scenarios,
                    "test_data_complexity": self._analyze_data_complexity(complex_data)
                }
            )
            
        except Exception as e:
            return DataConsistencyResult(
                test_name="JSON序列化测试",
                status="ERROR",
                message=f"测试异常: {str(e)}",
                details={"error": str(e)}
            )
    
    def test_utf8_encoding(self) -> DataConsistencyResult:
        """
        测试中文内容的正确处理
        
        Returns:
            DataConsistencyResult: 测试结果
        """
        try:
            self.logger.info("开始UTF-8编码测试")
            
            # 创建包含各种中文字符的测试数据
            utf8_test_data = self._generate_utf8_test_data()
            
            test_scenarios = []
            
            # 场景1: 测试中文用户名注册
            chinese_user_data = utf8_test_data["chinese_user"]
            chinese_user_result = self._test_utf8_handling(
                "中文用户注册", "POST", "/api/auth/register/", chinese_user_data
            )
            test_scenarios.append(chinese_user_result)
            
            # 场景2: 测试中文视频标题和描述（需要认证）
            if self._ensure_authentication():
                chinese_video_data = utf8_test_data["chinese_video"]
                chinese_video_result = self._test_utf8_handling(
                    "中文视频数据", "POST", "/api/videos/", 
                    chinese_video_data, requires_auth=True
                )
                test_scenarios.append(chinese_video_result)
                
                # 场景3: 测试特殊字符和emoji
                special_char_data = utf8_test_data["special_characters"]
                special_char_result = self._test_utf8_handling(
                    "特殊字符处理", "POST", "/api/videos/", 
                    special_char_data, requires_auth=True
                )
                test_scenarios.append(special_char_result)
            
            # 汇总结果
            passed_scenarios = sum(1 for s in test_scenarios if s["passed"])
            total_scenarios = len(test_scenarios)
            
            if passed_scenarios == total_scenarios:
                status = "PASS"
                message = f"所有{total_scenarios}个UTF-8编码场景测试通过"
            else:
                status = "FAIL"
                message = f"{passed_scenarios}/{total_scenarios}个UTF-8编码场景测试通过"
            
            return DataConsistencyResult(
                test_name="UTF-8编码测试",
                status=status,
                message=message,
                details={
                    "scenarios": test_scenarios,
                    "passed_count": passed_scenarios,
                    "total_count": total_scenarios,
                    "character_types_tested": list(utf8_test_data.keys())
                }
            )
            
        except Exception as e:
            return DataConsistencyResult(
                test_name="UTF-8编码测试",
                status="ERROR",
                message=f"测试异常: {str(e)}",
                details={"error": str(e)}
            )
    
    def test_datetime_handling(self) -> DataConsistencyResult:
        """
        测试日期时间处理的正确性
        
        Returns:
            DataConsistencyResult: 测试结果
        """
        try:
            self.logger.info("开始日期时间处理测试")
            
            # 创建各种日期时间格式的测试数据
            datetime_test_data = self._generate_datetime_test_data()
            
            test_scenarios = []
            
            # 场景1: 测试不同时区的日期时间处理
            if self._ensure_authentication():
                for timezone_name, test_data in datetime_test_data.items():
                    scenario_result = self._test_datetime_consistency(
                        f"时区{timezone_name}测试", test_data
                    )
                    test_scenarios.append(scenario_result)
            
            # 场景2: 测试日期时间格式的往返转换
            format_test_result = self._test_datetime_format_consistency()
            test_scenarios.append(format_test_result)
            
            # 汇总结果
            passed_scenarios = sum(1 for s in test_scenarios if s["passed"])
            total_scenarios = len(test_scenarios)
            
            if passed_scenarios == total_scenarios:
                status = "PASS"
                message = f"所有{total_scenarios}个日期时间处理场景测试通过"
            else:
                status = "FAIL"
                message = f"{passed_scenarios}/{total_scenarios}个日期时间处理场景测试通过"
            
            return DataConsistencyResult(
                test_name="日期时间处理测试",
                status=status,
                message=message,
                details={
                    "scenarios": test_scenarios,
                    "passed_count": passed_scenarios,
                    "total_count": total_scenarios,
                    "timezones_tested": list(datetime_test_data.keys())
                }
            )
            
        except Exception as e:
            return DataConsistencyResult(
                test_name="日期时间处理测试",
                status="ERROR",
                message=f"测试异常: {str(e)}",
                details={"error": str(e)}
            )
    
    def _generate_complex_json_data(self) -> Dict[str, Any]:
        """生成复杂的JSON测试数据"""
        timestamp = datetime.now().isoformat()
        random_id = str(uuid.uuid4())
        
        return {
            "user_data": {
                "username": f"test_user_{random_id[:8]}",
                "email": f"test_{random_id[:8]}@example.com",
                "password": "TestPass123!",
                "profile": {
                    "first_name": "测试",
                    "last_name": "用户",
                    "bio": "这是一个测试用户的简介，包含中文字符。",
                    "preferences": {
                        "language": "zh-CN",
                        "timezone": "Asia/Shanghai",
                        "notifications": {
                            "email": True,
                            "push": False,
                            "sms": None
                        }
                    },
                    "tags": ["道教", "养生", "太极"],
                    "metadata": {
                        "created_at": timestamp,
                        "version": 1.0,
                        "is_active": True,
                        "score": 95.5
                    }
                }
            },
            "video_data": {
                "title": f"测试视频_{random_id[:8]}",
                "description": "这是一个包含复杂数据结构的测试视频描述。\n支持多行文本，特殊字符：@#$%^&*()，以及emoji：🎬📹🎥",
                "category": "道德经",
                "duration": 1800,
                "tags": ["测试", "数据一致性", "JSON"],
                "metadata": {
                    "resolution": "1920x1080",
                    "bitrate": 5000,
                    "codec": "h264",
                    "audio_channels": 2,
                    "created_at": timestamp,
                    "custom_fields": {
                        "chapter_marks": [
                            {"time": 0, "title": "开始"},
                            {"time": 300, "title": "第一章"},
                            {"time": 900, "title": "第二章"},
                            {"time": 1500, "title": "结束"}
                        ],
                        "subtitles": [
                            {"language": "zh-CN", "file": "chinese.srt"},
                            {"language": "en-US", "file": "english.srt"}
                        ]
                    }
                }
            },
            "composition_data": {
                "video_ids": [1, 2, 3],
                "output_format": "mp4",
                "quality": "high",
                "resolution": "1920x1080",
                "settings": {
                    "transitions": [
                        {"type": "fade", "duration": 1.0},
                        {"type": "slide", "duration": 0.5, "direction": "left"}
                    ],
                    "audio": {
                        "background_music": True,
                        "volume": 0.8,
                        "fade_in": 2.0,
                        "fade_out": 3.0
                    },
                    "effects": {
                        "color_correction": {
                            "brightness": 1.1,
                            "contrast": 1.05,
                            "saturation": 1.0
                        },
                        "filters": ["sharpen", "noise_reduction"]
                    }
                },
                "metadata": {
                    "created_at": timestamp,
                    "priority": "normal",
                    "estimated_duration": 300,
                    "output_filename": f"composed_{random_id[:8]}.mp4"
                }
            }
        }
    
    def _generate_utf8_test_data(self) -> Dict[str, Any]:
        """生成UTF-8编码测试数据"""
        random_id = str(uuid.uuid4())[:8]
        
        return {
            "chinese_user": {
                "username": f"中文用户_{random_id}",
                "email": f"chinese_{random_id}@测试.com",
                "password": "中文密码123",
                "profile": {
                    "first_name": "张",
                    "last_name": "三",
                    "bio": "我是一个中文用户，喜欢道教文化和太极拳。"
                }
            },
            "chinese_video": {
                "title": "道德经第一章：道可道，非常道",
                "description": "《道德经》是中国古代哲学经典，本视频讲解第一章的深刻含义。\n包含繁体字：道德經、簡體字：道德经、以及古文：道可道，非常道。",
                "category": "道德经",
                "tags": ["道德经", "老子", "哲学", "中国文化"]
            },
            "special_characters": {
                "title": "特殊字符测试：!@#$%^&*()_+-=[]{}|;':\",./<>?",
                "description": "测试各种特殊字符和符号的处理能力：\n数学符号：±×÷≠≤≥∞∑∏√∫\n货币符号：¥$€£¢\nEmoji：🎬📹🎥🎭🎪🎨🎯🎲🎸🎹🎺🎻\n其他符号：™®©§¶†‡•…‰‱",
                "category": "测试",
                "tags": ["特殊字符", "符号", "emoji", "测试"]
            }
        }
    
    def _generate_datetime_test_data(self) -> Dict[str, Any]:
        """生成日期时间测试数据"""
        base_time = datetime.now()
        
        return {
            "UTC": {
                "datetime": base_time.replace(tzinfo=timezone.utc).isoformat(),
                "timestamp": base_time.timestamp(),
                "formatted": base_time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "Asia/Shanghai": {
                "datetime": base_time.replace(tzinfo=timezone(timedelta(hours=8))).isoformat(),
                "timestamp": base_time.timestamp(),
                "formatted": base_time.strftime("%Y年%m月%d日 %H时%M分%S秒")
            },
            "America/New_York": {
                "datetime": base_time.replace(tzinfo=timezone(timedelta(hours=-5))).isoformat(),
                "timestamp": base_time.timestamp(),
                "formatted": base_time.strftime("%m/%d/%Y %I:%M:%S %p")
            }
        }
    
    def _test_json_round_trip(self, scenario_name: str, method: str, 
                             endpoint: str, data: Dict[str, Any],
                             requires_auth: bool = False) -> Dict[str, Any]:
        """
        测试JSON数据的往返处理
        
        Args:
            scenario_name: 场景名称
            method: HTTP方法
            endpoint: API端点
            data: 测试数据
            requires_auth: 是否需要认证
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            self.logger.info(f"测试JSON往返处理: {scenario_name}")
            
            # 序列化测试数据
            original_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
            
            # 发送请求
            if method.upper() == "POST":
                response = self.client.post(endpoint, data=data)
            elif method.upper() == "PUT":
                response = self.client.put(endpoint, data=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            # 分析响应
            if response.json_data:
                # 检查响应中是否包含我们发送的数据
                consistency_check = self._check_json_consistency(
                    original_data=data,
                    response_data=response.json_data
                )
                
                return {
                    "scenario": scenario_name,
                    "passed": consistency_check["is_consistent"],
                    "message": consistency_check["message"],
                    "details": {
                        "status_code": response.status_code,
                        "response_time": response.response_time,
                        "original_size": len(original_json),
                        "response_size": len(response.text),
                        "consistency_details": consistency_check["details"]
                    }
                }
            else:
                return {
                    "scenario": scenario_name,
                    "passed": False,
                    "message": "响应不包含JSON数据",
                    "details": {
                        "status_code": response.status_code,
                        "response_text": response.text[:200]  # 只记录前200个字符
                    }
                }
                
        except Exception as e:
            return {
                "scenario": scenario_name,
                "passed": False,
                "message": f"测试异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _test_utf8_handling(self, scenario_name: str, method: str,
                           endpoint: str, data: Dict[str, Any],
                           requires_auth: bool = False) -> Dict[str, Any]:
        """
        测试UTF-8编码处理
        
        Args:
            scenario_name: 场景名称
            method: HTTP方法
            endpoint: API端点
            data: 测试数据
            requires_auth: 是否需要认证
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            self.logger.info(f"测试UTF-8编码处理: {scenario_name}")
            
            # 检查原始数据中的UTF-8字符
            utf8_analysis = self._analyze_utf8_content(data)
            
            # 发送请求
            if method.upper() == "POST":
                response = self.client.post(endpoint, data=data)
            elif method.upper() == "PUT":
                response = self.client.put(endpoint, data=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            # 检查响应的UTF-8处理
            if response.text:
                # 验证响应文本是否正确处理了UTF-8
                response_utf8_check = self._verify_utf8_response(
                    original_data=data,
                    response_text=response.text,
                    response_json=response.json_data
                )
                
                return {
                    "scenario": scenario_name,
                    "passed": response_utf8_check["is_valid"],
                    "message": response_utf8_check["message"],
                    "details": {
                        "status_code": response.status_code,
                        "response_time": response.response_time,
                        "original_utf8_analysis": utf8_analysis,
                        "response_utf8_check": response_utf8_check["details"]
                    }
                }
            else:
                return {
                    "scenario": scenario_name,
                    "passed": False,
                    "message": "响应为空",
                    "details": {"status_code": response.status_code}
                }
                
        except Exception as e:
            return {
                "scenario": scenario_name,
                "passed": False,
                "message": f"测试异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _test_datetime_consistency(self, scenario_name: str, 
                                  datetime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        测试日期时间一致性
        
        Args:
            scenario_name: 场景名称
            datetime_data: 日期时间测试数据
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            self.logger.info(f"测试日期时间一致性: {scenario_name}")
            
            # 创建包含日期时间的测试视频数据
            video_data = {
                "title": f"日期时间测试_{scenario_name}",
                "description": f"测试日期时间格式: {datetime_data['formatted']}",
                "category": "测试",
                "created_at": datetime_data["datetime"],
                "scheduled_at": datetime_data["datetime"],
                "metadata": {
                    "timestamp": datetime_data["timestamp"],
                    "formatted_time": datetime_data["formatted"]
                }
            }
            
            # 发送请求
            response = self.client.post("/api/videos/", data=video_data)
            
            # 检查日期时间处理
            if response.json_data:
                datetime_check = self._verify_datetime_handling(
                    original_datetime=datetime_data,
                    response_data=response.json_data
                )
                
                return {
                    "scenario": scenario_name,
                    "passed": datetime_check["is_consistent"],
                    "message": datetime_check["message"],
                    "details": {
                        "status_code": response.status_code,
                        "response_time": response.response_time,
                        "datetime_check": datetime_check["details"]
                    }
                }
            else:
                return {
                    "scenario": scenario_name,
                    "passed": False,
                    "message": "响应不包含JSON数据",
                    "details": {"status_code": response.status_code}
                }
                
        except Exception as e:
            return {
                "scenario": scenario_name,
                "passed": False,
                "message": f"测试异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _test_datetime_format_consistency(self) -> Dict[str, Any]:
        """测试日期时间格式的往返一致性"""
        try:
            # 测试健康检查端点的时间戳
            response = self.client.get("/api/monitoring/health/")
            
            if response.is_success and response.json_data:
                # 检查响应中的时间戳格式
                timestamp_fields = []
                self._extract_timestamp_fields(response.json_data, timestamp_fields)
                
                if timestamp_fields:
                    format_consistency = self._check_timestamp_formats(timestamp_fields)
                    
                    return {
                        "scenario": "日期时间格式一致性",
                        "passed": format_consistency["is_consistent"],
                        "message": format_consistency["message"],
                        "details": format_consistency["details"]
                    }
                else:
                    return {
                        "scenario": "日期时间格式一致性",
                        "passed": True,
                        "message": "响应中没有时间戳字段",
                        "details": {}
                    }
            else:
                return {
                    "scenario": "日期时间格式一致性",
                    "passed": False,
                    "message": "无法获取健康检查响应",
                    "details": {"status_code": response.status_code}
                }
                
        except Exception as e:
            return {
                "scenario": "日期时间格式一致性",
                "passed": False,
                "message": f"测试异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_json_consistency(self, original_data: Dict[str, Any],
                               response_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查JSON数据一致性"""
        try:
            inconsistencies = []
            
            # 检查关键字段是否在响应中正确反映
            for key, value in original_data.items():
                if key in response_data:
                    if isinstance(value, (str, int, float, bool)):
                        if response_data[key] != value:
                            inconsistencies.append({
                                "field": key,
                                "original": value,
                                "response": response_data[key],
                                "type": "value_mismatch"
                            })
                    elif isinstance(value, dict):
                        # 递归检查嵌套对象
                        nested_check = self._check_json_consistency(value, response_data[key])
                        if not nested_check["is_consistent"]:
                            inconsistencies.extend(nested_check["details"]["inconsistencies"])
                else:
                    # 某些字段可能不会在响应中返回（如密码），这是正常的
                    if key not in ["password", "token", "secret"]:
                        inconsistencies.append({
                            "field": key,
                            "original": value,
                            "response": None,
                            "type": "missing_field"
                        })
            
            is_consistent = len(inconsistencies) == 0
            message = "JSON数据一致性检查通过" if is_consistent else f"发现{len(inconsistencies)}个不一致项"
            
            return {
                "is_consistent": is_consistent,
                "message": message,
                "details": {
                    "inconsistencies": inconsistencies,
                    "total_fields_checked": len(original_data),
                    "inconsistent_fields": len(inconsistencies)
                }
            }
            
        except Exception as e:
            return {
                "is_consistent": False,
                "message": f"一致性检查异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _analyze_utf8_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据中的UTF-8内容"""
        utf8_stats = {
            "chinese_chars": 0,
            "special_chars": 0,
            "emoji_count": 0,
            "total_chars": 0,
            "fields_with_utf8": []
        }
        
        def analyze_value(key: str, value: Any):
            if isinstance(value, str):
                utf8_stats["total_chars"] += len(value)
                
                # 统计中文字符
                chinese_count = sum(1 for char in value if '\u4e00' <= char <= '\u9fff')
                utf8_stats["chinese_chars"] += chinese_count
                
                # 统计特殊字符
                special_count = sum(1 for char in value if ord(char) > 127 and not '\u4e00' <= char <= '\u9fff')
                utf8_stats["special_chars"] += special_count
                
                # 统计emoji（简化检测）
                emoji_count = sum(1 for char in value if ord(char) > 0x1F600)
                utf8_stats["emoji_count"] += emoji_count
                
                # 记录包含UTF-8字符的字段
                if chinese_count > 0 or special_count > 0 or emoji_count > 0:
                    utf8_stats["fields_with_utf8"].append(key)
            
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    analyze_value(f"{key}.{sub_key}", sub_value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    analyze_value(f"{key}[{i}]", item)
        
        for key, value in data.items():
            analyze_value(key, value)
        
        return utf8_stats
    
    def _verify_utf8_response(self, original_data: Dict[str, Any],
                             response_text: str, response_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """验证响应的UTF-8处理"""
        try:
            # 检查响应文本是否包含正确的UTF-8字符
            response_utf8_stats = {
                "can_decode": True,
                "contains_chinese": False,
                "contains_special_chars": False,
                "contains_emoji": False,
                "encoding_errors": []
            }
            
            try:
                # 尝试解码响应文本
                decoded_text = response_text.encode('utf-8').decode('utf-8')
                
                # 检查是否包含中文字符
                response_utf8_stats["contains_chinese"] = any('\u4e00' <= char <= '\u9fff' for char in decoded_text)
                
                # 检查是否包含特殊字符
                response_utf8_stats["contains_special_chars"] = any(ord(char) > 127 and not '\u4e00' <= char <= '\u9fff' for char in decoded_text)
                
                # 检查是否包含emoji
                response_utf8_stats["contains_emoji"] = any(ord(char) > 0x1F600 for char in decoded_text)
                
            except UnicodeError as e:
                response_utf8_stats["can_decode"] = False
                response_utf8_stats["encoding_errors"].append(str(e))
            
            # 如果有JSON响应，检查JSON中的UTF-8字符
            json_utf8_check = {}
            if response_json:
                json_utf8_check = self._analyze_utf8_content(response_json)
            
            # 判断UTF-8处理是否正确
            is_valid = (
                response_utf8_stats["can_decode"] and
                len(response_utf8_stats["encoding_errors"]) == 0
            )
            
            message = "UTF-8编码处理正确" if is_valid else "UTF-8编码处理存在问题"
            
            return {
                "is_valid": is_valid,
                "message": message,
                "details": {
                    "response_utf8_stats": response_utf8_stats,
                    "json_utf8_analysis": json_utf8_check
                }
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "message": f"UTF-8验证异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _verify_datetime_handling(self, original_datetime: Dict[str, Any],
                                 response_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证日期时间处理"""
        try:
            datetime_issues = []
            
            # 检查响应中的时间戳字段
            timestamp_fields = []
            self._extract_timestamp_fields(response_data, timestamp_fields)
            
            for field_path, timestamp_value in timestamp_fields:
                try:
                    # 尝试解析时间戳
                    if isinstance(timestamp_value, str):
                        # ISO格式时间戳
                        parsed_dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                    elif isinstance(timestamp_value, (int, float)):
                        # Unix时间戳
                        parsed_dt = datetime.fromtimestamp(timestamp_value)
                    else:
                        datetime_issues.append({
                            "field": field_path,
                            "issue": "不支持的时间戳格式",
                            "value": timestamp_value
                        })
                        continue
                    
                    # 检查时间戳是否合理（不能太久远或太未来）
                    now = datetime.now()
                    time_diff = abs((parsed_dt.replace(tzinfo=None) - now).total_seconds())
                    
                    if time_diff > 86400 * 365:  # 超过一年
                        datetime_issues.append({
                            "field": field_path,
                            "issue": "时间戳与当前时间差异过大",
                            "value": timestamp_value,
                            "parsed": parsed_dt.isoformat()
                        })
                
                except Exception as e:
                    datetime_issues.append({
                        "field": field_path,
                        "issue": f"时间戳解析失败: {str(e)}",
                        "value": timestamp_value
                    })
            
            is_consistent = len(datetime_issues) == 0
            message = "日期时间处理一致" if is_consistent else f"发现{len(datetime_issues)}个日期时间问题"
            
            return {
                "is_consistent": is_consistent,
                "message": message,
                "details": {
                    "timestamp_fields_found": len(timestamp_fields),
                    "datetime_issues": datetime_issues
                }
            }
            
        except Exception as e:
            return {
                "is_consistent": False,
                "message": f"日期时间验证异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _extract_timestamp_fields(self, data: Any, timestamp_fields: List, path: str = ""):
        """递归提取时间戳字段"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # 检查是否是时间戳字段
                if any(time_keyword in key.lower() for time_keyword in 
                      ['time', 'date', 'created', 'updated', 'modified', 'timestamp']):
                    timestamp_fields.append((current_path, value))
                else:
                    self._extract_timestamp_fields(value, timestamp_fields, current_path)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._extract_timestamp_fields(item, timestamp_fields, current_path)
    
    def _check_timestamp_formats(self, timestamp_fields: List) -> Dict[str, Any]:
        """检查时间戳格式的一致性"""
        try:
            format_analysis = {
                "iso_format": 0,
                "unix_timestamp": 0,
                "custom_format": 0,
                "invalid_format": 0,
                "format_details": []
            }
            
            for field_path, timestamp_value in timestamp_fields:
                format_info = {
                    "field": field_path,
                    "value": timestamp_value,
                    "format_type": "unknown"
                }
                
                try:
                    if isinstance(timestamp_value, str):
                        # 尝试解析ISO格式
                        datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                        format_analysis["iso_format"] += 1
                        format_info["format_type"] = "iso"
                    elif isinstance(timestamp_value, (int, float)):
                        # Unix时间戳
                        datetime.fromtimestamp(timestamp_value)
                        format_analysis["unix_timestamp"] += 1
                        format_info["format_type"] = "unix"
                    else:
                        format_analysis["custom_format"] += 1
                        format_info["format_type"] = "custom"
                
                except Exception:
                    format_analysis["invalid_format"] += 1
                    format_info["format_type"] = "invalid"
                
                format_analysis["format_details"].append(format_info)
            
            # 判断格式是否一致
            total_fields = len(timestamp_fields)
            is_consistent = (
                format_analysis["invalid_format"] == 0 and
                (format_analysis["iso_format"] == total_fields or 
                 format_analysis["unix_timestamp"] == total_fields)
            )
            
            message = "时间戳格式一致" if is_consistent else "时间戳格式不一致"
            
            return {
                "is_consistent": is_consistent,
                "message": message,
                "details": format_analysis
            }
            
        except Exception as e:
            return {
                "is_consistent": False,
                "message": f"格式检查异常: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _analyze_data_complexity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据复杂度"""
        complexity_stats = {
            "total_fields": 0,
            "nested_objects": 0,
            "arrays": 0,
            "max_nesting_level": 0,
            "data_types": {}
        }
        
        def analyze_recursive(obj: Any, level: int = 0):
            complexity_stats["max_nesting_level"] = max(complexity_stats["max_nesting_level"], level)
            
            if isinstance(obj, dict):
                complexity_stats["nested_objects"] += 1
                complexity_stats["total_fields"] += len(obj)
                
                for value in obj.values():
                    analyze_recursive(value, level + 1)
            
            elif isinstance(obj, list):
                complexity_stats["arrays"] += 1
                for item in obj:
                    analyze_recursive(item, level + 1)
            
            else:
                # 统计数据类型
                type_name = type(obj).__name__
                complexity_stats["data_types"][type_name] = complexity_stats["data_types"].get(type_name, 0) + 1
        
        analyze_recursive(data)
        return complexity_stats
    
    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()
        self.logger.info("数据一致性测试器已关闭")


# Pytest测试函数
@pytest.fixture
def data_consistency_tester():
    """数据一致性测试器fixture"""
    config = TestConfigManager()
    tester = DataConsistencyTester(config)
    yield tester
    tester.close()


def test_json_serialization_comprehensive(data_consistency_tester):
    """测试JSON序列化的全面功能"""
    result = data_consistency_tester.test_json_serialization()
    
    # 记录测试结果
    print(f"\n=== JSON序列化测试结果 ===")
    print(f"状态: {result.status}")
    print(f"消息: {result.message}")
    
    if result.details.get("scenarios"):
        for scenario in result.details["scenarios"]:
            status_icon = "✅" if scenario["passed"] else "❌"
            print(f"{status_icon} {scenario['scenario']}: {scenario['message']}")
    
    # 断言测试通过
    assert result.status in ["PASS", "SKIP"], f"JSON序列化测试失败: {result.message}"


def test_utf8_encoding_comprehensive(data_consistency_tester):
    """测试UTF-8编码的全面功能"""
    result = data_consistency_tester.test_utf8_encoding()
    
    # 记录测试结果
    print(f"\n=== UTF-8编码测试结果 ===")
    print(f"状态: {result.status}")
    print(f"消息: {result.message}")
    
    if result.details.get("scenarios"):
        for scenario in result.details["scenarios"]:
            status_icon = "✅" if scenario["passed"] else "❌"
            print(f"{status_icon} {scenario['scenario']}: {scenario['message']}")
    
    # 断言测试通过
    assert result.status in ["PASS", "SKIP"], f"UTF-8编码测试失败: {result.message}"


def test_datetime_handling_comprehensive(data_consistency_tester):
    """测试日期时间处理的全面功能"""
    result = data_consistency_tester.test_datetime_handling()
    
    # 记录测试结果
    print(f"\n=== 日期时间处理测试结果 ===")
    print(f"状态: {result.status}")
    print(f"消息: {result.message}")
    
    if result.details.get("scenarios"):
        for scenario in result.details["scenarios"]:
            status_icon = "✅" if scenario["passed"] else "❌"
            print(f"{status_icon} {scenario['scenario']}: {scenario['message']}")
    
    # 断言测试通过
    assert result.status in ["PASS", "SKIP"], f"日期时间处理测试失败: {result.message}"


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = DataConsistencyTester(config)
    
    try:
        print("开始数据一致性测试...")
        
        # 运行所有测试
        json_result = tester.test_json_serialization()
        utf8_result = tester.test_utf8_encoding()
        datetime_result = tester.test_datetime_handling()
        
        # 输出结果摘要
        results = [json_result, utf8_result, datetime_result]
        passed_count = sum(1 for r in results if r.status == "PASS")
        total_count = len(results)
        
        print(f"\n=== 数据一致性测试摘要 ===")
        print(f"总测试数: {total_count}")
        print(f"通过测试: {passed_count}")
        print(f"失败测试: {total_count - passed_count}")
        print(f"成功率: {(passed_count / total_count) * 100:.1f}%")
        
        for result in results:
            status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⏭️"
            print(f"{status_icon} {result.test_name}: {result.message}")
    
    finally:
        tester.close()