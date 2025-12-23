from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import os

User = get_user_model()


class Video(models.Model):
    """视频模型"""
    
    # 视频分类选择
    CATEGORY_CHOICES = [
        ('daoist_classic', '道教经典'),
        ('meditation', '静心冥想'),
        ('ritual', '道教仪式'),
        ('teaching', '道法教学'),
        ('chanting', '经文诵读'),
        ('other', '其他'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="标题")
    description = models.TextField(blank=True, verbose_name="描述")
    file_path = models.FileField(
        upload_to='videos/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'mkv', 'webm'])],
        verbose_name="视频文件"
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="缩略图"
    )
    duration = models.DurationField(null=True, blank=True, verbose_name="时长")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="文件大小(字节)")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name="分类"
    )
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    uploader = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_videos',
        verbose_name="上传者"
    )
    view_count = models.IntegerField(default=0, verbose_name="观看次数")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    
    # 视频元数据
    width = models.IntegerField(null=True, blank=True, verbose_name="视频宽度")
    height = models.IntegerField(null=True, blank=True, verbose_name="视频高度")
    fps = models.FloatField(null=True, blank=True, verbose_name="帧率")
    bitrate = models.IntegerField(null=True, blank=True, verbose_name="比特率")
    
    class Meta:
        verbose_name = "视频"
        verbose_name_plural = "视频"
        ordering = ['-upload_time']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['uploader']),
            models.Index(fields=['upload_time']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_file_name(self):
        """获取文件名"""
        if self.file_path:
            return os.path.basename(self.file_path.name)
        return ""
    
    def get_file_extension(self):
        """获取文件扩展名"""
        if self.file_path:
            return os.path.splitext(self.file_path.name)[1].lower()
        return ""
    
    def increment_view_count(self):
        """增加观看次数"""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class PlaybackHistory(models.Model):
    """播放历史记录模型"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='playback_history',
        verbose_name="用户"
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='playback_records',
        verbose_name="视频"
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="开始播放时间")
    last_position = models.FloatField(default=0.0, verbose_name="最后播放位置(秒)")
    duration_watched = models.FloatField(default=0.0, verbose_name="观看时长(秒)")
    completed = models.BooleanField(default=False, verbose_name="是否看完")
    completion_percentage = models.FloatField(default=0.0, verbose_name="完成百分比")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 播放会话信息
    session_id = models.CharField(max_length=100, blank=True, verbose_name="会话ID")
    user_agent = models.TextField(blank=True, verbose_name="用户代理")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP地址")
    
    class Meta:
        verbose_name = "播放历史"
        verbose_name_plural = "播放历史"
        ordering = ['-started_at']
        unique_together = ['user', 'video', 'session_id']
        indexes = [
            models.Index(fields=['user', 'started_at']),
            models.Index(fields=['video', 'started_at']),
            models.Index(fields=['completed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.video.title} ({self.completion_percentage:.1f}%)"
    
    def update_progress(self, current_time, total_duration):
        """更新播放进度"""
        self.last_position = current_time
        if total_duration > 0:
            self.completion_percentage = min((current_time / total_duration) * 100, 100)
            # 如果播放超过90%认为是看完了
            if self.completion_percentage >= 90:
                self.completed = True
        self.save(update_fields=['last_position', 'completion_percentage', 'completed', 'updated_at'])
    
    def add_watch_time(self, seconds):
        """增加观看时长"""
        self.duration_watched += seconds
        self.save(update_fields=['duration_watched', 'updated_at'])


class CompositionTask(models.Model):
    """视频合成任务模型"""
    
    # 任务状态选择
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    task_id = models.CharField(max_length=100, unique=True, verbose_name="任务ID")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='composition_tasks',
        verbose_name="用户"
    )
    video_list = models.JSONField(verbose_name="视频列表")  # 存储视频ID和顺序信息
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="状态"
    )
    progress = models.IntegerField(default=0, verbose_name="进度百分比")
    output_file = models.FileField(
        upload_to='composed/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="输出文件"
    )
    output_filename = models.CharField(max_length=255, blank=True, verbose_name="输出文件名")
    total_duration = models.DurationField(null=True, blank=True, verbose_name="总时长")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    
    class Meta:
        verbose_name = "合成任务"
        verbose_name_plural = "合成任务"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"合成任务 {self.task_id} - {self.get_status_display()}"
    
    def get_video_count(self):
        """获取视频数量"""
        if isinstance(self.video_list, list):
            return len(self.video_list)
        return 0
    
    def is_completed(self):
        """检查任务是否完成"""
        return self.status == 'completed'
    
    def is_failed(self):
        """检查任务是否失败"""
        return self.status == 'failed'
    
    def can_download(self):
        """检查是否可以下载"""
        return self.is_completed() and self.output_file


class VideoSelection(models.Model):
    """视频选择关联模型（用于合成任务中的视频选择）"""
    
    task = models.ForeignKey(
        CompositionTask,
        on_delete=models.CASCADE,
        related_name='video_selections',
        verbose_name="合成任务"
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='selections',
        verbose_name="视频"
    )
    order_index = models.IntegerField(verbose_name="排序索引")
    
    class Meta:
        verbose_name = "视频选择"
        verbose_name_plural = "视频选择"
        ordering = ['order_index']
        unique_together = ['task', 'video']
        indexes = [
            models.Index(fields=['task', 'order_index']),
        ]
    
    def __str__(self):
        return f"{self.task.task_id} - {self.video.title} (#{self.order_index})"
