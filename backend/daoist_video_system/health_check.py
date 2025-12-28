"""
健康检查模块
提供应用健康状态检查端点
"""

import json
import time
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis
import psutil
import os


def health_check(request):
    """
    应用健康检查端点
    检查数据库、缓存、磁盘空间等关键组件状态
    """
    health_status = {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'version': getattr(settings, 'VERSION', '1.0.0'),
        'checks': {}
    }
    
    # 检查数据库连接
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': '数据库连接正常'
        }
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': f'数据库连接失败: {str(e)}'
        }
    
    # 检查 Redis 缓存
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        if result == 'ok':
            health_status['checks']['cache'] = {
                'status': 'healthy',
                'message': 'Redis 缓存正常'
            }
        else:
            raise Exception('缓存读写测试失败')
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'message': f'Redis 缓存异常: {str(e)}'
        }
    
    # 检查磁盘空间
    try:
        disk_usage = psutil.disk_usage('/')
        free_percent = (disk_usage.free / disk_usage.total) * 100
        
        if free_percent > 10:  # 剩余空间大于10%
            health_status['checks']['disk'] = {
                'status': 'healthy',
                'message': f'磁盘空间充足 ({free_percent:.1f}% 可用)',
                'free_percent': round(free_percent, 1)
            }
        else:
            health_status['status'] = 'unhealthy'
            health_status['checks']['disk'] = {
                'status': 'unhealthy',
                'message': f'磁盘空间不足 ({free_percent:.1f}% 可用)',
                'free_percent': round(free_percent, 1)
            }
    except Exception as e:
        health_status['checks']['disk'] = {
            'status': 'unknown',
            'message': f'无法检查磁盘空间: {str(e)}'
        }
    
    # 检查内存使用
    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        if memory_percent < 90:  # 内存使用率小于90%
            health_status['checks']['memory'] = {
                'status': 'healthy',
                'message': f'内存使用正常 ({memory_percent:.1f}%)',
                'usage_percent': round(memory_percent, 1)
            }
        else:
            health_status['status'] = 'unhealthy'
            health_status['checks']['memory'] = {
                'status': 'unhealthy',
                'message': f'内存使用率过高 ({memory_percent:.1f}%)',
                'usage_percent': round(memory_percent, 1)
            }
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'unknown',
            'message': f'无法检查内存使用: {str(e)}'
        }
    
    # 检查媒体目录
    try:
        media_root = getattr(settings, 'MEDIA_ROOT', '/app/media')
        if os.path.exists(media_root) and os.access(media_root, os.W_OK):
            health_status['checks']['media_storage'] = {
                'status': 'healthy',
                'message': '媒体存储目录可访问'
            }
        else:
            health_status['status'] = 'unhealthy'
            health_status['checks']['media_storage'] = {
                'status': 'unhealthy',
                'message': '媒体存储目录不可访问'
            }
    except Exception as e:
        health_status['checks']['media_storage'] = {
            'status': 'unknown',
            'message': f'无法检查媒体存储: {str(e)}'
        }
    
    # 设置 HTTP 状态码
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return JsonResponse(health_status, status=status_code)


def readiness_check(request):
    """
    就绪检查端点
    检查应用是否准备好接收流量
    """
    readiness_status = {
        'status': 'ready',
        'timestamp': int(time.time()),
        'checks': {}
    }
    
    # 检查数据库迁移状态
    try:
        from django.core.management import execute_from_command_line
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        
        executor = MigrationExecutor(connections['default'])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if not plan:
            readiness_status['checks']['migrations'] = {
                'status': 'ready',
                'message': '数据库迁移已完成'
            }
        else:
            readiness_status['status'] = 'not_ready'
            readiness_status['checks']['migrations'] = {
                'status': 'not_ready',
                'message': f'存在未执行的迁移: {len(plan)} 个'
            }
    except Exception as e:
        readiness_status['status'] = 'not_ready'
        readiness_status['checks']['migrations'] = {
            'status': 'error',
            'message': f'无法检查迁移状态: {str(e)}'
        }
    
    # 检查静态文件
    try:
        static_root = getattr(settings, 'STATIC_ROOT', '/app/staticfiles')
        if os.path.exists(static_root):
            readiness_status['checks']['static_files'] = {
                'status': 'ready',
                'message': '静态文件已收集'
            }
        else:
            readiness_status['status'] = 'not_ready'
            readiness_status['checks']['static_files'] = {
                'status': 'not_ready',
                'message': '静态文件未收集'
            }
    except Exception as e:
        readiness_status['checks']['static_files'] = {
            'status': 'error',
            'message': f'无法检查静态文件: {str(e)}'
        }
    
    status_code = 200 if readiness_status['status'] == 'ready' else 503
    
    return JsonResponse(readiness_status, status=status_code)


def liveness_check(request):
    """
    存活检查端点
    简单检查应用是否还在运行
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': int(time.time()),
        'message': '应用正在运行'
    })