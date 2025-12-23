"""
管理员功能属性测试
测试视频编辑、删除和批量操作的正确性属性
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
import tempfile
import os
from videos.models import Video

User = get_user_model()


class AdminManagementPropertiesTest(HypothesisTestCase):
    """管理员功能属性测试类"""
    
    def setUp(self):
        """设置测试环境"""
        super().setUp()
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
    
    def create_test_video(self, title="测试视频", description="测试描述", category="经文"):
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
    
    @given(
        title=st.text(min_size=1, max_size=100),
        description=st.text(min_size=1, max_size=500),
        category=st.sampled_from(['经文', '法事', '修行', '其他'])
    )
    @settings(max_examples=50, deadline=10000)
    def test_property_12_video_edit_functionality(self, title, description, category):
        """
        属性 12: 视频编辑功能
        对于任何管理员对视频元数据的编辑操作，修改后的信息应该正确保存并在后续查询中反映出来
        验证需求: 需求 7.2
        """
        # 确保管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建原始视频
        original_video = self.create_test_video(
            title="原始标题",
            description="原始描述", 
            category="经文"
        )
        
        # 准备编辑数据
        edit_data = {
            'title': title,
            'description': description,
            'category': category
        }
        
        # 执行编辑操作
        response = self.client.patch(
            f'/api/videos/admin/{original_video.id}/edit/',
            edit_data,
            format='json'
        )
        
        # 验证编辑成功
        assert response.status_code == status.HTTP_200_OK
        
        # 重新查询视频，验证修改已保存
        updated_video = Video.objects.get(id=original_video.id)
        
        # 验证所有字段都已正确更新
        assert updated_video.title == title
        assert updated_video.description == description
        assert updated_video.category == category
        
        # 验证其他字段未被意外修改
        assert updated_video.uploader == original_video.uploader
        assert updated_video.file_size == original_video.file_size
        assert updated_video.is_active == original_video.is_active
    
    @given(
        video_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_13_video_deletion_integrity(self, video_count):
        """
        属性 13: 视频删除完整性
        对于任何管理员删除的视频，该视频及其相关文件应该从系统中完全移除，且无法再被检索到
        验证需求: 需求 7.3
        """
        # 确保管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建多个测试视频
        created_videos = []
        for i in range(video_count):
            video = self.create_test_video(
                title=f"测试视频{i}",
                description=f"测试描述{i}",
                category="经文"
            )
            created_videos.append(video)
        
        # 记录删除前的视频ID
        video_ids_to_delete = [video.id for video in created_videos]
        
        # 执行批量删除操作
        response = self.client.post(
            '/api/videos/admin/batch-delete/',
            {'video_ids': video_ids_to_delete},
            format='json'
        )
        
        # 验证删除操作成功
        assert response.status_code == status.HTTP_200_OK
        assert response.data['deleted_count'] == video_count
        
        # 验证所有视频都被标记为非活跃状态（软删除）
        for video_id in video_ids_to_delete:
            deleted_video = Video.objects.get(id=video_id)
            assert deleted_video.is_active == False
        
        # 验证普通用户无法通过API检索到已删除的视频
        self.client.force_authenticate(user=self.normal_user)
        
        for video_id in video_ids_to_delete:
            response = self.client.get(f'/api/videos/{video_id}/')
            assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # 验证已删除视频不出现在普通视频列表中
        response = self.client.get('/api/videos/')
        assert response.status_code == status.HTTP_200_OK
        
        active_video_ids = [video['id'] for video in response.data]
        for video_id in video_ids_to_delete:
            assert video_id not in active_video_ids
    
    @given(
        video_count=st.integers(min_value=2, max_value=8),
        new_category=st.sampled_from(['经文', '法事', '修行', '其他'])
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_14_batch_operation_consistency(self, video_count, new_category):
        """
        属性 14: 批量操作一致性
        对于任何批量操作（删除或分类），操作应该对所有选中的视频生效，且操作结果保持一致
        验证需求: 需求 7.5
        """
        # 确保管理员认证
        self.client.force_authenticate(user=self.admin_user)
        
        # 创建多个不同分类的测试视频
        created_videos = []
        original_categories = ['经文', '法事', '修行']
        
        for i in range(video_count):
            video = self.create_test_video(
                title=f"批量测试视频{i}",
                description=f"批量测试描述{i}",
                category=original_categories[i % len(original_categories)]
            )
            created_videos.append(video)
        
        video_ids = [video.id for video in created_videos]
        
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
        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated_count'] == video_count
        
        # 验证所有选中的视频分类都已更新
        for video_id in video_ids:
            updated_video = Video.objects.get(id=video_id)
            assert updated_video.category == new_category
        
        # 验证其他字段未被意外修改
        for i, video_id in enumerate(video_ids):
            updated_video = Video.objects.get(id=video_id)
            original_video = created_videos[i]
            
            assert updated_video.title == original_video.title
            assert updated_video.description == original_video.description
            assert updated_video.uploader == original_video.uploader
            assert updated_video.is_active == original_video.is_active
        
        # 测试批量删除操作的一致性
        # 选择部分视频进行删除
        videos_to_delete = video_ids[:video_count//2] if video_count > 1 else video_ids
        videos_to_keep = video_ids[video_count//2:] if video_count > 1 else []
        
        response = self.client.post(
            '/api/videos/admin/batch-delete/',
            {'video_ids': videos_to_delete},
            format='json'
        )
        
        # 验证批量删除成功
        assert response.status_code == status.HTTP_200_OK
        assert response.data['deleted_count'] == len(videos_to_delete)
        
        # 验证被删除的视频状态一致
        for video_id in videos_to_delete:
            deleted_video = Video.objects.get(id=video_id)
            assert deleted_video.is_active == False
        
        # 验证未被删除的视频状态保持不变
        for video_id in videos_to_keep:
            kept_video = Video.objects.get(id=video_id)
            assert kept_video.is_active == True
    
    def test_admin_permission_required_for_management_operations(self):
        """测试管理操作需要管理员权限"""
        # 创建测试视频
        video = self.create_test_video()
        
        # 切换到普通用户
        self.client.force_authenticate(user=self.normal_user)
        
        # 尝试编辑视频（应该失败）
        response = self.client.patch(
            f'/api/videos/admin/{video.id}/edit/',
            {'title': '新标题'},
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # 尝试批量删除（应该失败）
        response = self.client.post(
            '/api/videos/admin/batch-delete/',
            {'video_ids': [video.id]},
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # 尝试批量更新分类（应该失败）
        response = self.client.post(
            '/api/videos/admin/batch-category/',
            {'video_ids': [video.id], 'category': '法事'},
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


if __name__ == '__main__':
    pytest.main([__file__, '-v'])