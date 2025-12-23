"""
环境配置模块

管理测试环境变量和配置文件。
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库配置"""
    name: str
    engine: str = 'django.db.backends.sqlite3'
    host: str = ''
    port: str = ''
    user: str = ''
    password: str = ''
    
    def get_django_config(self) -> Dict[str, Any]:
        """获取Django数据库配置"""
        config = {
            'ENGINE': self.engine,
            'NAME': self.name,
        }
        
        if self.host:
            config['HOST'] = self.host
        if self.port:
            config['PORT'] = self.port
        if self.user:
            config['USER'] = self.user
        if self.password:
            config['PASSWORD'] = self.password
            
        return config


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = 'localhost'
    port: int = 6000
    protocol: str = 'http'
    
    @property
    def base_url(self) -> str:
        """获取基础URL"""
        return f"{self.protocol}://{self.host}:{self.port}"


class EnvironmentConfig:
    """环境配置管理器"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        初始化环境配置
        
        Args:
            env_file: 环境变量文件路径
        """
        self.env_file = env_file
        self._load_env_file()
    
    def _load_env_file(self):
        """加载环境变量文件"""
        if self.env_file and Path(self.env_file).exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
    
    def get_str(self, key: str, default: str = '') -> str:
        """获取字符串配置"""
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = os.getenv(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        else:
            return default
    
    def get_list(self, key: str, separator: str = ',', default: list = None) -> list:
        """获取列表配置"""
        if default is None:
            default = []
        
        value = os.getenv(key, '')
        if not value:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def get_dict(self, key: str, separator: str = ',', 
                 kv_separator: str = '=', default: dict = None) -> dict:
        """获取字典配置"""
        if default is None:
            default = {}
        
        value = os.getenv(key, '')
        if not value:
            return default
        
        result = {}
        for item in value.split(separator):
            item = item.strip()
            if kv_separator in item:
                k, v = item.split(kv_separator, 1)
                result[k.strip()] = v.strip()
        
        return result
    
    def get_backend_config(self) -> ServerConfig:
        """获取后端服务器配置"""
        return ServerConfig(
            host=self.get_str('BACKEND_HOST', 'localhost'),
            port=self.get_int('BACKEND_PORT', 6000),
            protocol=self.get_str('BACKEND_PROTOCOL', 'http')
        )
    
    def get_frontend_config(self) -> ServerConfig:
        """获取前端服务器配置"""
        return ServerConfig(
            host=self.get_str('FRONTEND_HOST', 'localhost'),
            port=self.get_int('FRONTEND_PORT', 5500),
            protocol=self.get_str('FRONTEND_PROTOCOL', 'http')
        )
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return DatabaseConfig(
            name=self.get_str('TEST_DB_NAME', 'test_db.sqlite3'),
            engine=self.get_str('TEST_DB_ENGINE', 'django.db.backends.sqlite3'),
            host=self.get_str('TEST_DB_HOST', ''),
            port=self.get_str('TEST_DB_PORT', ''),
            user=self.get_str('TEST_DB_USER', ''),
            password=self.get_str('TEST_DB_PASSWORD', '')
        )
    
    def get_test_user_config(self) -> Dict[str, str]:
        """获取测试用户配置"""
        return {
            'username': self.get_str('TEST_USERNAME', 'testuser'),
            'password': self.get_str('TEST_PASSWORD', 'testpass123'),
            'email': self.get_str('TEST_EMAIL', 'testuser@test.com')
        }
    
    def get_admin_user_config(self) -> Dict[str, str]:
        """获取管理员用户配置"""
        return {
            'username': self.get_str('ADMIN_USERNAME', 'admin'),
            'password': self.get_str('ADMIN_PASSWORD', 'admin123'),
            'email': self.get_str('ADMIN_EMAIL', 'admin@test.com')
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return {
            'timeout': self.get_int('API_TIMEOUT', 30),
            'retry_count': self.get_int('API_RETRY_COUNT', 3),
            'retry_delay': self.get_float('API_RETRY_DELAY', 1.0),
            'max_retry_delay': self.get_float('API_MAX_RETRY_DELAY', 10.0)
        }
    
    def get_test_config(self) -> Dict[str, Any]:
        """获取测试配置"""
        return {
            'parallel_workers': self.get_int('TEST_PARALLEL_WORKERS', 1),
            'output_dir': self.get_str('TEST_OUTPUT_DIR', 'test_results'),
            'log_level': self.get_str('TEST_LOG_LEVEL', 'INFO'),
            'generate_html_report': self.get_bool('TEST_GENERATE_HTML_REPORT', True),
            'generate_json_report': self.get_bool('TEST_GENERATE_JSON_REPORT', True),
            'cleanup_test_data': self.get_bool('TEST_CLEANUP_TEST_DATA', True)
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能测试配置"""
        return {
            'max_response_time': self.get_float('PERF_MAX_RESPONSE_TIME', 5.0),
            'concurrent_users': self.get_int('PERF_CONCURRENT_USERS', 10),
            'test_duration': self.get_int('PERF_TEST_DURATION', 60),
            'ramp_up_time': self.get_int('PERF_RAMP_UP_TIME', 10)
        }
    
    def is_debug_mode(self) -> bool:
        """是否为调试模式"""
        return self.get_bool('DEBUG', False)
    
    def is_ci_environment(self) -> bool:
        """是否为CI环境"""
        return self.get_bool('CI', False) or self.get_str('GITHUB_ACTIONS') == 'true'
    
    def should_skip_slow_tests(self) -> bool:
        """是否跳过慢速测试"""
        return self.get_bool('SKIP_SLOW_TESTS', False)
    
    def should_skip_network_tests(self) -> bool:
        """是否跳过网络测试"""
        return self.get_bool('SKIP_NETWORK_TESTS', False)
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            'backend': self.get_backend_config(),
            'frontend': self.get_frontend_config(),
            'database': self.get_database_config(),
            'test_user': self.get_test_user_config(),
            'admin_user': self.get_admin_user_config(),
            'api': self.get_api_config(),
            'test': self.get_test_config(),
            'performance': self.get_performance_config(),
            'debug_mode': self.is_debug_mode(),
            'ci_environment': self.is_ci_environment(),
            'skip_slow_tests': self.should_skip_slow_tests(),
            'skip_network_tests': self.should_skip_network_tests()
        }


# 全局配置实例
env_config = EnvironmentConfig(env_file='.env')