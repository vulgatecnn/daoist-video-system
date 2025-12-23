"""
视频管理相关的URL配置
"""
from django.urls import path
from . import views

app_name = 'videos'

urlpatterns = [
    # 视频上传
    path('upload/', views.VideoUploadView.as_view(), name='video-upload'),
    
    # 视频列表和详情
    path('', views.VideoListView.as_view(), name='video-list'),
    path('<int:pk>/', views.VideoDetailView.as_view(), name='video-detail'),
    
    # 视频分类
    path('categories/', views.video_categories, name='video-categories'),
    
    # 播放统计相关
    path('<int:video_id>/progress/', views.update_playback_progress, name='update-playback-progress'),
    path('<int:video_id>/progress/get/', views.get_video_progress, name='get-video-progress'),
    path('playback-history/', views.get_playback_history, name='get-playback-history'),
    
    # 管理员专用视频管理
    path('admin/list/', views.AdminVideoListView.as_view(), name='admin-video-list'),
    path('admin/<int:pk>/edit/', views.AdminVideoUpdateView.as_view(), name='admin-video-edit'),
    path('admin/batch-delete/', views.batch_delete_videos, name='admin-batch-delete'),
    path('admin/batch-category/', views.batch_update_category, name='admin-batch-category'),
    
    # 搜索和筛选
    path('search/', views.VideoSearchView.as_view(), name='video-search'),
    
    # 合成任务
    path('composition/create/', views.create_composition_task, name='create-composition-task'),
    path('composition/', views.composition_task_list, name='composition-task-list'),
    path('composition/<str:task_id>/', views.composition_task_detail, name='composition-task-detail'),
    path('composition/<str:task_id>/download/', views.download_composed_video, name='download-composed-video'),
    path('composition/<str:task_id>/stream/', views.stream_composed_video, name='stream-composed-video'),
    path('composition/<str:task_id>/cancel/', views.cancel_composition_task, name='cancel-composition-task'),
    
    # 系统监控
    path('admin/monitoring/statistics/', views.system_statistics, name='system-statistics'),
    path('admin/monitoring/storage/', views.storage_info, name='storage-info'),
    path('admin/monitoring/backup/create/', views.create_backup, name='create-backup'),
    path('admin/monitoring/backup/cleanup/', views.cleanup_backups, name='cleanup-backups'),
    path('admin/monitoring/check/', views.run_monitoring_check, name='run-monitoring-check'),
    
    # 性能监控
    path('admin/performance/statistics/', views.performance_statistics, name='performance-statistics'),
    path('admin/performance/slow-requests/', views.slow_requests, name='slow-requests'),
    path('admin/performance/alerts/', views.performance_alerts, name='performance-alerts'),
]