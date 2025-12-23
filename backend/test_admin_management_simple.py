"""
管理员功能简化测试
验证管理员功能的基本正确性
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from videos.models import Video

User = get_user_model()


class AdminManagementSimpleTest(TransactionTestCase):
    """管理员功能简化测试类"""
    
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
        
        # 创建普通用户
        self.normal_user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
    
    def create_test_video(self, title="测试视频", description="测试描述", category="daoist_classic"):
        """创建测试视频"""
        # 创建临时视频文件
        video_content = b"fake video content for testing"
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            video_content,
            content_type="video/mp4"
        )
        
        video = Video.objects.create(
            title=title,
            description=description,
            category=category,
            file_path=video_file,
            uploader=self.admin_user,
            file_size=len(video_content),
            is_active=True
        )
        return video
    
    def test_property_12_video_edit_functionality_basic(self):
        """
        属性 12: 视频编辑功能 - 基本测试
        验证管理员可以编辑视频信息并正确保存
        """
        # 管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建原始视频
        original_video = self.create_test_video(
            title="原始标题",
            description="原始描述", 
            category="daoist_classic"
        )
        
        # 准备编辑数据
        edit_data = {
            'title': '新标题',
            'description': '新描述',
            'category': 'ritual'
        }
        
        # 执行编辑操作
        response = self.client.patch(
            f'/api/videos/admin/{original_video.id}/edit/',
            edit_data,
            format='json'
        )
        
        # 打印调试信息
        if response.status_code != status.HTTP_200_OK:
            print(f"Edit response status: {response.status_code}")
            print(f"Edit response data: {response.data}")
        
        # 验证编辑成功
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 重新查询视频，验证修改已保存
        updated_video = Video.objects.get(id=original_video.id)
        
        # 验证所有字段都已正确更新
        self.assertEqual(updated_video.title, '新标题')
        self.assertEqual(updated_video.description, '新描述')
        self.assertEqual(updated_video.category, 'ritual')
        
        # 验证其他字段未被意外修改
        self.assertEqual(updated_video.uploader, original_video.uploader)
        self.assertEqual(updated_video.file_size, original_video.file_size)
        self.assertEqual(updated_video.is_active, original_video.is_active)
    
    def test_property_13_video_deletion_integrity_basic(self):
        """
        属性 13: 视频删除完整性 - 基本测试
        验证管理员删除的视频无法被普通用户检索到
        """
        # 管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建测试视频
        video1 = self.create_test_video(title="测试视频1", description="测试描述1")
        video2 = self.create_test_video(title="测试视频2", description="测试描述2")
        
        video_ids_to_delete = [video1.id, video2.id]
        
        # 执行批量删除操作
        response = self.client.post(
            '/api/videos/admin/batch-delete/',
            {'video_ids': video_ids_to_delete},
            format='json'
        )
        
        # 打印调试信息
        if response.status_code != status.HTTP_200_OK:
            print(f"Delete response status: {response.status_code}")
            print(f"Delete response data: {response.data}")
        
        # 验证删除操作成功
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 2)
        
        # 验证所有视频都被标记为非活跃状态（软删除）
        for video_id in video_ids_to_delete:
            deleted_video = Video.objects.get(id=video_id)
            self.assertFalse(deleted_video.is_active)
        
        # 验证普通用户无法通过API检索到已删除的视频
        self.client.force_authenticate(user=self.normal_user)
        
        for video_id in video_ids_to_delete:
            response = self.client.get(f'/api/videos/{video_id}/')
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # 验证已删除视频不出现在普通视频列表中
        response = self.client.get('/api/videos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 打印调试信息
        print(f"Video list response: {response.data}")
        
        # 检查响应数据格式
        if isinstance(response.data, list):
            active_video_ids = [video['id'] for video in response.data]
        else:
            # 可能是分页响应
            active_video_ids = [video['id'] for video in response.data.get('results', [])]
        
        for video_id in video_ids_to_delete:
            self.assertNotIn(video_id, active_video_ids)
    
    def test_property_14_batch_operation_consistency_basic(self):
        """
        属性 14: 批量操作一致性 - 基本测试
        验证批量操作对所有选中视频生效且结果一致
        """
        # 管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建多个不同分类的测试视频
        video1 = self.create_test_video(title="批量测试视频1", category="daoist_classic")
        video2 = self.create_test_video(title="批量测试视频2", category="ritual")
        video3 = self.create_test_video(title="批量测试视频3", category="meditation")
        
        video_ids = [video1.id, video2.id, video3.id]
        new_category = "other"
        
        # 测试批量分类更新操作
        response = self.client.post(
            '/api/videos/admin/batch-category/',
            {
                'video_ids': video_ids,
                'category': new_category
            },
            format='json'
        )
        
        # 验证批量操作成功
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 3)
        
        # 验证所有选中的视频分类都已更新
        for video_id in video_ids:
            updated_video = Video.objects.get(id=video_id)
            self.assertEqual(updated_video.category, new_category)
        
        # 验证其他字段未被意外修改
        updated_video1 = Video.objects.get(id=video1.id)
        updated_video2 = Video.objects.get(id=video2.id)
        updated_video3 = Video.objects.get(id=video3.id)
        
        self.assertEqual(updated_video1.title, video1.title)
        self.assertEqual(updated_video2.title, video2.title)
        self.assertEqual(updated_video3.title, video3.title)
        
        # 测试批量删除操作的一致性
        videos_to_delete = [video1.id, video2.id]
        videos_to_keep = [video3.id]
        
        response = self.client.post(
            '/api/videos/admin/batch-delete/',
            {'video_ids': videos_to_delete},
            format='json'
        )
        
        # 验证批量删除成功
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 2)
        
        # 验证被删除的视频状态一致
        for video_id in videos_to_delete:
            deleted_video = Video.objects.get(id=video_id)
            self.assertFalse(deleted_video.is_active)
        
        # 验证未被删除的视频状态保持不变
        for video_id in videos_to_keep:
            kept_video = Video.objects.get(id=video_id)
            self.assertTrue(kept_video.is_active)
    
    def test_admin_permission_required_for_management_operations(self):
        """测试管理操作需要管理员权限"""
        # 创建测试视频
        self.client.force_authenticate(user=self.admin_user)
        video = self.create_test_video()
        
        # 切换到普通用户
        self.client.force_authenticate(user=self.normal_user)
        
        # 尝试编辑视频（应该失败）
        response = self.client.patch(
            f'/api/videos/admin/{video.id}/edit/',
            {'title': '新标题'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 尝试批量删除（应该失败）
        response = self.client.post(
            '/api/videos/admin/batch-delete/',
            {'video_ids': [video.id]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 尝试批量更新分类（应该失败）
        response = self.client.post(
            '/api/videos/admin/batch-category/',
            {'video_ids': [video.id], 'category': 'ritual'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])