"""
错误报告和监控相关的API视图
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from users.permissions import IsAdmin
from .error_reporting import error_reporting_service, performance_monitor
import logging
import json

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def error_statistics(request):
    """获取错误统计信息"""
    try:
        hours = int(request.query_params.get('hours', 24))
        stats = error_reporting_service.get_error_statistics(hours=hours)
        
        return Response({
            'message': '错误统计获取成功',
            'data': stats
        })
    
    except Exception as e:
        logger.error(f"获取错误统计失败: {str(e)}")
        return Response(
            {'error': '获取错误统计失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def performance_statistics(request):
    """获取性能统计信息"""
    try:
        hours = int(request.query_params.get('hours', 1))
        stats = performance_monitor.get_performance_stats(hours=hours)
        
        return Response({
            'message': '性能统计获取成功',
            'data': stats
        })
    
    except Exception as e:
        logger.error(f"获取性能统计失败: {str(e)}")
        return Response(
            {'error': '获取性能统计失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def force_error_report(request):
    """强制生成错误报告"""
    try:
        # 强制发送当前的错误报告
        if error_reporting_service.error_stats:
            error_reporting_service._send_error_report()
            return Response({
                'message': '错误报告已生成并发送'
            })
        else:
            return Response({
                'message': '当前没有错误需要报告'
            })
    
    except Exception as e:
        logger.error(f"强制生成错误报告失败: {str(e)}")
        return Response(
            {'error': '生成错误报告失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def client_error_report(request):
    """接收前端错误报告"""
    try:
        errors = request.data.get('errors', [])
        
        if not errors:
            # 单个错误报告
            error_data = request.data
            errors = [error_data]
        
        # 处理每个错误报告
        for error_data in errors:
            error_info = {
                'error_id': f"client_{error_data.get('timestamp', '')}",
                'method': 'CLIENT',
                'path': error_data.get('url', ''),
                'user': str(request.user),
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': error_data.get('userAgent', ''),
                'exception_type': f"ClientError_{error_data.get('type', 'unknown')}",
                'exception_message': error_data.get('message', ''),
                'traceback': error_data.get('stack', ''),
                'component_stack': error_data.get('componentStack', ''),
                'client_timestamp': error_data.get('timestamp', ''),
                'endpoint': error_data.get('endpoint', ''),
                'status_code': error_data.get('statusCode', '')
            }
            
            # 记录到错误报告服务
            try:
                from .error_reporting import error_reporting_service
                error_reporting_service.record_error(error_info)
            except Exception as e:
                logger.error(f"记录客户端错误到报告服务失败: {str(e)}")
            
            # 记录到日志
            logger.error(f"客户端错误报告: {json.dumps(error_info, ensure_ascii=False)}")
        
        return Response({
            'message': f'已收到 {len(errors)} 个错误报告',
            'received_count': len(errors)
        })
    
    except Exception as e:
        logger.error(f"处理客户端错误报告失败: {str(e)}")
        return Response(
            {'error': '处理错误报告失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def system_health(request):
    """获取系统健康状态"""
    try:
        # 获取最近1小时的统计
        error_stats = error_reporting_service.get_error_statistics(hours=1)
        perf_stats = performance_monitor.get_performance_stats(hours=1)
        
        # 计算健康分数
        health_score = 100
        
        # 根据错误率降低分数
        if error_stats['total_errors'] > 0:
            health_score -= min(error_stats['total_errors'] * 2, 30)
        
        # 根据平均响应时间降低分数
        if perf_stats['avg_response_time'] > 2000:  # 超过2秒
            health_score -= min((perf_stats['avg_response_time'] - 2000) / 100, 20)
        
        # 根据错误率降低分数
        if perf_stats['error_rate'] > 5:  # 错误率超过5%
            health_score -= min(perf_stats['error_rate'] * 2, 25)
        
        health_score = max(health_score, 0)
        
        # 确定健康状态
        if health_score >= 90:
            health_status = 'excellent'
            health_message = '系统运行状态优秀'
        elif health_score >= 70:
            health_status = 'good'
            health_message = '系统运行状态良好'
        elif health_score >= 50:
            health_status = 'warning'
            health_message = '系统运行状态需要关注'
        else:
            health_status = 'critical'
            health_message = '系统运行状态严重，需要立即处理'
        
        return Response({
            'health_score': health_score,
            'health_status': health_status,
            'health_message': health_message,
            'error_stats': error_stats,
            'performance_stats': perf_stats,
            'timestamp': error_reporting_service.last_report_time.isoformat()
        })
    
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        return Response(
            {'error': '获取系统健康状态失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )