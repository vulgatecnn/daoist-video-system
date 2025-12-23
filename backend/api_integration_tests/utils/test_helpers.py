"""
测试辅助工具模块

提供测试过程中需要的各种辅助函数和工具类。
"""

import json
import time
import random
import string
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path


class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_random_string(length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_random_email() -> str:
        """生成随机邮箱地址"""
        username = TestDataGenerator.generate_random_string(8)
        domain = random.choice(['test.com', 'example.org', 'demo.net'])
        return f"{username}@{domain}"
    
    @staticmethod
    def generate_user_data() -> Dict[str, str]:
        """生成用户测试数据"""
        username = TestDataGenerator.generate_random_string(8)
        return {
            "username": username,
            "email": TestDataGenerator.generate_random_email(),
            "password": f"Pass{TestDataGenerator.generate_random_string(6)}123"
        }
    
    @staticmethod
    def generate_video_data() -> Dict[str, Any]:
        """生成视频测试数据"""
        categories = ['道德经', '庄子', '太极', '养生', '禅修']
        return {
            "title": f"测试视频_{TestDataGenerator.generate_random_string(5)}",
            "description": f"这是一个测试视频描述_{TestDataGenerator.generate_random_string(10)}",
            "category": random.choice(categories),
            "duration": random.randint(60, 3600),  # 1分钟到1小时
            "tags": [f"标签{i}" for i in range(random.randint(1, 5))]
        }
    
    @staticmethod
    def generate_composition_data() -> Dict[str, Any]:
        """生成合成任务测试数据"""
        return {
            "video_ids": [random.randint(1, 10) for _ in range(random.randint(2, 5))],
            "output_format": random.choice(['mp4', 'avi', 'mov']),
            "quality": random.choice(['low', 'medium', 'high']),
            "resolution": random.choice(['720p', '1080p', '4k'])
        }


class TestFileManager:
    """测试文件管理器"""
    
    def __init__(self, test_dir: str = "test_files"):
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(exist_ok=True)
    
    def create_test_video_file(self, filename: str = None) -> Path:
        """创建测试视频文件"""
        if filename is None:
            filename = f"test_video_{TestDataGenerator.generate_random_string(5)}.mp4"
        
        file_path = self.test_dir / filename
        
        # 创建一个模拟的视频文件（实际上是文本文件）
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Mock video file created at {datetime.now()}\n")
            f.write(f"Filename: {filename}\n")
            f.write("This is a mock video file for testing purposes.\n")
        
        return file_path
    
    def cleanup_test_files(self):
        """清理测试文件"""
        if self.test_dir.exists():
            for file in self.test_dir.iterdir():
                if file.is_file():
                    file.unlink()


class ResponseValidator:
    """响应验证器"""
    
    @staticmethod
    def validate_json_structure(response_data: Dict[str, Any], 
                              expected_schema: Dict[str, str]) -> bool:
        """验证JSON响应结构"""
        for field, expected_type in expected_schema.items():
            if field not in response_data:
                return False
            
            actual_value = response_data[field]
            
            if expected_type == "string" and not isinstance(actual_value, str):
                return False
            elif expected_type == "integer" and not isinstance(actual_value, int):
                return False
            elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                return False
            elif expected_type == "array" and not isinstance(actual_value, list):
                return False
            elif expected_type == "object" and not isinstance(actual_value, dict):
                return False
            elif expected_type == "boolean" and not isinstance(actual_value, bool):
                return False
        
        return True
    
    @staticmethod
    def validate_status_code(actual_code: int, expected_code: int) -> bool:
        """验证HTTP状态码"""
        return actual_code == expected_code
    
    @staticmethod
    def validate_response_time(response_time: float, max_time: float = 5.0) -> bool:
        """验证响应时间"""
        return response_time <= max_time


class TestLogger:
    """测试日志记录器"""
    
    def __init__(self, log_file: str = "test_log.txt"):
        self.log_file = Path(log_file)
        self.log_entries = []
    
    def log(self, level: str, message: str, details: Dict[str, Any] = None):
        """记录日志"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "details": details or {}
        }
        
        self.log_entries.append(log_entry)
        
        # 同时输出到控制台
        print(f"[{timestamp}] {level}: {message}")
        if details:
            print(f"  Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
    
    def info(self, message: str, details: Dict[str, Any] = None):
        """记录信息日志"""
        self.log("INFO", message, details)
    
    def warning(self, message: str, details: Dict[str, Any] = None):
        """记录警告日志"""
        self.log("WARNING", message, details)
    
    def error(self, message: str, details: Dict[str, Any] = None):
        """记录错误日志"""
        self.log("ERROR", message, details)
    
    def save_to_file(self):
        """保存日志到文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            for entry in self.log_entries:
                f.write(f"{json.dumps(entry, ensure_ascii=False)}\n")


class RetryHelper:
    """重试辅助工具"""
    
    @staticmethod
    def retry_with_backoff(func, max_retries: int = 3, 
                          initial_delay: float = 1.0, 
                          backoff_factor: float = 2.0):
        """带退避策略的重试装饰器"""
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"尝试 {attempt + 1} 失败，{delay}秒后重试: {str(e)}")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        print(f"所有重试都失败了，抛出最后一个异常")
                        raise last_exception
            
            raise last_exception
        
        return wrapper


def wait_for_condition(condition_func, timeout: float = 30.0, 
                      check_interval: float = 1.0) -> bool:
    """等待条件满足"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(check_interval)
    
    return False


def format_test_result(test_name: str, status: str, 
                      duration: float, message: str = "") -> Dict[str, Any]:
    """格式化测试结果"""
    return {
        "test_name": test_name,
        "status": status,
        "duration": round(duration, 3),
        "message": message,
        "timestamp": datetime.now().isoformat()
    }