from django.contrib import admin
from .models import Video, CompositionTask, VideoSelection


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """视频管理"""
    list_display = ['title', 'category', 'uploader', 'duration', 'file_size', 'view_count', 'upload_time', 'is_active']
    list_filter = ['category', 'is_active', 'upload_time', 'uploader']
    search_fields = ['title', 'description']
    readonly_fields = ['upload_time', 'view_count', 'file_size', 'duration', 'width', 'height', 'fps', 'bitrate']
    list_per_page = 20
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description', 'category', 'is_active')
        }),
        ('文件信息', {
            'fields': ('file_path', 'thumbnail', 'file_size', 'duration')
        }),
        ('视频元数据', {
            'fields': ('width', 'height', 'fps', 'bitrate'),
            'classes': ('collapse',)
        }),
        ('统计信息', {
            'fields': ('uploader', 'upload_time', 'view_count'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('uploader')


@admin.register(CompositionTask)
class CompositionTaskAdmin(admin.ModelAdmin):
    """合成任务管理"""
    list_display = ['task_id', 'user', 'status', 'progress', 'get_video_count', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at', 'completed_at']
    search_fields = ['task_id', 'user__username']
    readonly_fields = ['task_id', 'created_at', 'started_at', 'completed_at', 'total_duration']
    list_per_page = 20
    
    fieldsets = (
        ('任务信息', {
            'fields': ('task_id', 'user', 'status', 'progress')
        }),
        ('视频信息', {
            'fields': ('video_list', 'total_duration')
        }),
        ('输出信息', {
            'fields': ('output_file', 'output_filename')
        }),
        ('时间信息', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
        ('错误信息', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(VideoSelection)
class VideoSelectionAdmin(admin.ModelAdmin):
    """视频选择管理"""
    list_display = ['task', 'video', 'order_index']
    list_filter = ['task__status']
    search_fields = ['task__task_id', 'video__title']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'video')
