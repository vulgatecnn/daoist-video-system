#!/usr/bin/env python
"""
测试视频合成API功能
"""
import os
import sys
import django
from pathlib import Path
import uuid

# 添加项目路径到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from videos.models import Video, CompositionTask
from videos.tasks import compose_videos_task

User = get_user_model()


def test_composition_api():
    """测试视频合成API"""
    print("🧪 测试视频合成API...")
    
    # 清理现有数据
    User.objects.filter(username__startswith='testuser').delete()
    User.objects.filter(username__startswith='admin').delete()
    
    # 生成唯一用户名
    unique_id = str(uuid.uuid4())[:8]
    
    # 创建测试用户
    user = User.objects.create_user(
        username=f'testuser_{unique_id}',
        email=f'test_{unique_id}@example.com',
        password='testpass123',
        role='user'
    )
    
    admin_user = User.objects.create_user(
        username=f'admin_{unique_id}',
        email=f'admin_{unique_id}@example.com',
        password='adminpass123',
        role='admin'
    )
    
    # 创建测试视频
    video1 = Video.objects.create(
        title='测试视频1',
        description='第一个测试视频',
        category='daoist_classic',
        uploader=admin_user,
        file_size=1024000
    )
    
    video2 = Video.objects.create(
        title='测试视频2',
        description='第二个测试视频',
        category='daoist_classic',
        uploader=admin_user,
        file_size=2048000
    )
    
    print(f"✅ 创建测试数据: 用户 {user.username}, 视频 {video1.title}, {video2.title}")
    
    # 测试API客户端
    client = Client()
    
    # 登录用户
    login_response = client.post('/api/auth/login/', {
        'username': f'testuser_{unique_id}',
        'password': 'testpass123'
    })
    
    if login_response.status_code == 200:
        print("✅ 用户登录成功")
        # 获取JWT令牌
        token_data = json.loads(login_response.content)
        access_token = token_data.get('access')
        
        # 设置认证头
        auth_header = f'Bearer {access_token}'
        
        # 测试创建合成任务
        composition_data = {
            'video_ids': [video1.id, video2.id],
            'output_filename': '测试合成视频.mp4'
        }
        
        response = client.post(
            '/api/videos/composition/create/',
            data=json.dumps(composition_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth_header
        )
        
        if response.status_code == 201:
            print("✅ 合成任务创建成功")
            task_data = json.loads(response.content)
            task_id = task_data['data']['task_id']
            print(f"   任务ID: {task_id}")
            
            # 检查任务状态
            status_response = client.get(
                f'/api/videos/composition/{task_id}/',
                HTTP_AUTHORIZATION=auth_header
            )
            
            if status_response.status_code == 200:
                print("✅ 任务状态查询成功")
                status_data = json.loads(status_response.content)
                print(f"   任务状态: {status_data['status']}")
                print(f"   进度: {status_data['progress']}%")
                
                # 如果任务完成，测试下载
                if status_data['status'] == 'completed':
                    download_response = client.get(
                        f'/api/videos/composition/{task_id}/download/',
                        HTTP_AUTHORIZATION=auth_header
                    )
                    
                    if download_response.status_code == 200:
                        print("✅ 文件下载成功")
                        print(f"   文件大小: {len(download_response.content)} 字节")
                    else:
                        print(f"❌ 文件下载失败: {download_response.status_code}")
                
            else:
                print(f"❌ 任务状态查询失败: {status_response.status_code}")
                
        else:
            print(f"❌ 合成任务创建失败: {response.status_code}")
            print(f"   响应内容: {response.content.decode()}")
            
    else:
        print(f"❌ 用户登录失败: {login_response.status_code}")
        print(f"   响应内容: {login_response.content.decode()}")
    
    # 清理测试数据
    CompositionTask.objects.all().delete()
    Video.objects.all().delete()
    User.objects.all().delete()
    
    print("🧹 清理测试数据完成")


def test_celery_task():
    """测试Celery任务"""
    print("\n🔧 测试Celery任务...")
    
    # 清理现有数据
    User.objects.filter(username__startswith='testuser2').delete()
    User.objects.filter(username__startswith='admin2').delete()
    
    # 生成唯一用户名
    unique_id = str(uuid.uuid4())[:8]
    
    # 创建测试用户和视频
    user = User.objects.create_user(
        username=f'testuser2_{unique_id}',
        email=f'test2_{unique_id}@example.com',
        password='testpass123',
        role='user'
    )
    
    admin_user = User.objects.create_user(
        username=f'admin2_{unique_id}',
        email=f'admin2_{unique_id}@example.com',
        password='adminpass123',
        role='admin'
    )
    
    video1 = Video.objects.create(
        title='Celery测试视频1',
        description='第一个Celery测试视频',
        category='daoist_classic',
        uploader=admin_user,
        file_size=1024000
    )
    
    video2 = Video.objects.create(
        title='Celery测试视频2',
        description='第二个Celery测试视频',
        category='daoist_classic',
        uploader=admin_user,
        file_size=2048000
    )
    
    # 创建合成任务
    task = CompositionTask.objects.create(
        task_id='test_task_123',
        user=user,
        video_list=[video1.id, video2.id],
        output_filename='celery_test.mp4'
    )
    
    print(f"✅ 创建测试任务: {task.task_id}")
    
    # 执行Celery任务
    try:
        result = compose_videos_task(task.task_id)
        print(f"✅ Celery任务执行完成")
        print(f"   结果: {result}")
        
        # 检查任务状态
        task.refresh_from_db()
        print(f"   最终状态: {task.status}")
        print(f"   进度: {task.progress}%")
        
        if task.output_file:
            print(f"   输出文件: {task.output_file.name}")
        
    except Exception as e:
        print(f"❌ Celery任务执行失败: {str(e)}")
    
    # 清理测试数据
    CompositionTask.objects.all().delete()
    Video.objects.all().delete()
    User.objects.all().delete()
    
    print("🧹 清理测试数据完成")


def main():
    """运行所有测试"""
    print("🚀 开始测试视频合成功能...")
    print("=" * 50)
    
    try:
        test_composition_api()
        test_celery_task()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)