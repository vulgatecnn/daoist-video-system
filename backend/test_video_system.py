#!/usr/bin/env python
"""
视频系统功能测试脚本
"""
import os
import sys
import django
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from videos.models import Video, CompositionTask, VideoSelection
from videos.serializers import VideoUploadSerializer, CompositionTaskCreateSerializer

User = get_user_model()


def test_user_creation():
    """测试用户创建"""
    print("测试用户创建...")
    
    # 创建管理员用户
    admin_user, created = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'email': 'admin@test.com',
            'role': 'admin'
        }
    )
    if created:
        admin_user.set_password('testpass123')
        admin_user.save()
        print(f"✓ 创建管理员用户: {admin_user.username}")
    else:
        print(f"✓ 管理员用户已存在: {admin_user.username}")
    
    # 创建普通用户
    regular_user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'user@test.com',
            'role': 'user'
        }
    )
    if created:
        regular_user.set_password('testpass123')
        regular_user.save()
        print(f"✓ 创建普通用户: {regular_user.username}")
    else:
        print(f"✓ 普通用户已存在: {regular_user.username}")
    
    return admin_user, regular_user


def test_video_model():
    """测试视频模型"""
    print("\n测试视频模型...")
    
    admin_user, _ = User.objects.get_or_create(
        username='test_admin',
        defaults={'email': 'admin@test.com', 'role': 'admin'}
    )
    
    # 创建测试视频
    video = Video.objects.create(
        title='道德经诵读',
        description='老子道德经第一章诵读',
        category='daoist_classic',
        uploader=admin_user
    )
    
    print(f"✓ 创建视频: {video.title}")
    print(f"  - ID: {video.id}")
    print(f"  - 分类: {video.get_category_display()}")
    print(f"  - 上传者: {video.uploader.username}")
    print(f"  - 观看次数: {video.view_count}")
    
    # 测试增加观看次数
    video.increment_view_count()
    print(f"  - 增加观看次数后: {video.view_count}")
    
    return video


def test_composition_task():
    """测试合成任务"""
    print("\n测试合成任务...")
    
    # 获取用户
    user, _ = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'user@test.com', 'role': 'user'}
    )
    
    # 创建多个测试视频
    admin_user, _ = User.objects.get_or_create(
        username='test_admin',
        defaults={'email': 'admin@test.com', 'role': 'admin'}
    )
    
    video1 = Video.objects.create(
        title='道德经第一章',
        category='daoist_classic',
        uploader=admin_user
    )
    
    video2 = Video.objects.create(
        title='道德经第二章',
        category='daoist_classic',
        uploader=admin_user
    )
    
    # 清理可能存在的旧任务
    CompositionTask.objects.filter(task_id='test_comp_123').delete()
    
    # 创建合成任务
    task = CompositionTask.objects.create(
        task_id='test_comp_123',
        user=user,
        video_list=[video1.id, video2.id],
        output_filename='道德经合集.mp4'
    )
    
    print(f"✓ 创建合成任务: {task.task_id}")
    print(f"  - 用户: {task.user.username}")
    print(f"  - 视频数量: {task.get_video_count()}")
    print(f"  - 状态: {task.get_status_display()}")
    print(f"  - 输出文件名: {task.output_filename}")
    
    # 创建视频选择记录
    VideoSelection.objects.create(
        task=task,
        video=video1,
        order_index=0
    )
    
    VideoSelection.objects.create(
        task=task,
        video=video2,
        order_index=1
    )
    
    print(f"✓ 创建视频选择记录: {task.video_selections.count()} 个")
    
    return task


def test_serializers():
    """测试序列化器"""
    print("\n测试序列化器...")
    
    # 测试合成任务创建序列化器
    admin_user, _ = User.objects.get_or_create(
        username='test_admin',
        defaults={'email': 'admin@test.com', 'role': 'admin'}
    )
    
    # 创建测试视频
    video1 = Video.objects.create(
        title='测试视频1',
        uploader=admin_user
    )
    video2 = Video.objects.create(
        title='测试视频2',
        uploader=admin_user
    )
    
    # 测试序列化器验证
    serializer = CompositionTaskCreateSerializer(data={
        'video_ids': [video1.id, video2.id],
        'output_filename': '测试合成.mp4'
    })
    
    if serializer.is_valid():
        print("✓ 合成任务序列化器验证通过")
        print(f"  - 视频IDs: {serializer.validated_data['video_ids']}")
        print(f"  - 输出文件名: {serializer.validated_data['output_filename']}")
    else:
        print("✗ 合成任务序列化器验证失败")
        print(f"  - 错误: {serializer.errors}")


def test_database_queries():
    """测试数据库查询"""
    print("\n测试数据库查询...")
    
    # 统计数据
    total_videos = Video.objects.count()
    active_videos = Video.objects.filter(is_active=True).count()
    total_tasks = CompositionTask.objects.count()
    
    print(f"✓ 数据库统计:")
    print(f"  - 总视频数: {total_videos}")
    print(f"  - 激活视频数: {active_videos}")
    print(f"  - 合成任务数: {total_tasks}")
    
    # 测试查询
    if total_videos > 0:
        latest_video = Video.objects.order_by('-upload_time').first()
        print(f"  - 最新视频: {latest_video.title}")
        
        # 测试分类查询
        classic_videos = Video.objects.filter(category='daoist_classic').count()
        print(f"  - 道教经典视频数: {classic_videos}")


def main():
    """主函数"""
    print("道士经文视频管理系统 - 功能测试")
    print("=" * 50)
    
    try:
        # 运行测试
        test_user_creation()
        test_video_model()
        test_composition_task()
        test_serializers()
        test_database_queries()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试完成！系统基本功能正常。")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())