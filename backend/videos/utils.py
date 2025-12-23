"""
视频处理工具函数
"""
import os
import subprocess
import json
import logging
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image

logger = logging.getLogger(__name__)


class VideoProcessor:
    """视频处理器"""
    
    @staticmethod
    def get_video_metadata(video_path):
        """
        获取视频元数据
        
        Args:
            video_path (str): 视频文件路径
            
        Returns:
            dict: 包含视频元数据的字典，如果失败返回None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(video_path):
                logger.error(f"视频文件不存在: {video_path}")
                return None
            
            # 使用ffprobe获取视频信息
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"ffprobe执行失败: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # 查找视频流
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                logger.error("未找到视频流")
                return None
            
            format_info = data.get('format', {})
            
            # 计算帧率
            fps = 0
            r_frame_rate = video_stream.get('r_frame_rate', '0/1')
            if '/' in r_frame_rate:
                try:
                    num, den = map(int, r_frame_rate.split('/'))
                    if den != 0:
                        fps = num / den
                except (ValueError, ZeroDivisionError):
                    fps = 0
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': fps,
                'bitrate': int(format_info.get('bit_rate', 0))
            }
            
        except subprocess.TimeoutExpired:
            logger.error("ffprobe执行超时")
        except json.JSONDecodeError as e:
            logger.error(f"解析ffprobe输出失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取视频元数据失败: {str(e)}")
        
        return None
    
    @staticmethod
    def generate_thumbnail(video_path, output_path=None, timestamp='00:00:01.000'):
        """
        生成视频缩略图
        
        Args:
            video_path (str): 视频文件路径
            output_path (str): 输出路径，如果为None则生成临时路径
            timestamp (str): 截取时间点，默认为第1秒
            
        Returns:
            str: 缩略图文件路径，如果失败返回None
        """
        try:
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                logger.error(f"视频文件不存在: {video_path}")
                return None
            
            # 生成输出路径
            if output_path is None:
                output_path = f"/tmp/thumbnail_{uuid.uuid4().hex}.jpg"
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 使用ffmpeg生成缩略图
            cmd = [
                'ffmpeg', '-i', video_path, 
                '-ss', timestamp,
                '-vframes', '1',
                '-vf', 'scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2',
                '-y', output_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                timeout=30,
                check=False
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                logger.error(f"ffmpeg生成缩略图失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg执行超时")
        except Exception as e:
            logger.error(f"生成缩略图失败: {str(e)}")
        
        return None
    
    @staticmethod
    def validate_video_file(file_path):
        """
        验证视频文件是否有效
        
        Args:
            file_path (str): 视频文件路径
            
        Returns:
            bool: 文件是否有效
        """
        try:
            metadata = VideoProcessor.get_video_metadata(file_path)
            return metadata is not None and metadata.get('duration', 0) > 0
        except Exception as e:
            logger.error(f"验证视频文件失败: {str(e)}")
            return False


class FileValidator:
    """文件验证器"""
    
    # 支持的视频格式
    SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    SUPPORTED_VIDEO_MIMETYPES = [
        'video/mp4', 'video/avi', 'video/quicktime', 
        'video/x-msvideo', 'video/webm', 'video/x-matroska'
    ]
    
    # 文件大小限制 (500MB)
    MAX_FILE_SIZE = 500 * 1024 * 1024
    
    @classmethod
    def validate_video_extension(cls, filename):
        """
        验证视频文件扩展名
        
        Args:
            filename (str): 文件名
            
        Returns:
            bool: 扩展名是否有效
        """
        if not filename:
            return False
        
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.SUPPORTED_VIDEO_EXTENSIONS
    
    @classmethod
    def validate_file_size(cls, file_size):
        """
        验证文件大小
        
        Args:
            file_size (int): 文件大小（字节）
            
        Returns:
            bool: 文件大小是否有效
        """
        return 0 < file_size <= cls.MAX_FILE_SIZE
    
    @classmethod
    def get_file_size_mb(cls, file_size):
        """
        将文件大小转换为MB
        
        Args:
            file_size (int): 文件大小（字节）
            
        Returns:
            float: 文件大小（MB）
        """
        return file_size / (1024 * 1024)


def process_uploaded_video(video_instance):
    """
    处理上传的视频文件
    
    Args:
        video_instance: Video模型实例
        
    Returns:
        bool: 处理是否成功
    """
    try:
        video_path = video_instance.file_path.path
        
        # 获取视频元数据
        metadata = VideoProcessor.get_video_metadata(video_path)
        if metadata:
            video_instance.duration = timedelta(seconds=metadata.get('duration', 0))
            video_instance.width = metadata.get('width')
            video_instance.height = metadata.get('height')
            video_instance.fps = metadata.get('fps')
            video_instance.bitrate = metadata.get('bitrate')
        
        # 生成缩略图
        thumbnail_path = VideoProcessor.generate_thumbnail(video_path)
        if thumbnail_path:
            try:
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_name = f"thumbnail_{video_instance.id}.jpg"
                    video_instance.thumbnail.save(
                        thumbnail_name, 
                        ContentFile(f.read()), 
                        save=False
                    )
            finally:
                # 清理临时文件
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
        
        # 保存更新
        video_instance.save(update_fields=[
            'duration', 'width', 'height', 'fps', 'bitrate', 'thumbnail'
        ])
        
        logger.info(f"视频 {video_instance.id} 处理完成")
        return True
        
    except Exception as e:
        logger.error(f"处理视频 {video_instance.id} 失败: {str(e)}")
        return False