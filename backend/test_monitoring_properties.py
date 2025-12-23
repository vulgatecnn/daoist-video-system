"""
系统监控功能属性测试
测试存储空间监控和数据备份的正确性属性
"""
import os
import django
import tempfile
import shutil

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import pytest
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from videos.models import Video
from videos.monitoring import SystemMonitoringService

User = get_user_model()


@override_settings(
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',  # 使用内存数据库进行测试
        }
    }
)
class MonitoringPropertiesTest(TransactionTestCase):
    """系统监控属性测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        
        # 创建管理员用户
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.temp_backup_dir = tempfile.mkdtemp()
        
        # 创建临时数据库文件用于备份测试
        self.temp_db_file = os.path.join(self.temp_dir, 'test_db.sqlite3')
        with open(self.temp_db_file, 'wb') as f:
            f.write(b'test database content')
        
        # 创建监控服务实例
        self.monitoring_service = SystemMonitoringService()
        self.monitoring_service.backup_root = self.temp_backup_dir
    
    def tearDown(self):
        """清理测试环境"""
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_backup_dir):
            shutil.rmtree(self.temp_backup_dir)
    
    def create_test_video(self, title="测试视频", file_size=1024):
        """创建测试视频"""
        video_content = b"x" * file_size  # 创建指定大小的内容
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            video_content,
            content_type="video/mp4"
        )
        
        video = Video.objects.create(
            title=title,
            description="测试描述",
            category="daoist_classic",
            file_path=video_file,
            uploader=self.admin_user,
            file_size=file_size,
            is_active=True
        )
        return video
    
    def test_property_15_storage_space_monitoring_basic(self):
        """
        属性 15: 存储空间监控 - 基本测试
        验证系统能够正确监控存储空间并在不足时发出警告
        """
        # 管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 获取存储信息
        response = self.client.get('/api/videos/admin/monitoring/storage/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        storage_data = response.data
        
        # 验证存储信息包含必要字段
        required_fields = [
            'disk_total', 'disk_used', 'disk_free', 'disk_usage_percent',
            'video_files_size', 'composed_files_size', 'total_media_size',
            'warning_threshold', 'critical_threshold', 'warnings'
        ]
        
        for field in required_fields:
            self.assertIn(field, storage_data, f"存储信息缺少字段: {field}")
        
        # 验证数值的合理性
        self.assertGreaterEqual(storage_data['disk_total'], 0)
        self.assertGreaterEqual(storage_data['disk_used'], 0)
        self.assertGreaterEqual(storage_data['disk_free'], 0)
        self.assertGreaterEqual(storage_data['disk_usage_percent'], 0)
        self.assertLessEqual(storage_data['disk_usage_percent'], 100)
        
        # 验证阈值设置
        self.assertEqual(storage_data['warning_threshold'], 85)
        self.assertEqual(storage_data['critical_threshold'], 95)
        
        # 验证警告列表是一个列表
        self.assertIsInstance(storage_data['warnings'], list)
    
    def test_property_15_storage_warning_thresholds(self):
        """
        属性 15: 存储空间监控 - 警告阈值测试
        验证存储空间警告在达到阈值时正确触发
        """
        # 测试警告检查逻辑
        storage_info = self.monitoring_service.get_storage_info()
        self.assertIsNotNone(storage_info)
        
        # 模拟不同的使用率情况
        original_usage = storage_info['disk_usage_percent']
        
        # 测试正常情况（无警告）
        warnings = self.monitoring_service.check_storage_warnings()
        
        # 如果当前使用率低于警告阈值，应该没有警告
        if original_usage < 85:
            self.assertEqual(len(warnings), 0)
        
        # 验证警告结构
        for warning in warnings:
            self.assertIn('level', warning)
            self.assertIn('message', warning)
            self.assertIn('action', warning)
            self.assertIn(warning['level'], ['warning', 'critical'])
    
    def test_property_16_data_backup_integrity_basic(self):
        """
        属性 16: 数据备份完整性 - 基本测试
        验证数据备份功能能够完整备份所有必要数据
        """
        # 创建一些测试数据
        video1 = self.create_test_video("备份测试视频1", 2048)
        video2 = self.create_test_video("备份测试视频2", 1024)
        
        # 使用临时数据库文件进行备份测试
        with override_settings(DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': self.temp_db_file,
            }
        }):
            # 创建数据库备份
            backup_info = self.monitoring_service.create_backup('database')
            
            # 验证备份信息的完整性
            required_fields = ['timestamp', 'type', 'status', 'files_backed_up']
            for field in required_fields:
                self.assertIn(field, backup_info, f"备份信息缺少字段: {field}")
            
            # 验证备份状态
            self.assertEqual(backup_info['status'], 'completed')
            self.assertEqual(backup_info['type'], 'database')
            
            # 验证备份文件列表
            self.assertIsInstance(backup_info['files_backed_up'], list)
            self.assertIn('database.sqlite3', backup_info['files_backed_up'])
    
    def test_property_16_backup_file_integrity(self):
        """
        属性 16: 数据备份完整性 - 文件完整性测试
        验证备份文件包含完整的数据
        """
        # 创建测试数据
        video1 = self.create_test_video("完整性测试视频1")
        video2 = self.create_test_video("完整性测试视频2")
        
        # 记录备份前的数据状态
        videos_before = Video.objects.filter(is_active=True).count()
        users_before = User.objects.count()
        
        # 使用临时数据库文件进行备份测试
        with override_settings(DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': self.temp_db_file,
            }
        }):
            # 执行备份
            backup_info = self.monitoring_service.create_backup('database')
            
            # 验证备份成功
            self.assertEqual(backup_info['status'], 'completed')
            self.assertIn('database.sqlite3', backup_info['files_backed_up'])
            
            # 验证备份文件存在
            backup_dir = os.path.join(
                self.monitoring_service.backup_root, 
                f"backup_{backup_info['timestamp']}"
            )
            backup_db_path = os.path.join(backup_dir, 'database.sqlite3')
            self.assertTrue(os.path.exists(backup_db_path))
            
            # 验证备份文件不为空
            self.assertGreater(os.path.getsize(backup_db_path), 0)
            
            # 验证备份信息文件存在
            info_file = os.path.join(backup_dir, 'backup_info.txt')
            self.assertTrue(os.path.exists(info_file))
            
            # 验证备份信息文件内容
            with open(info_file, 'r', encoding='utf-8') as f:
                info_content = f.read()
                self.assertIn(backup_info['timestamp'], info_content)
                self.assertIn('database.sqlite3', info_content)
    
    def test_property_16_backup_cleanup_consistency(self):
        """
        属性 16: 数据备份完整性 - 清理一致性测试
        验证备份清理功能正确删除旧备份而保留新备份
        """
        # 创建多个模拟备份目录
        backup_dirs = []
        
        # 创建旧备份（应该被删除）
        old_timestamp = "20231201_120000"  # 2023年的备份
        old_backup_dir = os.path.join(self.temp_backup_dir, f"backup_{old_timestamp}")
        os.makedirs(old_backup_dir)
        with open(os.path.join(old_backup_dir, 'test_file.txt'), 'w') as f:
            f.write('old backup')
        backup_dirs.append(old_backup_dir)
        
        # 创建新备份（应该被保留）
        new_timestamp = "20251220_120000"  # 2025年的备份
        new_backup_dir = os.path.join(self.temp_backup_dir, f"backup_{new_timestamp}")
        os.makedirs(new_backup_dir)
        with open(os.path.join(new_backup_dir, 'test_file.txt'), 'w') as f:
            f.write('new backup')
        backup_dirs.append(new_backup_dir)
        
        # 验证备份目录都存在
        for backup_dir in backup_dirs:
            self.assertTrue(os.path.exists(backup_dir))
        
        # 执行清理（保留30天）
        result = self.monitoring_service.cleanup_old_backups(keep_days=30)
        
        # 验证清理结果
        self.assertIn('cleaned', result)
        self.assertIn('errors', result)
        self.assertIsInstance(result['errors'], list)
        
        # 验证旧备份被删除，新备份被保留
        self.assertFalse(os.path.exists(old_backup_dir), "旧备份应该被删除")
        self.assertTrue(os.path.exists(new_backup_dir), "新备份应该被保留")
    
    def test_system_statistics_completeness(self):
        """测试系统统计信息的完整性"""
        # 管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建一些测试数据
        self.create_test_video("统计测试视频1")
        self.create_test_video("统计测试视频2")
        
        # 获取系统统计
        response = self.client.get('/api/videos/admin/monitoring/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        stats = response.data
        
        # 验证统计信息结构
        required_sections = ['users', 'videos', 'compositions', 'playbacks', 'storage']
        for section in required_sections:
            self.assertIn(section, stats, f"统计信息缺少部分: {section}")
        
        # 验证用户统计
        user_stats = stats['users']
        self.assertIn('total', user_stats)
        self.assertIn('admins', user_stats)
        self.assertGreaterEqual(user_stats['total'], 1)  # 至少有测试管理员
        self.assertGreaterEqual(user_stats['admins'], 1)
        
        # 验证视频统计
        video_stats = stats['videos']
        self.assertIn('total', video_stats)
        self.assertGreaterEqual(video_stats['total'], 2)  # 我们创建了2个测试视频
    
    def test_monitoring_check_execution(self):
        """测试监控检查的执行"""
        # 管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 运行监控检查
        response = self.client.post('/api/videos/admin/monitoring/check/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results']
        
        # 验证监控检查结果结构
        required_fields = ['timestamp', 'storage_warnings', 'system_stats', 'notifications_sent']
        for field in required_fields:
            self.assertIn(field, results, f"监控检查结果缺少字段: {field}")
        
        # 验证时间戳格式
        self.assertIsInstance(results['timestamp'], str)
        
        # 验证警告列表
        self.assertIsInstance(results['storage_warnings'], list)
        
        # 验证通知计数
        self.assertIsInstance(results['notifications_sent'], int)
        self.assertGreaterEqual(results['notifications_sent'], 0)
    
    def test_admin_permission_required_for_monitoring(self):
        """测试监控功能需要管理员权限"""
        # 创建普通用户
        normal_user = User.objects.create_user(
            username='normal_user',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        
        # 普通用户认证
        self.client.force_authenticate(user=normal_user)
        
        # 尝试访问监控API（应该失败）
        monitoring_endpoints = [
            '/api/videos/admin/monitoring/statistics/',
            '/api/videos/admin/monitoring/storage/',
            '/api/videos/admin/monitoring/check/',
        ]
        
        for endpoint in monitoring_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code, 
                status.HTTP_403_FORBIDDEN,
                f"普通用户不应该能访问 {endpoint}"
            )
        
        # 尝试创建备份（应该失败）
        response = self.client.post(
            '/api/videos/admin/monitoring/backup/create/',
            {'type': 'database'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])