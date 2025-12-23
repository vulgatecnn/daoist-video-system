"""
视频系统中间件
包含性能监控中间件
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from .performance_monitoring import performance_monitor

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """性能监控中间件 - 记录API响应时间"""
    
    def process_request(self, request):
        """请求开始时记录时间"""
        request._performance_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """请求结束时计算响应时间并记录"""
        try:
            # 只监控API请求
            if not request.path.startswith('/api/'):
                return response
            
            # 计算响应时间
            start_time = getattr(request, '_performance_start_time', None)
            if start_time is None:
                return response
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # 记录响应时间
            performance_monitor.record_response_time(
                endpoint=request.path,
                method=request.method,
                response_time_ms=response_time_ms,
                status_code=response.status_code
            )
            
            # 在响应头中添加响应时间信息（用于调试）
            response['X-Response-Time'] = f"{response_time_ms:.2f}ms"
            
        except Exception as e:
            logger.error(f"性能监控中间件处理失败: {str(e)}")
        
        return response
    
    def process_exception(self, request, exception):
        """处理异常时也记录响应时间"""
        try:
            # 只监控API请求
            if not request.path.startswith('/api/'):
                return None
            
            start_time = getattr(request, '_performance_start_time', None)
            if start_time is None:
                return None
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # 记录异常请求的响应时间（状态码设为500）
            performance_monitor.record_response_time(
                endpoint=request.path,
                method=request.method,
                response_time_ms=response_time_ms,
                status_code=500
            )
            
        except Exception as e:
            logger.error(f"性能监控中间件异常处理失败: {str(e)}")
        
        return None


class CompositionTaskPerformanceMiddleware(MiddlewareMixin):
    """合成任务性能监控中间件 - 专门监控合成相关API"""
    
    def process_request(self, request):
        """请求开始时记录时间"""
        # 只处理合成相关的API
        if '/api/videos/compose' in request.path:
            request._composition_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """请求结束时检查是否符合性能要求"""
        try:
            # 只处理合成相关的API
            if '/api/videos/compose' not in request.path:
                return response
            
            start_time = getattr(request, '_composition_start_time', None)
            if start_time is None:
                return response
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # 检查合成任务创建API的响应时间要求（500ms）
            if request.path == '/api/videos/compose/' and request.method == 'POST':
                if response_time_ms > 500:
                    logger.warning(
                        f"合成任务创建API响应时间超标: {response_time_ms:.2f}ms > 500ms "
                        f"(用户: {getattr(request.user, 'username', 'anonymous')})"
                    )
                else:
                    logger.info(
                        f"合成任务创建API响应时间: {response_time_ms:.2f}ms "
                        f"(用户: {getattr(request.user, 'username', 'anonymous')})"
                    )
            
            # 检查任务查询API的响应时间要求（100ms）
            elif 'compose/' in request.path and request.method == 'GET':
                if response_time_ms > 100:
                    logger.warning(
                        f"任务查询API响应时间超标: {response_time_ms:.2f}ms > 100ms "
                        f"(路径: {request.path})"
                    )
            
            # 检查任务取消API的响应时间要求（200ms）
            elif 'compose/' in request.path and request.method == 'DELETE':
                if response_time_ms > 200:
                    logger.warning(
                        f"任务取消API响应时间超标: {response_time_ms:.2f}ms > 200ms "
                        f"(路径: {request.path})"
                    )
            
            # 在响应头中添加详细的性能信息
            response['X-Composition-Response-Time'] = f"{response_time_ms:.2f}ms"
            
            # 添加性能要求信息
            if request.path == '/api/videos/compose/' and request.method == 'POST':
                response['X-Performance-Requirement'] = "500ms"
                response['X-Performance-Met'] = "true" if response_time_ms <= 500 else "false"
            elif 'compose/' in request.path and request.method == 'GET':
                response['X-Performance-Requirement'] = "100ms"
                response['X-Performance-Met'] = "true" if response_time_ms <= 100 else "false"
            elif 'compose/' in request.path and request.method == 'DELETE':
                response['X-Performance-Requirement'] = "200ms"
                response['X-Performance-Met'] = "true" if response_time_ms <= 200 else "false"
            
        except Exception as e:
            logger.error(f"合成任务性能监控中间件处理失败: {str(e)}")
        
        return response