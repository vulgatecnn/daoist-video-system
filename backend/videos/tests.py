from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import os

from .models import Video, CompositionTask, VideoSelection

User = get_user_model()


class VideoModelTest(TestCase):
    """视频模型测试"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
    
    def test_video_creation(self):
        """测试视频创建"""
        video = Video.objects.create(
            title='测试视频',
            description='这是一个测试视频',
            category='daoist_classic',
            uploader=self.admin_user
        )
        
        self.assertEqual(video.title, '测试视频')
        self.assertEqual(video.category, 'daoist_classic')
        self.assertEqual(video.uploader, self.admin_user)
        self.assertTrue(video.is_active)
        self.assertEqual(video.view_count, 0)
    
    def test_video_str_method(self):
        """测试视频字符串表示"""
        video = Video.objects.create(
            title='测试视频',
            uploader=self.admin_user
        )
        self.assertEqual(str(video), '测试视频')
    
    def test_increment_view_count(self):
        """测试增加观看次数"""
        video = Video.objects.create(
            title='测试视频',
            uploader=self.admin_user
        )
        
        initial_count = video.view_count
        video.increment_view_count()
        video.refresh_from_db()
        
        self.assertEqual(video.view_count, initial_count + 1)


class CompositionTaskModelTest(TestCase):
    """合成任务模型测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
    
    def test_composition_task_creation(self):
        """测试合成任务创建"""
        task = CompositionTask.objects.create(
            task_id='test_task_123',
            user=self.user,
            video_list=[1, 2, 3]
        )
        
        self.assertEqual(task.task_id, 'test_task_123')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.video_list, [1, 2, 3])
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.progress, 0)
    
    def test_get_video_count(self):
        """测试获取视频数量"""
        task = CompositionTask.objects.create(
            task_id='test_task_123',
            user=self.user,
            video_list=[1, 2, 3, 4, 5]
        )
        
        self.assertEqual(task.get_video_count(), 5)
    
    def test_task_status_methods(self):
        """测试任务状态方法"""
        task = CompositionTask.objects.create(
            task_id='test_task_123',
            user=self.user,
            video_list=[1, 2, 3]
        )
        
        # 测试初始状态
        self.assertFalse(task.is_completed())
        self.assertFalse(task.is_failed())
        self.assertFalse(task.can_download())
        
        # 测试完成状态
        task.status = 'completed'
        task.save()
        self.assertTrue(task.is_completed())
        self.assertFalse(task.is_failed())


class VideoAPITest(APITestCase):
    """视频API测试"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        
        # 创建测试视频
        self.video = Video.objects.create(
            title='测试视频',
            description='这是一个测试视频',
            category='daoist_classic',
            uploader=self.admin_user
        )
    
    def test_video_list_authenticated(self):
        """测试已认证用户获取视频列表"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('videos:video-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_video_list_unauthenticated(self):
        """测试未认证用户无法获取视频列表"""
        url = reverse('videos:video-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_video_detail_increments_view_count(self):
        """测试获取视频详情会增加观看次数"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('videos:video-detail', kwargs={'pk': self.video.pk})
        
        initial_count = self.video.view_count
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.video.refresh_from_db()
        self.assertEqual(self.video.view_count, initial_count + 1)
    
    def test_video_categories(self):
        """测试获取视频分类"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('videos:video-categories')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(len(response.data) > 0)
    
    def test_video_search(self):
        """测试视频搜索"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('videos:video-search')
        response = self.client.get(url, {'q': '测试'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_admin_video_list(self):
        """测试管理员视频列表"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('videos:admin-video-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_regular_user_cannot_access_admin_video_list(self):
        """测试普通用户无法访问管理员视频列表"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('videos:admin-video-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CompositionTaskAPITest(APITestCase):
    """合成任务API测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        # 创建测试视频
        self.video1 = Video.objects.create(
            title='视频1',
            uploader=self.admin_user
        )
        self.video2 = Video.objects.create(
            title='视频2',
            uploader=self.admin_user
        )
    
    def test_create_composition_task(self):
        """测试创建合成任务"""
        self.client.force_authenticate(user=self.user)
        url = reverse('videos:create-composition-task')
        data = {
            'video_ids': [self.video1.id, self.video2.id],
            'output_filename': '合成视频.mp4'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('task_id', response.data)
        self.assertIn('status', response.data)
        self.assertIn('progress', response.data)
        
        # 验证任务已创建
        task = CompositionTask.objects.get(task_id=response.data['task_id'])
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.video_list, [self.video1.id, self.video2.id])
    
    def test_create_composition_task_with_invalid_video_ids(self):
        """测试使用无效视频ID创建合成任务"""
        self.client.force_authenticate(user=self.user)
        url = reverse('videos:create-composition-task')
        data = {
            'video_ids': [999, 1000]  # 不存在的视频ID
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_composition_task_list(self):
        """测试获取合成任务列表"""
        # 创建测试任务
        task = CompositionTask.objects.create(
            task_id='test_task_123',
            user=self.user,
            video_list=[self.video1.id]
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('videos:composition-task-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['task_id'], 'test_task_123')
    
    def test_composition_task_detail(self):
        """测试获取合成任务详情"""
        task = CompositionTask.objects.create(
            task_id='test_task_123',
            user=self.user,
            video_list=[self.video1.id]
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('videos:composition-task-detail', kwargs={'task_id': 'test_task_123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['task_id'], 'test_task_123')
    
    def test_composition_task_detail_not_found(self):
        """测试获取不存在的合成任务详情"""
        self.client.force_authenticate(user=self.user)
        url = reverse('videos:composition-task-detail', kwargs={'task_id': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)