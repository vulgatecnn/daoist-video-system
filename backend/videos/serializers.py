from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from .models import Video, CompositionTask, VideoSelection, PlaybackHistory
import os
import mimetypes


class VideoUploadSerializer(serializers.ModelSerializer):
    """视频上传序列化器"""
    
    class Meta:
        model = Video
        fields = ['title', 'description', 'category', 'file_path']
        
    def validate_file_path(self, value):
        """验证上传的视频文件"""
        if not isinstance(value, UploadedFile):
            raise serializers.ValidationError("必须上传一个有效的文件")
        
        # 检查文件大小 (限制为500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        if value.size > max_size:
            raise serializers.ValidationError(f"文件大小不能超过 {max_size // (1024*1024)}MB")
        
        # 检查文件扩展名
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 检查MIME类型
        mime_type, _ = mimetypes.guess_type(value.name)
        if mime_type and not mime_type.startswith('video/'):
            raise serializers.ValidationError("上传的文件不是有效的视频文件")
        
        # 如果无法从文件名推断MIME类型，检查content_type
        if hasattr(value, 'content_type') and value.content_type:
            if not value.content_type.startswith('video/'):
                raise serializers.ValidationError("上传的文件不是有效的视频文件")
        
        return value
    
    def validate_title(self, value):
        """验证标题"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("标题长度不能少于2个字符")
        return value.strip()
    
    def create(self, validated_data):
        """创建视频记录"""
        # 从请求上下文中获取用户
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['uploader'] = request.user
        
        # 设置文件大小
        if 'file_path' in validated_data:
            validated_data['file_size'] = validated_data['file_path'].size
        
        return super().create(validated_data)


class VideoSerializer(serializers.ModelSerializer):
    """视频详情序列化器"""
    uploader_name = serializers.CharField(source='uploader.username', read_only=True)
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'category', 'duration', 'file_size',
            'upload_time', 'view_count', 'is_active', 'width', 'height', 'fps', 'bitrate',
            'uploader_name', 'file_url', 'thumbnail_url', 'file_name', 'file_extension'
        ]
        read_only_fields = [
            'id', 'upload_time', 'view_count', 'file_size', 'duration',
            'width', 'height', 'fps', 'bitrate', 'uploader_name'
        ]
    
    def get_file_url(self, obj):
        """获取文件URL"""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
            return obj.file_path.url
        return None
    
    def get_thumbnail_url(self, obj):
        """获取缩略图URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_file_name(self, obj):
        """获取文件名"""
        return obj.get_file_name()
    
    def get_file_extension(self, obj):
        """获取文件扩展名"""
        return obj.get_file_extension()


class VideoListSerializer(serializers.ModelSerializer):
    """视频列表序列化器（简化版）"""
    uploader_name = serializers.CharField(source='uploader.username', read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'category', 'duration',
            'upload_time', 'view_count', 'uploader_name', 'thumbnail_url'
        ]
    
    def get_thumbnail_url(self, obj):
        """获取缩略图URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class PlaybackHistorySerializer(serializers.ModelSerializer):
    """播放历史序列化器"""
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = PlaybackHistory
        fields = [
            'id', 'video', 'video_title', 'video_thumbnail',
            'started_at', 'last_position', 'duration_watched',
            'completed', 'completion_percentage', 'updated_at'
        ]
        read_only_fields = ['user', 'started_at', 'updated_at']
    
    def get_video_thumbnail(self, obj):
        """获取视频缩略图URL"""
        if obj.video.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.video.thumbnail.url)
            return obj.video.thumbnail.url
        return None


class PlaybackProgressSerializer(serializers.Serializer):
    """播放进度更新序列化器"""
    current_time = serializers.FloatField(min_value=0)
    total_duration = serializers.FloatField(min_value=0)
    session_id = serializers.CharField(max_length=100, required=False)


class CompositionTaskSerializer(serializers.ModelSerializer):
    """合成任务序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    output_file_url = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CompositionTask
        fields = [
            'id', 'task_id', 'status', 'progress', 'output_filename',
            'total_duration', 'created_at', 'started_at', 'completed_at',
            'error_message', 'user_name', 'output_file_url', 'video_count'
        ]
        read_only_fields = [
            'id', 'task_id', 'status', 'progress', 'total_duration',
            'created_at', 'started_at', 'completed_at', 'error_message'
        ]
    
    def get_output_file_url(self, obj):
        """获取输出文件URL"""
        if obj.output_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.output_file.url)
            return obj.output_file.url
        return None
    
    def get_video_count(self, obj):
        """获取视频数量"""
        return obj.get_video_count()


class CompositionTaskCreateSerializer(serializers.Serializer):
    """创建合成任务序列化器"""
    video_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=20,
        help_text="要合成的视频ID列表"
    )
    output_filename = serializers.CharField(
        max_length=255,
        required=False,
        help_text="输出文件名（可选）"
    )
    
    def validate_video_ids(self, value):
        """验证视频ID列表"""
        # 检查是否有重复的ID
        if len(value) != len(set(value)):
            raise serializers.ValidationError("视频ID列表中不能有重复项")
        
        # 检查视频是否存在且激活
        existing_videos = Video.objects.filter(id__in=value, is_active=True)
        existing_ids = set(existing_videos.values_list('id', flat=True))
        missing_ids = set(value) - existing_ids
        
        if missing_ids:
            raise serializers.ValidationError(f"以下视频ID不存在或未激活: {list(missing_ids)}")
        
        return value
    
    def validate_output_filename(self, value):
        """验证输出文件名"""
        if value:
            # 移除不安全的字符
            import re
            safe_filename = re.sub(r'[^\w\-_\.]', '_', value)
            if not safe_filename.endswith('.mp4'):
                safe_filename += '.mp4'
            return safe_filename
        return None


class VideoSelectionSerializer(serializers.ModelSerializer):
    """视频选择序列化器"""
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_duration = serializers.DurationField(source='video.duration', read_only=True)
    
    class Meta:
        model = VideoSelection
        fields = ['id', 'video', 'order_index', 'video_title', 'video_duration']