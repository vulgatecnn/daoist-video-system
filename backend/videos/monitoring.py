"""
系统监控服务
提供存储空间监控、数据备份和系统统计功能
"""
import os
import shutil
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Sum, Count, Avg
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from .models import Video, CompositionTask, PlaybackHistory
from users.models import User

logger = logging.getLogger(__name__)


class SystemMonitoringService:
    """系统监控服务类"""
    
    def __init__(self):
        self.media_root = settings.MEDIA_ROOT
        self.backup_root = getattr(settings, 'BACKUP_ROOT', os.path.join(settings.BASE_DIR, 'backups'))
        
    def get_storage_info(self):
        """获取存储空间信息"""
        try:
            # 获取媒体目录的磁盘使用情况
            total, used, free = shutil.disk_usage(self.media_root)
            
            # 计算视频文件总大小
            video_total_size = Video.objects.filter(is_active=True).aggregate(
                total_size=Sum('file_size')
            )['total_size'] or 0
            
            # 计算合成视频文件大小
            composed_files_size = 0
            composed_dir = os.path.join(self.media_root, 'composed')
            if os.path.exists(composed_dir):
                for root, dirs, files in os.walk(composed_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            composed_files_size += os.path.getsize(file_path)
            
            return {
                'disk_total': total,
                'disk_used': used,
                'disk_free': free,
                'disk_usage_percent': (used / total) * 100,
                'video_files_size': video_total_size,
                'composed_files_size': composed_files_size,
                'total_media_size': video_total_size + composed_files_size,
                'warning_threshold': 85,  # 85%使用率警告
                'critical_threshold': 95,  # 95%使用率严重警告
            }
        except Exception as e:
            logger.error(f"获取存储信息失败: {str(e)}")
            return None
    
    def check_storage_warnings(self):
        """检查存储空间警告"""
        storage_info = self.get_storage_info()
        if not storage_info:
            return []
        
        warnings = []
        usage_percent = storage_info['disk_usage_percent']
        
        if usage_percent >= storage_info['critical_threshold']:
            warnings.append({
                'level': 'critical',
                'message': f'磁盘使用率达到 {usage_percent:.1f}%，已超过临界值 {storage_info["critical_threshold"]}%',
                'action': '立即清理磁盘空间或扩容'
            })
        elif usage_percent >= storage_info['warning_threshold']:
            warnings.append({
                'level': 'warning',
                'message': f'磁盘使用率达到 {usage_percent:.1f}%，已超过警告值 {storage_info["warning_threshold"]}%',
                'action': '建议清理不必要的文件或考虑扩容'
            })
        
        return warnings
    
    def get_system_statistics(self):
        """获取系统统计信息"""
        try:
            now = timezone.now()
            last_30_days = now - timedelta(days=30)
            last_7_days = now - timedelta(days=7)
            
            # 用户统计
            total_users = User.objects.count()
            admin_users = User.objects.filter(role='admin').count()
            active_users_30d = PlaybackHistory.objects.filter(
                updated_at__gte=last_30_days
            ).values('user').distinct().count()
            
            # 视频统计
            total_videos = Video.objects.filter(is_active=True).count()
            videos_uploaded_30d = Video.objects.filter(
                upload_time__gte=last_30_days,
                is_active=True
            ).count()
            total_views = Video.objects.filter(is_active=True).aggregate(
                total=Sum('view_count')
            )['total'] or 0
            
            # 合成任务统计
            total_compositions = CompositionTask.objects.count()
            successful_compositions = CompositionTask.objects.filter(
                status='completed'
            ).count()
            failed_compositions = CompositionTask.objects.filter(
                status='failed'
            ).count()
            compositions_7d = CompositionTask.objects.filter(
                created_at__gte=last_7_days
            ).count()
            
            # 播放统计
            total_playbacks = PlaybackHistory.objects.count()
            completed_playbacks = PlaybackHistory.objects.filter(
                completed=True
            ).count()
            avg_completion_rate = PlaybackHistory.objects.aggregate(
                avg_rate=Avg('completion_percentage')
            )['avg_rate'] or 0
            
            return {
                'users': {
                    'total': total_users,
                    'admins': admin_users,
                    'active_30d': active_users_30d,
                },
                'videos': {
                    'total': total_videos,
                    'uploaded_30d': videos_uploaded_30d,
                    'total_views': total_views,
                    'avg_views_per_video': total_views / total_videos if total_videos > 0 else 0,
                },
                'compositions': {
                    'total': total_compositions,
                    'successful': successful_compositions,
                    'failed': failed_compositions,
                    'success_rate': (successful_compositions / total_compositions * 100) if total_compositions > 0 else 0,
                    'recent_7d': compositions_7d,
                },
                'playbacks': {
                    'total': total_playbacks,
                    'completed': completed_playbacks,
                    'completion_rate': (completed_playbacks / total_playbacks * 100) if total_playbacks > 0 else 0,
                    'avg_completion_percentage': avg_completion_rate,
                },
                'storage': self.get_storage_info(),
            }
        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            return None
    
    def create_backup(self, backup_type='full'):
        """创建数据备份"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(self.backup_root, f'backup_{timestamp}')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_info = {
                'timestamp': timestamp,
                'type': backup_type,
                'status': 'in_progress',
                'files_backed_up': [],
                'errors': [],
            }
            
            if backup_type in ['full', 'database']:
                # 备份数据库（SQLite）
                db_path = str(settings.DATABASES['default']['NAME'])  # 确保转换为字符串
                logger.info(f"尝试备份数据库: {db_path}")
                
                if os.path.exists(db_path):
                    backup_db_path = os.path.join(backup_dir, 'database.sqlite3')
                    shutil.copy2(db_path, backup_db_path)
                    backup_info['files_backed_up'].append('database.sqlite3')
                    logger.info(f"数据库备份完成: {backup_db_path}")
                else:
                    error_msg = f"数据库文件不存在: {db_path}"
                    logger.error(error_msg)
                    backup_info['errors'].append(error_msg)
            
            if backup_type in ['full', 'media']:
                # 备份媒体文件
                media_backup_dir = os.path.join(backup_dir, 'media')
                logger.info(f"尝试备份媒体文件: {self.media_root}")
                
                if os.path.exists(self.media_root):
                    shutil.copytree(self.media_root, media_backup_dir, dirs_exist_ok=True)
                    backup_info['files_backed_up'].append('media/')
                    logger.info(f"媒体文件备份完成: {media_backup_dir}")
                else:
                    logger.warning(f"媒体目录不存在: {self.media_root}")
            
            # 创建备份信息文件
            backup_info['status'] = 'completed' if not backup_info['errors'] else 'completed_with_errors'
            backup_info['completed_at'] = datetime.now().isoformat()
            
            info_file = os.path.join(backup_dir, 'backup_info.txt')
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"备份时间: {backup_info['timestamp']}\n")
                f.write(f"备份类型: {backup_info['type']}\n")
                f.write(f"备份状态: {backup_info['status']}\n")
                f.write(f"完成时间: {backup_info['completed_at']}\n")
                f.write(f"备份文件:\n")
                for file in backup_info['files_backed_up']:
                    f.write(f"  - {file}\n")
                if backup_info['errors']:
                    f.write(f"错误信息:\n")
                    for error in backup_info['errors']:
                        f.write(f"  - {error}\n")
            
            logger.info(f"备份创建成功: {backup_dir}")
            return backup_info
            
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            backup_info['status'] = 'failed'
            backup_info['errors'].append(str(e))
            return backup_info
    
    def cleanup_old_backups(self, keep_days=30):
        """清理旧备份文件"""
        try:
            if not os.path.exists(self.backup_root):
                return {'cleaned': 0, 'errors': []}
            
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            cleaned_count = 0
            errors = []
            
            for item in os.listdir(self.backup_root):
                item_path = os.path.join(self.backup_root, item)
                if os.path.isdir(item_path) and item.startswith('backup_'):
                    try:
                        # 从文件夹名称提取时间戳
                        timestamp_str = item.replace('backup_', '')
                        backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        
                        if backup_date < cutoff_date:
                            shutil.rmtree(item_path)
                            cleaned_count += 1
                            logger.info(f"删除旧备份: {item_path}")
                    except Exception as e:
                        errors.append(f"删除备份 {item} 失败: {str(e)}")
            
            return {'cleaned': cleaned_count, 'errors': errors}
            
        except Exception as e:
            logger.error(f"清理旧备份失败: {str(e)}")
            return {'cleaned': 0, 'errors': [str(e)]}
    
    def send_alert_notification(self, alert_type, message, recipients=None):
        """发送警告通知"""
        try:
            if recipients is None:
                # 获取所有管理员邮箱
                recipients = list(User.objects.filter(
                    role='admin',
                    email__isnull=False
                ).exclude(email='').values_list('email', flat=True))
            
            if not recipients:
                logger.warning("没有找到管理员邮箱，无法发送通知")
                return False
            
            subject = f"[道士经文视频系统] {alert_type}警告"
            
            email_body = f"""
系统监控警告通知

警告类型: {alert_type}
警告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
警告内容: {message}

请及时处理相关问题。

---
道士经文视频管理系统
            """.strip()
            
            send_mail(
                subject=subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
            
            logger.info(f"警告通知已发送给 {len(recipients)} 位管理员")
            return True
            
        except Exception as e:
            logger.error(f"发送警告通知失败: {str(e)}")
            return False
    
    def run_monitoring_check(self):
        """运行监控检查"""
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'storage_warnings': [],
                'system_stats': None,
                'notifications_sent': 0,
            }
            
            # 检查存储空间警告
            storage_warnings = self.check_storage_warnings()
            results['storage_warnings'] = storage_warnings
            
            # 发送存储警告通知
            for warning in storage_warnings:
                if warning['level'] == 'critical':
                    if self.send_alert_notification('存储空间严重不足', warning['message']):
                        results['notifications_sent'] += 1
                elif warning['level'] == 'warning':
                    if self.send_alert_notification('存储空间不足', warning['message']):
                        results['notifications_sent'] += 1
            
            # 获取系统统计
            results['system_stats'] = self.get_system_statistics()
            
            logger.info(f"监控检查完成，发送了 {results['notifications_sent']} 个通知")
            return results
            
        except Exception as e:
            logger.error(f"监控检查失败: {str(e)}")
            return {'error': str(e)}


# 单例实例
monitoring_service = SystemMonitoringService()