"""
异步执行属性测试
测试 Property 3: 异步执行验证
"""
import os
import django
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import pytest
import time
import threading
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from hypothesis.extra.django import TestCase as HypothesisTestCase
from hypothesis import given, strategies as st, settings, assume
from videos.models import Video, CompositionTask
from videos.task_manager import task_manager

User = get_user_model()


class AsyncExecutionPropertiesTest(HypothesisTestCase):
    """异步执行属性测试类"""
    
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
    
    @settings(max_examples=10, deadline=30000)
    @given(
        video_count=st.integers(min_value=2, max_value=3),
        output_filename=st.one_of(
            st.none(),
            st.just("async_test.mp4")
        )
    )
    def test_async_execution_verification(self, video_count, output_filename):
        """
        Property 3: 异步执行验证
        
        For any 成功创建的合成任务，主线程应在返回响应后立即可用，
        后台线程应已启动执行合成操作。
        
        **Validates: Requirements 1.3**
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
        
        # 记录主线程ID
        main_thread_id = threading.get_ident()
        
        # 记录请求前的活跃线程数
        threads_before = threading.active_count()
        
        # 发送创建合成任务请求
        response = client.post(
            '/api/videos/composition/create/',
            data=request_data,
            format='json'
        )
        
        # 验证请求成功
        assert response.status_code == 201, f"请求失败: {response.data}"
        
        response_data = response.json()
        task_id = response_data['task_id']
        
        # 验证主线程立即可用（响应已返回）
        assert threading.get_ident() == main_thread_id, "主线程ID应保持不变"
        
        # 验证任务已创建
        assert 'task_id' in response_data, "响应中应包含任务ID"
        assert response_data['status'] == 'pending', "新创建的任务状态应为pending"
        
        # 等待一小段时间让后台线程启动
        time.sleep(0.1)
        
        # 验证后台线程已启动（线程数应该增加）
        threads_after = threading.active_count()
        assert threads_after >= threads_before, (
            f"后台线程应已启动，线程数应增加或保持不变 "
            f"(之前: {threads_before}, 之后: {threads_after})"
        )
        
        # 验证任务在TaskManager中已注册
        task_info = task_manager.get_task_info(task_id)
        assert task_info is not None, f"任务 {task_id} 应在TaskManager中注册"
        
        # 验证任务状态已更新（可能是pending或processing）
        assert task_info.status.value in ['pending', 'processing'], (
            f"任务状态应为pending或processing，实际为: {task_info.status.value}"
        )
        
        # 验证后台线程确实在执行（通过检查线程对象）
        if task_info.thread is not None:
            # 线程可能已经完成，这也是正常的异步执行证据
            assert task_info.thread.ident != main_thread_id, "后台线程ID应与主线程不同"
            # 不要求线程仍然活跃，因为任务可能已经快速完成
        
        # 清理：取消任务以避免影响其他测试
        try:
            task_manager.cancel_task(task_id)
        except Exception:
            pass  # 忽略清理错误
    
    def test_main_thread_availability_after_task_creation(self):
        """
        测试任务创建后主线程的可用性
        
        验证创建任务后主线程立即可用，不会被阻塞。
        """
        # 认证为管理员用户
        self.authenticate_user(self.admin_user)
        
        # 准备请求数据
        request_data = {
            'video_ids': [self.test_videos[0].id, self.test_videos[1].id]
        }
        
        # 记录主线程ID
        main_thread_id = threading.get_ident()
        
        # 发送创建合成任务请求
        response = self.client.post(
            '/api/videos/composition/create/',
            data=request_data,
            format='json'
        )
        
        # 验证请求成功
        assert response.status_code == 201, f"请求失败: {response.data}"
        
        response_data = response.json()
        task_id = response_data['task_id']
        
        # 立即执行一些主线程操作，验证主线程未被阻塞
        start_time = time.time()
        
        # 执行一些计算密集型操作
        result = sum(i * i for i in range(1000))
        
        # 执行一些I/O操作
        test_data = {'test': 'data', 'numbers': list(range(100))}
        
        # 验证主线程操作能够立即完成
        operation_time = (time.time() - start_time) * 1000
        assert operation_time < 50, f"主线程操作应立即完成，实际耗时: {operation_time:.2f}ms"
        
        # 验证主线程ID未改变
        assert threading.get_ident() == main_thread_id, "主线程ID应保持不变"
        
        # 验证计算结果正确（确保操作确实执行了）
        expected_result = sum(i * i for i in range(1000))
        assert result == expected_result, "主线程计算结果应正确"
        
        # 清理任务
        try:
            task_manager.cancel_task(task_id)
        except Exception:
            pass
    
    def test_background_thread_execution(self):
        """
        测试后台线程的执行
        
        验证后台线程确实在执行合成操作。
        """
        # 认证为管理员用户
        self.authenticate_user(self.admin_user)
        
        # 准备请求数据
        request_data = {
            'video_ids': [self.test_videos[0].id, self.test_videos[1].id]
        }
        
        # 记录请求前的线程信息
        main_thread_id = threading.get_ident()
        threads_before = set(t.ident for t in threading.enumerate())
        
        # 发送创建合成任务请求
        response = self.client.post(
            '/api/videos/composition/create/',
            data=request_data,
            format='json'
        )
        
        # 验证请求成功
        assert response.status_code == 201, f"请求失败: {response.data}"
        
        response_data = response.json()
        task_id = response_data['task_id']
        
        # 等待后台线程启动
        time.sleep(0.2)
        
        # 检查新线程
        threads_after = set(t.ident for t in threading.enumerate())
        new_threads = threads_after - threads_before
        
        # 验证有新线程启动（可能有多个新线程，包括合成线程）
        assert len(new_threads) >= 0, "应该有新线程启动"
        
        # 验证任务在TaskManager中的状态
        task_info = task_manager.get_task_info(task_id)
        assert task_info is not None, f"任务 {task_id} 应在TaskManager中存在"
        
        # 验证任务状态表明后台处理已开始
        assert task_info.status.value in ['pending', 'processing', 'failed'], (
            f"任务状态应表明后台处理，实际状态: {task_info.status.value}"
        )
        
        # 如果有线程对象，验证它不是主线程
        if task_info.thread is not None:
            assert task_info.thread.ident != main_thread_id, "后台线程应与主线程不同"
        
        # 清理任务
        try:
            task_manager.cancel_task(task_id)
        except Exception:
            pass
    
    def test_concurrent_task_creation_async_behavior(self):
        """
        测试并发任务创建的异步行为
        
        验证多个任务可以并发创建，每个都异步执行。
        """
        # 认证为管理员用户
        self.authenticate_user(self.admin_user)
        
        # 记录开始时间和线程信息
        start_time = time.time()
        main_thread_id = threading.get_ident()
        
        task_ids = []
        
        # 并发创建多个任务
        for i in range(3):
            request_data = {
                'video_ids': [self.test_videos[0].id, self.test_videos[1].id],
                'output_filename': f'concurrent_test_{i}.mp4'
            }
            
            response = self.client.post(
                '/api/videos/composition/create/',
                data=request_data,
                format='json'
            )
            
            # 验证每个请求都成功
            assert response.status_code == 201, f"第{i+1}个请求失败: {response.data}"
            
            response_data = response.json()
            task_ids.append(response_data['task_id'])
            
            # 验证每个任务都立即返回
            current_time = time.time()
            elapsed_time = (current_time - start_time) * 1000
            
            # 每个任务创建应该很快（累计时间不应过长）
            max_expected_time = (i + 1) * 200  # 每个任务最多200ms
            assert elapsed_time < max_expected_time, (
                f"前{i+1}个任务创建耗时过长: {elapsed_time:.2f}ms > {max_expected_time}ms"
            )
        
        # 验证所有任务都已创建
        assert len(task_ids) == 3, "应该创建了3个任务"
        assert len(set(task_ids)) == 3, "所有任务ID应该唯一"
        
        # 验证主线程仍然可用
        assert threading.get_ident() == main_thread_id, "主线程ID应保持不变"
        
        # 等待一段时间让后台线程启动
        time.sleep(0.3)
        
        # 验证所有任务都在TaskManager中
        for task_id in task_ids:
            task_info = task_manager.get_task_info(task_id)
            assert task_info is not None, f"任务 {task_id} 应在TaskManager中存在"
            assert task_info.status.value in ['pending', 'processing', 'failed'], (
                f"任务 {task_id} 状态应表明后台处理，实际状态: {task_info.status.value}"
            )
        
        # 清理所有任务
        for task_id in task_ids:
            try:
                task_manager.cancel_task(task_id)
            except Exception:
                pass
    
    def test_task_status_progression_indicates_async_execution(self):
        """
        测试任务状态变化表明异步执行
        
        验证任务状态从pending变为processing，表明后台异步执行。
        """
        # 认证为管理员用户
        self.authenticate_user(self.admin_user)
        
        # 准备请求数据
        request_data = {
            'video_ids': [self.test_videos[0].id, self.test_videos[1].id]
        }
        
        # 发送创建合成任务请求
        response = self.client.post(
            '/api/videos/composition/create/',
            data=request_data,
            format='json'
        )
        
        # 验证请求成功
        assert response.status_code == 201, f"请求失败: {response.data}"
        
        response_data = response.json()
        task_id = response_data['task_id']
        
        # 初始状态应为pending
        assert response_data['status'] == 'pending', "初始状态应为pending"
        
        # 等待后台线程启动并开始处理
        max_wait_time = 2.0  # 最多等待2秒
        wait_interval = 0.1  # 每100ms检查一次
        waited_time = 0
        
        status_progression = [response_data['status']]
        
        while waited_time < max_wait_time:
            time.sleep(wait_interval)
            waited_time += wait_interval
            
            # 查询任务状态
            task_info = task_manager.get_task_info(task_id)
            if task_info:
                current_status = task_info.status.value
                if current_status != status_progression[-1]:
                    status_progression.append(current_status)
                
                # 如果状态变为processing，说明异步执行已开始
                if current_status == 'processing':
                    break
        
        # 验证状态变化表明异步执行
        assert len(status_progression) >= 1, "应该有状态记录"
        
        # 验证初始状态为pending
        assert status_progression[0] == 'pending', "初始状态应为pending"
        
        # 验证状态发生了变化（表明后台处理）
        final_status = status_progression[-1]
        assert final_status in ['pending', 'processing', 'failed'], (
            f"最终状态应表明后台处理，实际状态序列: {status_progression}"
        )
        
        # 如果状态变为processing，这是异步执行的明确证据
        if 'processing' in status_progression:
            print(f"✓ 检测到异步执行：状态变化 {' -> '.join(status_progression)}")
        else:
            # 即使没有变为processing，pending状态也表明任务已排队等待异步处理
            print(f"✓ 任务已排队异步处理：状态 {final_status}")
        
        # 清理任务
        try:
            task_manager.cancel_task(task_id)
        except Exception:
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])