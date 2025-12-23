"""
添加示例视频数据脚本
"""
import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from videos.models import Video
from datetime import timedelta

User = get_user_model()

def add_sample_videos():
    """添加示例视频"""
    # 获取或创建管理员用户
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    if not admin_user:
        print("错误：没有找到用户，请先创建用户")
        return
    
    # 视频数据
    videos_data = [
        {
            'title': '后土',
            'description': '道教后土皇地祇经文视频，讲述后土娘娘的神圣故事与祭祀仪式。',
            'file_path': 'videos/2025/12/22/后土.mp4',
            'category': 'daoist_classic',
            'duration': timedelta(minutes=5, seconds=30),
            'file_size': os.path.getsize('media/videos/2025/12/22/后土.mp4') if os.path.exists('media/videos/2025/12/22/后土.mp4') else 0,
        },
        {
            'title': '龙虎山',
            'description': '龙虎山道教圣地纪录片，展示道教发源地的壮丽风光与深厚文化底蕴。',
            'file_path': 'videos/2025/12/22/龙虎山.mp4',
            'category': 'ritual',
            'duration': timedelta(minutes=8, seconds=15),
            'file_size': os.path.getsize('media/videos/2025/12/22/龙虎山.mp4') if os.path.exists('media/videos/2025/12/22/龙虎山.mp4') else 0,
        },
    ]
    
    created_count = 0
    for video_data in videos_data:
        # 检查是否已存在
        if Video.objects.filter(title=video_data['title']).exists():
            print(f"视频 '{video_data['title']}' 已存在，跳过")
            continue
        
        video = Video.objects.create(
            title=video_data['title'],
            description=video_data['description'],
            file_path=video_data['file_path'],
            category=video_data['category'],
            duration=video_data['duration'],
            file_size=video_data['file_size'],
            uploader=admin_user,
            is_active=True,
            view_count=0,
        )
        print(f"✅ 创建视频: {video.title}")
        created_count += 1
    
    print(f"\n完成！共创建 {created_count} 个视频")

if __name__ == '__main__':
    add_sample_videos()
