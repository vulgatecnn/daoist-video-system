"""
HTTP客户端封装模块

提供统一的HTTP请求接口，包含认证、重试、错误处理等功能。
"""

import json
import time
import requests
from typing import Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .test_helpers import TestLogger, RetryHelper


@dataclass
class HTTPResponse:
    """HTTP响应数据类"""
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json_data: Optional[Dict[str, Any]]
    response_time: float
    url: str
    
    @property
    def is_success(self) -> bool:
        """判断请求是否成功"""
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        """判断是否为客户端错误"""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """判断是否为服务器错误"""
        return 500 <= self.status_code < 600


class APIClient:
    """API客户端封装类"""
    
    def __init__(self, base_url: str, timeout: int = 30, 
                 retry_count: int = 3, retry_delay: float = 1.0):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL
            timeout: 请求超时时间（秒）
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        
        # 创建session
        self.session = requests.Session()
        
        # 设置默认headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'API-Integration-Test-Client/1.0'
        })
        
        # 认证信息
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # 日志记录器
        self.logger = TestLogger("api_client.log")
    
    def set_auth_token(self, access_token: str, refresh_token: str = None, 
                      expires_in: int = 3600):
        """
        设置认证令牌
        
        Args:
            access_token: 访问令牌
            refresh_token: 刷新令牌
            expires_in: 令牌有效期（秒）
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # 更新session headers
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}'
        })
        
        self.logger.info("认证令牌已设置", {
            "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None
        })
    
    def clear_auth(self):
        """清除认证信息"""
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # 移除Authorization header
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        self.logger.info("认证信息已清除")
    
    def is_token_expired(self) -> bool:
        """检查令牌是否过期"""
        if not self.token_expires_at:
            return True
        return datetime.now() >= self.token_expires_at
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _prepare_request_data(self, data: Any) -> Tuple[Optional[str], Dict[str, str]]:
        """准备请求数据"""
        headers = {}
        
        if data is None:
            return None, headers
        
        if isinstance(data, dict):
            # JSON数据
            json_data = json.dumps(data, ensure_ascii=False)
            headers['Content-Type'] = 'application/json'
            return json_data, headers
        elif isinstance(data, str):
            # 字符串数据
            return data, headers
        else:
            # 其他类型转为JSON
            json_data = json.dumps(data, ensure_ascii=False)
            headers['Content-Type'] = 'application/json'
            return json_data, headers
    
    def _make_request(self, method: str, url: str, **kwargs) -> HTTPResponse:
        """执行HTTP请求"""
        start_time = time.time()
        
        try:
            # 记录请求日志
            self.logger.info(f"发送{method}请求", {
                "url": url,
                "headers": dict(self.session.headers),
                "timeout": self.timeout
            })
            
            # 发送请求
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            # 尝试解析JSON
            json_data = None
            try:
                if response.content:
                    json_data = response.json()
            except (json.JSONDecodeError, ValueError):
                pass
            
            # 创建响应对象
            http_response = HTTPResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.content,
                text=response.text,
                json_data=json_data,
                response_time=response_time,
                url=url
            )
            
            # 记录响应日志
            self.logger.info(f"收到响应", {
                "status_code": response.status_code,
                "response_time": response_time,
                "content_length": len(response.content)
            })
            
            return http_response
            
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            self.logger.error("请求超时", {
                "url": url,
                "timeout": self.timeout,
                "response_time": response_time
            })
            raise
        except requests.exceptions.ConnectionError as e:
            response_time = time.time() - start_time
            self.logger.error("连接错误", {
                "url": url,
                "error": str(e),
                "response_time": response_time
            })
            raise
        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error("请求异常", {
                "url": url,
                "error": str(e),
                "response_time": response_time
            })
            raise
    
    def request(self, method: str, endpoint: str, 
                data: Any = None, params: Dict[str, Any] = None,
                headers: Dict[str, str] = None, 
                files: Dict[str, Any] = None,
                **kwargs) -> HTTPResponse:
        """
        发送HTTP请求（带重试机制）
        
        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            params: URL参数
            headers: 额外的请求头
            files: 文件上传
            **kwargs: 其他requests参数
            
        Returns:
            HTTPResponse: 响应对象
        """
        def _make_single_request():
            url = self._build_url(endpoint)
            
            # 准备请求参数
            request_kwargs = kwargs.copy()
            
            # 处理请求数据
            if files is None and data is not None:
                json_data, content_headers = self._prepare_request_data(data)
                request_kwargs['data'] = json_data
                
                # 合并headers
                if headers:
                    content_headers.update(headers)
                if content_headers:
                    request_kwargs['headers'] = content_headers
            else:
                # 文件上传或其他情况
                if data is not None:
                    request_kwargs['data'] = data
                if files is not None:
                    request_kwargs['files'] = files
                if headers:
                    request_kwargs['headers'] = headers
            
            # URL参数
            if params:
                request_kwargs['params'] = params
            
            return self._make_request(method, url, **request_kwargs)
        
        # 使用重试机制
        return RetryHelper.retry_with_backoff(
            _make_single_request,
            max_retries=self.retry_count,
            initial_delay=self.retry_delay,
            backoff_factor=2.0
        )()
    
    def get(self, endpoint: str, params: Dict[str, Any] = None, 
            headers: Dict[str, str] = None, **kwargs) -> HTTPResponse:
        """发送GET请求"""
        return self.request('GET', endpoint, params=params, headers=headers, **kwargs)
    
    def post(self, endpoint: str, data: Any = None, 
             headers: Dict[str, str] = None, files: Dict[str, Any] = None,
             **kwargs) -> HTTPResponse:
        """发送POST请求"""
        return self.request('POST', endpoint, data=data, headers=headers, 
                          files=files, **kwargs)
    
    def put(self, endpoint: str, data: Any = None, 
            headers: Dict[str, str] = None, **kwargs) -> HTTPResponse:
        """发送PUT请求"""
        return self.request('PUT', endpoint, data=data, headers=headers, **kwargs)
    
    def patch(self, endpoint: str, data: Any = None, 
              headers: Dict[str, str] = None, **kwargs) -> HTTPResponse:
        """发送PATCH请求"""
        return self.request('PATCH', endpoint, data=data, headers=headers, **kwargs)
    
    def delete(self, endpoint: str, headers: Dict[str, str] = None, 
               **kwargs) -> HTTPResponse:
        """发送DELETE请求"""
        return self.request('DELETE', endpoint, headers=headers, **kwargs)
    
    def login(self, username: str, password: str, 
              login_endpoint: str = '/api/auth/login/') -> bool:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            login_endpoint: 登录端点
            
        Returns:
            bool: 登录是否成功
        """
        try:
            response = self.post(login_endpoint, {
                'username': username,
                'password': password
            })
            
            if response.is_success and response.json_data:
                # 提取令牌信息
                access_token = response.json_data.get('access')
                refresh_token = response.json_data.get('refresh')
                
                if access_token:
                    self.set_auth_token(access_token, refresh_token)
                    self.logger.info("登录成功", {"username": username})
                    return True
            
            self.logger.warning("登录失败", {
                "username": username,
                "status_code": response.status_code,
                "response": response.json_data
            })
            return False
            
        except Exception as e:
            self.logger.error("登录异常", {
                "username": username,
                "error": str(e)
            })
            return False
    
    def refresh_access_token(self, refresh_endpoint: str = '/api/auth/token/refresh/') -> bool:
        """
        刷新访问令牌
        
        Args:
            refresh_endpoint: 刷新端点
            
        Returns:
            bool: 刷新是否成功
        """
        if not self.refresh_token:
            self.logger.warning("没有刷新令牌，无法刷新访问令牌")
            return False
        
        try:
            response = self.post(refresh_endpoint, {
                'refresh': self.refresh_token
            })
            
            if response.is_success and response.json_data:
                access_token = response.json_data.get('access')
                if access_token:
                    # 更新访问令牌，保持刷新令牌不变
                    self.set_auth_token(access_token, self.refresh_token)
                    self.logger.info("访问令牌刷新成功")
                    return True
            
            self.logger.warning("访问令牌刷新失败", {
                "status_code": response.status_code,
                "response": response.json_data
            })
            return False
            
        except Exception as e:
            self.logger.error("访问令牌刷新异常", {"error": str(e)})
            return False
    
    def logout(self):
        """用户登出"""
        self.clear_auth()
        self.logger.info("用户已登出")
    
    def health_check(self, health_endpoint: str = '/api/monitoring/health/') -> bool:
        """
        健康检查
        
        Args:
            health_endpoint: 健康检查端点
            
        Returns:
            bool: 服务是否健康
        """
        try:
            response = self.get(health_endpoint)
            
            if response.is_success:
                self.logger.info("健康检查通过", {
                    "status_code": response.status_code,
                    "response_time": response.response_time
                })
                return True
            else:
                self.logger.warning("健康检查失败", {
                    "status_code": response.status_code,
                    "response": response.json_data
                })
                return False
                
        except Exception as e:
            self.logger.error("健康检查异常", {"error": str(e)})
            return False
    
    def close(self):
        """关闭客户端"""
        if self.session:
            self.session.close()
        self.logger.info("API客户端已关闭")