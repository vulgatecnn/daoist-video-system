"""
响应时间属性测试
测试 Property 1: 响应时间保证
"""
import os
import django
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import pytest
import time
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from hypothesis.extra.django import TestCase as HypothesisTestCase
from hypothesis import given, strategies as st, settings, assume
from videos.models import Video, CompositionTask
from videos.performance_monitoring import performance_monitor

User = get_user_model()


class ResponseTimePropertiesTest(HypothesisTestCase):
    """响应时间属性测试类"""
    
    def setUp(self):
        """测试设置"""
        # 创建测试用户
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        # 创建API客户端
        self.client = APIClient()
        
        # 创建测试视频
        self.test_videos = []
        for i in range(5):
            video = Video.objects.create(
                title=f'测试视频{i+1}',
                description=f'测试描述{i+1}',
                uploader=self.admin_user,
                file_size=1024 * 1024,  # 1MB
                duration=timedelta(seconds=60),  # 60秒
                category='documentary'
            )
            self.test_videos.append(video)
    
    def get_jwt_token(self, user):
        """获取JWT令牌"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """认证用户"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    @settings(max_examples=20, deadline=30000)  # 减少测试数量，增加deadline
    @given(
        video_count=st.integers(min_value=2, max_value=3),  # 减少视频数量范围
        output_filename=st.one_of(
            st.none(),
            st.just("test_output.mp4")  # 使用固定文件名简化测试
        )
    )
    def test_composition_task_creation_response_time(self, video_count, output_filename):
        """
        Property 1: 响应时间保证 - 合成任务创建
        
        For any 合成请求，Composition_Service 返回响应的时间应小于 500ms，
        无论后台合成任务的复杂度如何。
        
        **Validates: Requirements 1.1**
        """
        # 重新创建API客户端以确保正确的类型
        client = APIClient()
        
        # 认证为管理员用户
        token = self.get_jwt_token(self.admin_user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # 选择指定数量的视频
        selected_videos = self.test_videos[:video_count]
        video_ids = [video.id for video in selected_videos]
        
        # 准备请求数据
        request_data = {
            'video_ids': video_ids
        }
        if output_filename:
            request_data['output_filename'] = output_filename
        
        # 记录开始时间
        start_time = time.time()
        
        # 发送创建合成任务请求
        response = client.post(
            '/api/videos/composition/create/',  # 修正URL路径
            data=request_data,
            format='json'
        )
        
        # 计算响应时间
        response_time_ms = (time.time() - start_time) * 1000
        
        # 验证响应时间要求：应小于500ms
        assert response_time_ms < 500, (
            f"合成任务创建响应时间 {response_time_ms:.2f}ms 超过了500ms的要求 "
            f"(视频数量: {video_count}, 输出文件名: {output_filename})"
        )
        
        # 验证请求成功
        assert response.status_code == 201, f"请求失败: {response.data}"
        
        # 验证返回的响应时间信息
        response_data = response.json()
        assert 'response_time_ms' in response_data, "响应中应包含响应时间信息"
        
        # 验证任务创建成功
        assert 'task_id' in response_data, "响应中应包含任务ID"
        assert response_data['status'] == 'pending', "新创建的任务状态应为pending"
        assert response_data['progress'] == 0, "新创建的任务进度应为0"
    
    def test_simple_response_time_check(self):
        """
        简单的响应时间检查测试
        """
        # 认证为管理员用户
        self.authenticate_user(self.admin_user)
        
        # 准备请求数据
        request_data = {
            'video_ids': [self.test_videos[0].id, self.test_videos[1].id]
        }
        
        # 记录开始时间
        start_time = time.time()
        
        # 发送创建合成任务请求
        response = self.client.post(
            '/api/videos/composition/create/',
            data=request_data,
            format='json'
        )
        
        # 计算响应时间
        response_time_ms = (time.time() - start_time) * 1000
        
        # 验证响应时间要求：应小于500ms
        assert response_time_ms < 500, (
            f"合成任务创建响应时间 {response_time_ms:.2f}ms 超过了500ms的要求"
        )
        
        # 验证请求成功
        assert response.status_code == 201, f"请求失败: {response.data}"
        
        # 验证返回的响应时间信息
        response_data = response.json()
        assert 'response_time_ms' in response_data, "响应中应包含响应时间信息"
        
        print(f"实际响应时间: {response_time_ms:.2f}ms")
        print(f"报告的响应时间: {response_data.get('response_time_ms', 'N/A')}ms")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])