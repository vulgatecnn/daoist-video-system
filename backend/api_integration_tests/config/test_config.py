"""
测试配置管理模块

提供测试环境的配置管理功能，包括API端点、超时设置、重试策略等。
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class APIEndpoint:
    """API端点配置"""
    name: str
    url: str
    method: str
    requires_auth: bool
    expected_response_schema: Dict[str, Any]
    test_cases: List[Dict[str, Any]]


class TestConfigManager:
    """测试配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:6000")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5500")
        self.timeout = int(os.getenv("API_TIMEOUT", "30"))
        self.retry_count = int(os.getenv("API_RETRY_COUNT", "3"))
        self.retry_delay = float(os.getenv("API_RETRY_DELAY", "1.0"))
        
        # 测试数据库配置
        self.test_db_name = os.getenv("TEST_DB_NAME", "test_db.sqlite3")
        
        # 测试用户配置
        self.test_username = os.getenv("TEST_USERNAME", "testuser")
        self.test_password = os.getenv("TEST_PASSWORD", "testpass123")
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    def get_api_endpoints(self) -> Dict[str, Dict[str, APIEndpoint]]:
        """获取所有API端点配置"""
        return {
            "auth": {
                "login": APIEndpoint(
                    name="用户登录",
                    url="/api/auth/login/",
                    method="POST",
                    requires_auth=False,
                    expected_response_schema={
                        "access": "string",
                        "refresh": "string",
                        "user": "object"
                    },
                    test_cases=[
                        {"username": self.test_username, "password": self.test_password},
                        {"username": "invalid", "password": "wrong"}
                    ]
                ),
                "register": APIEndpoint(
                    name="用户注册",
                    url="/api/auth/register/",
                    method="POST",
                    requires_auth=False,
                    expected_response_schema={
                        "user": "object",
                        "message": "string"
                    },
                    test_cases=[
                        {
                            "username": "newuser",
                            "email": "newuser@test.com",
                            "password": "newpass123"
                        }
                    ]
                ),
                "refresh": APIEndpoint(
                    name="令牌刷新",
                    url="/api/auth/token/refresh/",
                    method="POST",
                    requires_auth=False,
                    expected_response_schema={
                        "access": "string"
                    },
                    test_cases=[
                        {"refresh": "valid_refresh_token"}
                    ]
                )
            },
            "videos": {
                "list": APIEndpoint(
                    name="视频列表",
                    url="/api/videos/",
                    method="GET",
                    requires_auth=True,
                    expected_response_schema={
                        "count": "integer",
                        "results": "array"
                    },
                    test_cases=[
                        {"page": 1, "page_size": 10},
                        {"search": "test"}
                    ]
                ),
                "detail": APIEndpoint(
                    name="视频详情",
                    url="/api/videos/{id}/",
                    method="GET",
                    requires_auth=True,
                    expected_response_schema={
                        "id": "integer",
                        "title": "string",
                        "description": "string",
                        "file": "string"
                    },
                    test_cases=[
                        {"id": 1},
                        {"id": 999}  # 不存在的ID
                    ]
                ),
                "upload": APIEndpoint(
                    name="视频上传",
                    url="/api/videos/upload/",
                    method="POST",
                    requires_auth=True,
                    expected_response_schema={
                        "id": "integer",
                        "message": "string"
                    },
                    test_cases=[
                        {"file": "test_video.mp4", "title": "测试视频"}
                    ]
                )
            },
            "composition": {
                "create": APIEndpoint(
                    name="创建合成任务",
                    url="/api/videos/composition/create/",
                    method="POST",
                    requires_auth=True,
                    expected_response_schema={
                        "task_id": "string",
                        "status": "string"
                    },
                    test_cases=[
                        {
                            "video_ids": [1, 2],
                            "output_format": "mp4",
                            "quality": "high"
                        }
                    ]
                ),
                "status": APIEndpoint(
                    name="查询任务状态",
                    url="/api/videos/composition/{task_id}/",
                    method="GET",
                    requires_auth=True,
                    expected_response_schema={
                        "task_id": "string",
                        "status": "string",
                        "progress": "number"
                    },
                    test_cases=[
                        {"task_id": "test_task_id"}
                    ]
                )
            },
            "monitoring": {
                "health": APIEndpoint(
                    name="健康检查",
                    url="/api/monitoring/health/",
                    method="GET",
                    requires_auth=False,
                    expected_response_schema={
                        "status": "string",
                        "timestamp": "string"
                    },
                    test_cases=[{}]
                ),
                "statistics": APIEndpoint(
                    name="系统统计",
                    url="/api/videos/admin/monitoring/statistics/",
                    method="GET",
                    requires_auth=True,
                    expected_response_schema={
                        "user_count": "integer",
                        "video_count": "integer"
                    },
                    test_cases=[{}]
                )
            }
        }
    
    def get_test_data(self) -> Dict[str, Any]:
        """获取测试数据"""
        return {
            "valid_user": {
                "username": self.test_username,
                "password": self.test_password,
                "email": f"{self.test_username}@test.com"
            },
            "admin_user": {
                "username": self.admin_username,
                "password": self.admin_password,
                "email": f"{self.admin_username}@test.com"
            },
            "invalid_user": {
                "username": "invalid",
                "password": "wrong"
            },
            "test_video": {
                "title": "测试视频",
                "description": "这是一个测试视频",
                "category": "道德经"
            },
            "composition_request": {
                "video_ids": [1, 2],
                "output_format": "mp4",
                "quality": "high"
            }
        }
    
    def get_base_url(self) -> str:
        """获取后端API基础URL"""
        return self.backend_url
    
    def get_timeout(self) -> int:
        """获取请求超时时间"""
        return self.timeout
    
    def get_retry_config(self) -> Dict[str, Any]:
        """获取重试配置"""
        return {
            "count": self.retry_count,
            "delay": self.retry_delay
        }