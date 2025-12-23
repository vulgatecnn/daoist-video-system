#!/usr/bin/env python
"""
测试视频合成功能
验证FFmpeg和MoviePy是否正确安装和配置
"""
import os
import sys
import django
from pathlib import Path

# 添加项目路径到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import logging
from django.test import TestCase
from django.contrib.auth import get_user_model
from videos.models import Video, CompositionTask
from videos.tasks import compose_videos_task

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()


def test_ffmpeg_installation():
    """测试FFmpeg是否正确安装"""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ FFmpeg 已正确安装")
            logger.info(f"FFmpeg 版本信息: {result.stdout.split()[2]}")
            return True
        else:
            logger.error("❌ FFmpeg 未正确安装或配置")
            return False
    except FileNotFoundError:
        logger.error("❌ FFmpeg 未找到，请安装FFmpeg")
        logger.info("安装指南:")
        logger.info("Windows: 下载 https://ffmpeg.org/download.html 并添加到PATH")
        logger.info("macOS: brew install ffmpeg")
        logger.info("Ubuntu: sudo apt install ffmpeg")
        return False
    except Exception as e:
        logger.error(f"❌ 检查FFmpeg时出错: {str(e)}")
        return False


def test_moviepy_import():
    """测试MoviePy是否正确安装"""
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        logger.info("✅ MoviePy 已正确安装")
        return True
    except ImportError as e:
        logger.error(f"❌ MoviePy 导入失败: {str(e)}")
        logger.info("请运行: pip install moviepy")
        return False
    except Exception as e:
        logger.error(f"❌ MoviePy 测试失败: {str(e)}")
        return False


def test_cache_connection():
    """测试缓存连接"""
    try:
        from django.core.cache import cache
        
        # 测试缓存写入和读取
        test_key = 'test_cache_key'
        test_value = 'test_cache_value'
        
        cache.set(test_key, test_value, 60)
        retrieved_value = cache.get(test_key)
        
        if retrieved_value == test_value:
            logger.info("✅ 缓存连接正常 (本地内存缓存)")
            return True
        else:
            logger.error("❌ 缓存测试失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 缓存测试失败: {str(e)}")
        return False


def test_celery_configuration():
    """测试Celery配置"""
    try:
        from celery import current_app
        from videos.tasks import compose_videos_task
        
        # 检查任务是否注册
        if 'videos.tasks.compose_videos_task' in current_app.tasks:
            logger.info("✅ Celery 任务已正确注册")
            return True
        else:
            logger.error("❌ Celery 任务未注册")
            return False
            
    except Exception as e:
        logger.error(f"❌ Celery 配置测试失败: {str(e)}")
        return False


def create_test_video_files():
    """创建测试视频文件（如果不存在）"""
    try:
        from moviepy.editor import ColorClip
        
        # 创建测试目录
        test_dir = BASE_DIR / 'media' / 'test_videos'
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建两个简单的测试视频
        video_files = []
        for i in range(2):
            video_path = test_dir / f'test_video_{i+1}.mp4'
            if not video_path.exists():
                logger.info(f"创建测试视频: {video_path}")
                # 创建3秒的彩色视频
                color = ['red', 'blue'][i]
                clip = ColorClip(size=(640, 480), color=color, duration=3)
                clip.write_videofile(str(video_path), fps=24, verbose=False, logger=None)
                clip.close()
            video_files.append(str(video_path))
        
        logger.info("✅ 测试视频文件准备完成")
        return video_files
        
    except Exception as e:
        logger.error(f"❌ 创建测试视频失败: {str(e)}")
        return []


def test_video_composition():
    """测试视频合成功能"""
    try:
        video_files = create_test_video_files()
        if not video_files:
            return False
        
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        # 加载视频片段
        clips = []
        for video_file in video_files:
            clip = VideoFileClip(video_file)
            clips.append(clip)
        
        # 合成视频
        final_clip = concatenate_videoclips(clips)
        
        # 输出测试文件
        output_path = BASE_DIR / 'media' / 'test_videos' / 'test_composition.mp4'
        final_clip.write_videofile(str(output_path), verbose=False, logger=None)
        
        # 清理
        for clip in clips:
            clip.close()
        final_clip.close()
        
        # 检查输出文件
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info("✅ 视频合成测试成功")
            logger.info(f"输出文件: {output_path}")
            return True
        else:
            logger.error("❌ 视频合成测试失败：输出文件无效")
            return False
            
    except Exception as e:
        logger.error(f"❌ 视频合成测试失败: {str(e)}")
        return False


def main():
    """运行所有测试"""
    logger.info("🚀 开始测试视频合成环境...")
    logger.info("=" * 50)
    
    tests = [
        ("FFmpeg 安装", test_ffmpeg_installation),
        ("MoviePy 导入", test_moviepy_import),
        ("Redis 连接", test_cache_connection),
        ("Celery 配置", test_celery_configuration),
        ("视频合成功能", test_video_composition),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 测试: {test_name}")
        logger.info("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    # 汇总结果
    logger.info("\n" + "=" * 50)
    logger.info("📊 测试结果汇总:")
    logger.info("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n总计: {passed}/{len(tests)} 项测试通过")
    
    if passed == len(tests):
        logger.info("🎉 所有测试通过！视频合成环境配置正确。")
        return True
    else:
        logger.error("⚠️  部分测试失败，请检查上述错误信息并修复相关问题。")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)