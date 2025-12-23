"""
全局中间件
"""
import logging
import traceback
import json
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware:
    """全局异常处理中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """处理未捕获的异常"""
        # 记录异常详情
        error_id = self._log_exception(request, exception)
        
        # 根据异常类型返回相应的错误响应
        if isinstance(exception, ValidationError):
            return self._handle_validation_error(exception, error_id)
        elif isinstance(exception, PermissionDenied):
            return self._handle_permission_error(exception, error_id)
        elif isinstance(exception, IntegrityError):
            return self._handle_integrity_error(exception, error_id)
        else:
            return self._handle_generic_error(exception, error_id)
    
    def _log_exception(self, request, exception):
        """记录异常信息并返回错误ID"""
        import uuid
        error_id = str(uuid.uuid4())[:8]
        
        # 收集请求信息
        request_info = {
            'error_id': error_id,
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc()
        }
        
        # 记录POST数据（敏感信息除外）
        if request.method == 'POST':
            try:
                post_data = request.POST.copy()
                # 移除敏感字段
                sensitive_fields = ['password', 'token', 'secret', 'key']
                for field in sensitive_fields:
                    if field in post_data:
                        post_data[field] = '***'
                request_info['post_data'] = dict(post_data)
            except:
                request_info['post_data'] = 'Unable to parse POST data'
        
        logger.error(f"未处理的异常 [{error_id}]: {json.dumps(request_info, ensure_ascii=False, indent=2)}")
        
        # 发送到错误报告服务
        try:
            from .error_reporting import error_reporting_service
            error_reporting_service.record_error(request_info)
        except Exception as e:
            logger.error(f"记录错误到报告服务失败: {str(e)}")
        
        return error_id
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _handle_validation_error(self, exception, error_id):
        """处理验证错误"""
        return JsonResponse({
            'error': '数据验证失败',
            'details': str(exception),
            'error_id': error_id
        }, status=400)
    
    def _handle_permission_error(self, exception, error_id):
        """处理权限错误"""
        return JsonResponse({
            'error': '权限不足',
            'details': '您没有执行此操作的权限',
            'error_id': error_id
        }, status=403)
    
    def _handle_integrity_error(self, exception, error_id):
        """处理数据完整性错误"""
        return JsonResponse({
            'error': '数据完整性错误',
            'details': '操作违反了数据完整性约束',
            'error_id': error_id
        }, status=400)
    
    def _handle_generic_error(self, exception, error_id):
        """处理通用错误"""
        return JsonResponse({
            'error': '服务器内部错误',
            'details': '系统遇到了未预期的错误，请稍后重试',
            'error_id': error_id
        }, status=500)


class RequestLoggingMiddleware:
    """请求日志记录中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('request')
    
    def __call__(self, request):
        # 记录请求开始
        start_time = self._get_current_time()
        
        # 记录请求信息
        self._log_request_start(request)
        
        # 处理请求
        response = self.get_response(request)
        
        # 记录响应信息
        end_time = self._get_current_time()
        duration = end_time - start_time
        self._log_request_end(request, response, duration)
        
        return response
    
    def _get_current_time(self):
        """获取当前时间（毫秒）"""
        import time
        return int(time.time() * 1000)
    
    def _log_request_start(self, request):
        """记录请求开始"""
        # 只记录API请求
        if request.path.startswith('/api/'):
            self.logger.info(f"请求开始: {request.method} {request.path} - 用户: {getattr(request, 'user', 'Anonymous')}")
    
    def _log_request_end(self, request, response, duration):
        """记录请求结束"""
        # 只记录API请求
        if request.path.startswith('/api/'):
            status_code = getattr(response, 'status_code', 'Unknown')
            self.logger.info(f"请求完成: {request.method} {request.path} - 状态码: {status_code} - 耗时: {duration}ms")
            
            # 记录到性能监控
            try:
                from .error_reporting import performance_monitor
                performance_monitor.record_request(
                    path=request.path,
                    method=request.method,
                    duration=duration,
                    status_code=status_code
                )
            except Exception as e:
                self.logger.error(f"记录性能数据失败: {str(e)}")
            
            # 记录慢请求
            if duration > 5000:  # 超过5秒的请求
                self.logger.warning(f"慢请求警告: {request.method} {request.path} - 耗时: {duration}ms")


def custom_exception_handler(exc, context):
    """自定义DRF异常处理器"""
    # 调用DRF默认的异常处理器
    response = exception_handler(exc, context)
    
    if response is not None:
        # 获取请求信息
        request = context.get('request')
        view = context.get('view')
        
        # 记录异常信息
        error_info = {
            'exception_type': type(exc).__name__,
            'exception_message': str(exc),
            'view': str(view) if view else 'Unknown',
            'method': request.method if request else 'Unknown',
            'path': request.path if request else 'Unknown',
            'user': str(request.user) if request and hasattr(request, 'user') else 'Anonymous'
        }
        
        logger.warning(f"DRF异常处理: {json.dumps(error_info, ensure_ascii=False)}")
        
        # 自定义错误响应格式
        custom_response_data = {
            'error': True,
            'message': '请求处理失败',
            'details': response.data,
            'status_code': response.status_code
        }
        
        # 根据异常类型提供更友好的错误信息
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                # 字段验证错误
                custom_response_data['message'] = '数据验证失败'
                custom_response_data['field_errors'] = exc.detail
            elif isinstance(exc.detail, list):
                # 非字段错误
                custom_response_data['message'] = exc.detail[0] if exc.detail else '请求处理失败'
            else:
                # 字符串错误信息
                custom_response_data['message'] = str(exc.detail)
        
        response.data = custom_response_data
    
    return response