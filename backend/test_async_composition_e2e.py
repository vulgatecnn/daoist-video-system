#!/usr/bin/env python
"""
端到端测试异步视频合成功能
"""
import os
import sys
import django
from pathlib import Path
import time
import uuid

# 添加项目路径到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from videos.models import Video, CompositionTask
from videos.task_manager import task_manager

User = get_user_model()


def test_async_composition_e2e():
    """端到端测试异步视频合成"""
    print("🚀 开始端到端异步视频合成测试...")
    
    try:
        # 1. 创建测试用户
        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'testuser_{unique_id}',
            email=f'test_{unique_id}@example.com',
            password='testpass123',
            role='user'
        )
        print(f"✅ 创建测试用户: {user.username}")
        
        # 2. 创建测试视频
        from datetime import timedelta
        
        video1 = Video.objects.create(
            title='测试视频1',
            description='用于合成测试的视频1',
            uploader=user,
            file_path='test_video_1.mp4',
            file_size=1024000,
            duration=timedelta(seconds=30),
            category='test'
        )
        
        video2 = Video.objects.create(
            title='测试视频2',
            description='用于合成测试的视频2',
            uploader=user,
            file_path='test_video_2.mp4',
            file_size=2048000,
            duration=timedelta(seconds=45),
            category='test'
        )
        print(f"✅ 创建测试视频: {video1.title}, {video2.title}")
        
        # 3. 测试任务管理器注册任务
        task_id = task_manager.register_task(
            user_id=user.id,
            video_ids=[video1.id, video2.id]
        )
        print(f"✅ 注册任务成功: {task_id}")
        
        # 4. 创建数据库记录
        task = CompositionTask.objects.create(
            task_id=task_id,
            user=user,
            video_list=[video1.id, video2.id],
            output_filename=f"test_composition_{unique_id}.mp4",
            status='pending'
        )
        print(f"✅ 创建数据库记录: {task.task_id}")
        
        # 5. 测试任务状态查询
        from videos.task_manager import TaskStatus
        
        task_info = task_manager.get_task_info(task_id)
        assert task_info is not None, "任务信息不应为空"
        assert task_info.status == TaskStatus.PENDING, f"任务状态应为PENDING，实际为{task_info.status}"
        print(f"✅ 任务状态查询正常: {task_info.status}")
        
        # 6. 测试进度更新
        task_manager.update_task_progress(task_id, 25, status='processing')
        
        # 验证TaskManager中的状态
        updated_task_info = task_manager.get_task_info(task_id)
        assert updated_task_info.progress == 25, f"进度应为25，实际为{updated_task_info.progress}"
        assert updated_task_info.status == TaskStatus.PROCESSING, f"状态应为PROCESSING，实际为{updated_task_info.status}"
        print(f"✅ 进度更新正常: {updated_task_info.progress}%")
        
        # 7. 测试任务取消
        cancel_result = task_manager.cancel_task(task_id)
        assert cancel_result['success'], f"取消任务失败: {cancel_result['message']}"
        
        # 验证取消状态
        task_info = task_manager.get_task_info(task_id)
        assert task_info.status == TaskStatus.CANCELLED, f"任务状态应为CANCELLED，实际为{task_info.status}"
        print(f"✅ 任务取消正常: {task_info.status}")
        
        # 8. 测试任务清理
        task_manager.cleanup_task(task_id)
        task_info = task_manager.get_task_info(task_id)
        assert task_info is None, "任务清理后应该无法查询到任务信息"
        print(f"✅ 任务清理正常")
        
        print("\n🎉 端到端测试全部通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理测试数据
        try:
            CompositionTask.objects.filter(task_id__startswith='test').delete()
            Video.objects.filter(title__startswith='测试视频').delete()
            User.objects.filter(username__startswith='testuser').delete()
            print("🧹 清理测试数据完成")
        except Exception as e:
            print(f"⚠️ 清理数据时出错: {str(e)}")


def test_response_time():
    """测试响应时间要求"""
    print("\n⏱️ 测试响应时间要求...")
    
    try:
        # 创建测试用户
        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'perfuser_{unique_id}',
            email=f'perf_{unique_id}@example.com',
            password='testpass123',
            role='user'
        )
        
        # 创建测试视频
        from datetime import timedelta
        
        video1 = Video.objects.create(
            title='性能测试视频1',
            uploader=user,
            file_path='perf_test_1.mp4',
            file_size=1024000,
            duration=timedelta(seconds=30)
        )
        
        video2 = Video.objects.create(
            title='性能测试视频2',
            uploader=user,
            file_path='perf_test_2.mp4',
            file_size=1024000,
            duration=timedelta(seconds=30)
        )
        
        # 测试任务注册响应时间
        start_time = time.time()
        task_id = task_manager.register_task(
            user_id=user.id,
            video_ids=[video1.id, video2.id]
        )
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # 验证响应时间 < 500ms
        assert response_time_ms < 500, f"响应时间 {response_time_ms:.2f}ms 超过500ms要求"
        print(f"✅ 响应时间测试通过: {response_time_ms:.2f}ms < 500ms")
        
        return True
        
    except Exception as e:
        print(f"❌ 响应时间测试失败: {str(e)}")
        return False
        
    finally:
        # 清理测试数据
        try:
            Video.objects.filter(title__startswith='性能测试视频').delete()
            User.objects.filter(username__startswith='perfuser').delete()
        except:
            pass


if __name__ == '__main__':
    print("=" * 60)
    print("异步视频合成端到端测试")
    print("=" * 60)
    
    success1 = test_async_composition_e2e()
    success2 = test_response_time()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有端到端测试通过！异步视频合成功能正常工作。")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查问题。")
        sys.exit(1)