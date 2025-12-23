from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.core.files.base import ContentFile
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import os
import logging
import uuid
from datetime import timedelta

from .models import Video, CompositionTask, VideoSelection, PlaybackHistory
from .serializers import (
    VideoUploadSerializer, VideoSerializer, VideoListSerializer,
    CompositionTaskSerializer, CompositionTaskCreateSerializer,
    PlaybackHistorySerializer, PlaybackProgressSerializer
)
from .utils import process_uploaded_video
from users.permissions import IsAdmin

logger = logging.getLogger(__name__)


class VideoUploadView(generics.CreateAPIView):
    """视频上传视图"""
    serializer_class = VideoUploadSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        """执行创建操作"""
        video = serializer.save()
        
        # 异步处理视频元数据提取和缩略图生成
        try:
            process_uploaded_video(video)
        except Exception as e:
            logger.error(f"处理视频元数据失败: {str(e)}")
            # 即使处理失败，也不影响视频上传成功
    
    def create(self, request, *args, **kwargs):
        """创建视频记录"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                {
                    'message': '视频上传成功',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except Exception as e:
            logger.error(f"视频上传失败: {str(e)}")
            return Response(
                {'error': '视频上传失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoListView(generics.ListAPIView):
    """视频列表视图"""
    serializer_class = VideoListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['upload_time', 'view_count', 'title']
    ordering = ['-upload_time']
    
    def get_queryset(self):
        """获取查询集"""
        queryset = Video.objects.filter(is_active=True).select_related('uploader')
        
        # 搜索功能
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # 分类筛选
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 上传者筛选（管理员功能）
        uploader = self.request.query_params.get('uploader')
        if uploader and self.request.user.is_admin():
            queryset = queryset.filter(uploader__username=uploader)
        
        return queryset


class VideoSearchView(generics.ListAPIView):
    """视频搜索视图"""
    serializer_class = VideoListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取搜索结果"""
        queryset = Video.objects.filter(is_active=True).select_related('uploader')
        
        # 获取搜索参数
        query = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category')
        uploader_id = self.request.query_params.get('uploader_id')
        
        # 应用搜索条件
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
        
        if category:
            queryset = queryset.filter(category=category)
        
        if uploader_id:
            queryset = queryset.filter(uploader_id=uploader_id)
        
        return queryset.order_by('-upload_time')


class AdminVideoListView(generics.ListAPIView):
    """管理员视频列表视图"""
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['upload_time', 'view_count', 'title', 'file_size']
    ordering = ['-upload_time']
    
    def get_queryset(self):
        """获取所有视频（包括已删除的）"""
        queryset = Video.objects.all().select_related('uploader')
        
        # 状态筛选
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # 搜索功能
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(uploader__username__icontains=search)
            )
        
        # 分类筛选
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset


class AdminVideoUpdateView(generics.RetrieveUpdateAPIView):
    """管理员视频编辑视图"""
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = Video.objects.all()
    
    def update(self, request, *args, **kwargs):
        """更新视频信息"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'message': '视频信息更新成功',
            'data': serializer.data
        })


class VideoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """视频详情视图"""
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集"""
        return Video.objects.filter(is_active=True).select_related('uploader')
    
    def get_permissions(self):
        """获取权限"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # 只有管理员可以编辑和删除
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]
    
    def retrieve(self, request, *args, **kwargs):
        """获取视频详情时增加观看次数"""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_destroy(self, instance):
        """软删除视频"""
        instance.is_active = False
        instance.save(update_fields=['is_active'])


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_playback_progress(request, video_id):
    """更新播放进度"""
    try:
        video = Video.objects.get(id=video_id, is_active=True)
    except Video.DoesNotExist:
        return Response(
            {'error': '视频不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = PlaybackProgressSerializer(data=request.data)
    if serializer.is_valid():
        current_time = serializer.validated_data['current_time']
        total_duration = serializer.validated_data['total_duration']
        session_id = serializer.validated_data.get('session_id', '')
        
        # 获取或创建播放历史记录
        playback_history, created = PlaybackHistory.objects.get_or_create(
            user=request.user,
            video=video,
            session_id=session_id,
            defaults={
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': request.META.get('REMOTE_ADDR'),
            }
        )
        
        # 更新播放进度
        playback_history.update_progress(current_time, total_duration)
        
        return Response({
            'message': '播放进度已更新',
            'completion_percentage': playback_history.completion_percentage,
            'completed': playback_history.completed
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_playback_history(request):
    """获取用户播放历史"""
    # 获取查询参数
    video_id = request.query_params.get('video_id')
    limit = int(request.query_params.get('limit', 20))
    
    queryset = PlaybackHistory.objects.filter(user=request.user).select_related('video')
    
    if video_id:
        queryset = queryset.filter(video_id=video_id)
    
    # 按最后更新时间排序，限制数量
    history = queryset.order_by('-updated_at')[:limit]
    
    serializer = PlaybackHistorySerializer(history, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_video_progress(request, video_id):
    """获取特定视频的播放进度"""
    try:
        video = Video.objects.get(id=video_id, is_active=True)
    except Video.DoesNotExist:
        return Response(
            {'error': '视频不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    session_id = request.query_params.get('session_id', '')
    
    try:
        playback_history = PlaybackHistory.objects.get(
            user=request.user,
            video=video,
            session_id=session_id
        )
        
        return Response({
            'last_position': playback_history.last_position,
            'completion_percentage': playback_history.completion_percentage,
            'completed': playback_history.completed,
            'duration_watched': playback_history.duration_watched
        })
    except PlaybackHistory.DoesNotExist:
        return Response({
            'last_position': 0,
            'completion_percentage': 0,
            'completed': False,
            'duration_watched': 0
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def video_categories(request):
    """获取视频分类列表"""
    categories = [
        {'value': choice[0], 'label': choice[1]}
        for choice in Video.CATEGORY_CHOICES
    ]
    return Response(categories)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def batch_delete_videos(request):
    """批量删除视频"""
    video_ids = request.data.get('video_ids', [])
    
    if not video_ids:
        return Response(
            {'error': '请选择要删除的视频'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            # 软删除视频
            updated_count = Video.objects.filter(
                id__in=video_ids,
                is_active=True
            ).update(is_active=False)
            
            return Response({
                'message': f'成功删除 {updated_count} 个视频',
                'deleted_count': updated_count
            })
    
    except Exception as e:
        logger.error(f"批量删除视频失败: {str(e)}")
        return Response(
            {'error': '删除失败，请稍后重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def batch_update_category(request):
    """批量更新视频分类"""
    video_ids = request.data.get('video_ids', [])
    new_category = request.data.get('category')
    
    if not video_ids:
        return Response(
            {'error': '请选择要更新的视频'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not new_category:
        return Response(
            {'error': '请选择新的分类'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 验证分类是否有效
    valid_categories = [choice[0] for choice in Video.CATEGORY_CHOICES]
    if new_category not in valid_categories:
        return Response(
            {'error': '无效的分类'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            updated_count = Video.objects.filter(
                id__in=video_ids,
                is_active=True
            ).update(category=new_category)
            
            return Response({
                'message': f'成功更新 {updated_count} 个视频的分类',
                'updated_count': updated_count
            })
    
    except Exception as e:
        logger.error(f"批量更新分类失败: {str(e)}")
        return Response(
            {'error': '更新失败，请稍后重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_composition_task(request):
    """创建视频合成任务 - 异步执行，快速返回"""
    import time
    start_time = time.time()
    
    serializer = CompositionTaskCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        video_ids = serializer.validated_data['video_ids']
        output_filename = serializer.validated_data.get('output_filename')
        
        # 验证视频数量（至少2个）
        if len(video_ids) < 2:
            return Response(
                {'error': '至少需要选择两个视频进行合成'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证视频是否存在且用户有权限访问
        videos = Video.objects.filter(id__in=video_ids, is_active=True)
        if len(videos) != len(video_ids):
            return Response(
                {'error': '部分视频不存在或已被删除'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 使用 TaskManager 注册任务并生成唯一任务ID
            from .task_manager import task_manager
            task_id = task_manager.register_task(
                user_id=request.user.id,
                video_ids=video_ids
            )
            
            with transaction.atomic():
                # 创建数据库记录
                task = CompositionTask.objects.create(
                    task_id=task_id,
                    user=request.user,
                    video_list=video_ids,
                    output_filename=output_filename or f"合成视频_{task_id[:8]}.mp4",
                    status='pending'
                )
                
                # 创建视频选择记录
                video_selections = []
                for index, video_id in enumerate(video_ids):
                    video_selections.append(
                        VideoSelection(
                            task=task,
                            video_id=video_id,
                            order_index=index
                        )
                    )
                VideoSelection.objects.bulk_create(video_selections)
                
                # 启动异步合成任务
                from .tasks import run_composition_in_thread
                success = task_manager.start_task(task_id, run_composition_in_thread)
                
                if not success:
                    # 如果启动失败，更新任务状态
                    task.status = 'failed'
                    task.error_message = '启动合成任务失败'
                    task.save()
                    return Response(
                        {'error': '启动合成任务失败，请稍后重试'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                # 计算响应时间
                response_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                logger.info(f"创建视频合成任务: {task_id}, 用户: {request.user.username}, 响应时间: {response_time:.2f}ms")
                
                # 返回任务信息
                return Response(
                    {
                        'message': '合成任务创建成功，正在后台处理',
                        'task_id': task_id,
                        'status': 'pending',
                        'progress': 0,
                        'created_at': task.created_at.isoformat(),
                        'response_time_ms': round(response_time, 2)
                    },
                    status=status.HTTP_201_CREATED
                )
        
        except Exception as e:
            logger.error(f"创建合成任务失败: {str(e)}")
            return Response(
                {'error': '创建任务失败，请稍后重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def composition_task_list(request):
    """获取用户的合成任务列表"""
    tasks = CompositionTask.objects.filter(user=request.user).order_by('-created_at')
    serializer = CompositionTaskSerializer(tasks, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def composition_task_detail(request, task_id):
    """获取合成任务详情 - 返回完整的进度信息"""
    try:
        # 从数据库获取任务基本信息
        task = CompositionTask.objects.get(task_id=task_id, user=request.user)
        
        # 从 TaskManager 获取实时进度信息
        from .task_manager import task_manager
        progress_info = task_manager.get_progress_info(task_id)
        task_info = task_manager.get_task_info(task_id)
        
        # 构建响应数据
        response_data = {
            'task_id': task_id,
            'status': task.status,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'output_filename': task.output_filename,
            'error_message': task.error_message,
            'video_list': task.video_list
        }
        
        # 如果 TaskManager 中有更新的信息，使用实时数据
        if progress_info:
            response_data.update({
                'status': progress_info.status,
                'progress': progress_info.progress,
                'started_at': progress_info.started_at.isoformat() if progress_info.started_at else response_data['started_at'],
                'completed_at': progress_info.completed_at.isoformat() if progress_info.completed_at else response_data['completed_at'],
                'error_message': progress_info.error_message or response_data['error_message']
            })
            
            # 添加当前处理阶段描述
            if progress_info.current_stage:
                response_data['current_stage'] = progress_info.current_stage
            
            # 添加预计剩余时间
            if progress_info.estimated_time_remaining is not None:
                response_data['estimated_time_remaining'] = progress_info.estimated_time_remaining
                # 格式化为易读的时间字符串
                remaining_seconds = progress_info.estimated_time_remaining
                if remaining_seconds < 60:
                    response_data['estimated_time_remaining_formatted'] = f"{remaining_seconds}秒"
                elif remaining_seconds < 3600:
                    minutes = remaining_seconds // 60
                    seconds = remaining_seconds % 60
                    response_data['estimated_time_remaining_formatted'] = f"{minutes}分{seconds}秒"
                else:
                    hours = remaining_seconds // 3600
                    minutes = (remaining_seconds % 3600) // 60
                    response_data['estimated_time_remaining_formatted'] = f"{hours}小时{minutes}分"
            else:
                # 如果进度信息中没有，尝试计算
                estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
                if estimated_time is not None:
                    response_data['estimated_time_remaining'] = estimated_time
                    # 格式化为易读的时间字符串
                    if estimated_time < 60:
                        response_data['estimated_time_remaining_formatted'] = f"{estimated_time}秒"
                    elif estimated_time < 3600:
                        minutes = estimated_time // 60
                        seconds = estimated_time % 60
                        response_data['estimated_time_remaining_formatted'] = f"{minutes}分{seconds}秒"
                    else:
                        hours = estimated_time // 3600
                        minutes = (estimated_time % 3600) // 60
                        response_data['estimated_time_remaining_formatted'] = f"{hours}小时{minutes}分"
        
        # 当任务完成时，返回输出文件信息
        if response_data['status'] == 'completed' and task.output_file:
            try:
                # 获取文件信息
                file_path = task.output_file.path
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                response_data.update({
                    'output_file': {
                        'filename': task.output_filename,
                        'file_size': file_size,
                        'file_size_mb': round(file_size / (1024 * 1024), 2),
                        'download_url': f'/api/videos/compose/{task_id}/download/',
                        'stream_url': f'/api/videos/compose/{task_id}/stream/',
                        'file_exists': os.path.exists(file_path)
                    }
                })
            except Exception as e:
                logger.warning(f"获取输出文件信息失败: {str(e)}")
                response_data['output_file'] = {
                    'filename': task.output_filename,
                    'error': '无法获取文件信息'
                }
        
        # 添加任务统计信息
        if task_info:
            response_data['task_info'] = {
                'user_id': task_info.user_id,
                'video_count': len(task_info.video_ids) if task_info.video_ids else len(task.video_list),
                'is_cancelled': task_manager.is_task_cancelled(task_id)
            }
        
        # 添加可执行的操作
        response_data['available_actions'] = []
        if response_data['status'] in ['pending', 'processing']:
            response_data['available_actions'].append('cancel')
        if response_data['status'] == 'completed' and task.output_file:
            response_data['available_actions'].extend(['download', 'stream'])
        
        return Response(response_data)
        
    except CompositionTask.DoesNotExist:
        return Response(
            {'error': '任务不存在或无权访问'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_composed_video(request, task_id):
    """下载合成视频"""
    try:
        task = CompositionTask.objects.get(task_id=task_id, user=request.user)
        
        if not task.can_download():
            return Response(
                {'error': '视频尚未合成完成或合成失败'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 返回文件下载URL
        if task.output_file:
            from django.http import HttpResponse, Http404
            import mimetypes
            
            try:
                # 获取文件路径
                file_path = task.output_file.path
                if not os.path.exists(file_path):
                    return Response(
                        {'error': '文件不存在'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # 确定MIME类型
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                # 读取文件内容
                with open(file_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type=mime_type)
                    response['Content-Disposition'] = f'attachment; filename="{task.output_filename}"'
                    response['Content-Length'] = os.path.getsize(file_path)
                    return response
                    
            except Exception as e:
                logger.error(f"下载文件失败: {str(e)}")
                return Response(
                    {'error': '文件下载失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {'error': '输出文件不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
        
    except CompositionTask.DoesNotExist:
        return Response(
            {'error': '任务不存在或无权访问'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def stream_composed_video(request, task_id):
    """流式播放合成视频"""
    try:
        task = CompositionTask.objects.get(task_id=task_id, user=request.user)
        
        if not task.can_download():
            return Response(
                {'error': '视频尚未合成完成或合成失败'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if task.output_file:
            from django.http import FileResponse, Http404
            import mimetypes
            
            try:
                file_path = task.output_file.path
                if not os.path.exists(file_path):
                    return Response(
                        {'error': '文件不存在'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # 确定MIME类型
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'video/mp4'
                
                # 使用 FileResponse 支持流式传输和范围请求
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=mime_type
                )
                response['Content-Disposition'] = f'inline; filename="{task.output_filename}"'
                response['Accept-Ranges'] = 'bytes'
                
                return response
                    
            except Exception as e:
                logger.error(f"流式播放文件失败: {str(e)}")
                return Response(
                    {'error': '文件播放失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {'error': '输出文件不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
        
    except CompositionTask.DoesNotExist:
        return Response(
            {'error': '任务不存在或无权访问'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def cancel_composition_task(request, task_id):
    """取消合成任务 - 集成 TaskManager 的取消功能"""
    try:
        # 验证任务存在且用户有权限
        task = CompositionTask.objects.get(task_id=task_id, user=request.user)
        
        # 使用 TaskManager 取消任务
        from .task_manager import task_manager
        cancel_result = task_manager.cancel_task(task_id)
        
        if not cancel_result['success']:
            # 检查具体的错误原因
            if '任务状态为' in cancel_result['message']:
                # 任务状态不允许取消
                current_status = task.status
                if current_status in ['completed', 'failed', 'cancelled']:
                    return Response(
                        {
                            'error': f'任务已{current_status}，无法取消',
                            'current_status': current_status,
                            'message': '只能取消等待中或处理中的任务'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # 其他错误
            return Response(
                {
                    'error': cancel_result['message'],
                    'success': False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 取消成功，同步更新数据库状态
        try:
            with transaction.atomic():
                task.status = 'cancelled'
                task.error_message = '用户取消'
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'error_message', 'completed_at'])
                
                logger.info(f"用户 {request.user.username} 成功取消了合成任务: {task_id}")
                
                return Response({
                    'message': '任务已成功取消',
                    'task_id': task_id,
                    'status': 'cancelled',
                    'cancelled_at': task.completed_at.isoformat(),
                    'success': True
                })
        
        except Exception as e:
            logger.error(f"更新取消任务状态失败: {str(e)}")
            # 即使数据库更新失败，TaskManager 中的取消仍然有效
            return Response({
                'message': '任务已取消，但状态更新可能延迟',
                'task_id': task_id,
                'success': True,
                'warning': '数据库状态更新失败'
            })
        
    except CompositionTask.DoesNotExist:
        return Response(
            {
                'error': '任务不存在或无权访问',
                'task_id': task_id
            },
            status=status.HTTP_404_NOT_FOUND
        )


# 系统监控相关API

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def system_statistics(request):
    """获取系统统计信息"""
    from .monitoring import monitoring_service
    
    try:
        stats = monitoring_service.get_system_statistics()
        if stats is None:
            return Response(
                {'error': '获取系统统计失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(stats)
    
    except Exception as e:
        logger.error(f"获取系统统计失败: {str(e)}")
        return Response(
            {'error': '获取系统统计失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# 性能监控相关API

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def performance_statistics(request):
    """获取性能统计信息"""
    from .performance_monitoring import performance_monitor
    
    try:
        # 获取查询参数
        endpoint = request.query_params.get('endpoint')
        method = request.query_params.get('method')
        hours = int(request.query_params.get('hours', 24))
        
        # 获取端点统计
        endpoint_stats = performance_monitor.get_endpoint_stats(endpoint, method, hours)
        
        # 获取性能摘要
        performance_summary = performance_monitor.get_performance_summary()
        
        # 获取告警信息
        alerts = performance_monitor.check_performance_alerts()
        
        return Response({
            'summary': performance_summary,
            'endpoint_stats': endpoint_stats,
            'alerts': alerts,
            'query_params': {
                'endpoint': endpoint,
                'method': method,
                'hours': hours
            }
        })
    
    except Exception as e:
        logger.error(f"获取性能统计失败: {str(e)}")
        return Response(
            {'error': '获取性能统计失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def slow_requests(request):
    """获取慢请求列表"""
    from .performance_monitoring import performance_monitor
    
    try:
        hours = int(request.query_params.get('hours', 1))
        limit = int(request.query_params.get('limit', 50))
        
        slow_requests = performance_monitor.get_slow_requests(hours, limit)
        
        return Response({
            'slow_requests': slow_requests,
            'total_count': len(slow_requests),
            'query_params': {
                'hours': hours,
                'limit': limit
            }
        })
    
    except Exception as e:
        logger.error(f"获取慢请求列表失败: {str(e)}")
        return Response(
            {'error': '获取慢请求列表失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def performance_alerts(request):
    """获取性能告警"""
    from .performance_monitoring import performance_monitor
    
    try:
        alerts = performance_monitor.check_performance_alerts()
        
        # 按严重程度分组
        critical_alerts = [a for a in alerts if a['level'] == 'critical']
        warning_alerts = [a for a in alerts if a['level'] == 'warning']
        
        return Response({
            'alerts': alerts,
            'critical_alerts': critical_alerts,
            'warning_alerts': warning_alerts,
            'summary': {
                'total_alerts': len(alerts),
                'critical_count': len(critical_alerts),
                'warning_count': len(warning_alerts)
            }
        })
    
    except Exception as e:
        logger.error(f"获取性能告警失败: {str(e)}")
        return Response(
            {'error': '获取性能告警失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def storage_info(request):
    """获取存储空间信息"""
    from .monitoring import monitoring_service
    
    try:
        storage_info = monitoring_service.get_storage_info()
        if storage_info is None:
            return Response(
                {'error': '获取存储信息失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 检查警告
        warnings = monitoring_service.check_storage_warnings()
        storage_info['warnings'] = warnings
        
        return Response(storage_info)
    
    except Exception as e:
        logger.error(f"获取存储信息失败: {str(e)}")
        return Response(
            {'error': '获取存储信息失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def create_backup(request):
    """创建数据备份"""
    from .monitoring import monitoring_service
    
    backup_type = request.data.get('type', 'full')
    
    if backup_type not in ['full', 'database', 'media']:
        return Response(
            {'error': '无效的备份类型，支持: full, database, media'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        backup_info = monitoring_service.create_backup(backup_type)
        
        if backup_info['status'] == 'completed':
            return Response({
                'message': '备份创建成功',
                'backup_info': backup_info
            })
        else:
            return Response({
                'message': '备份创建失败',
                'backup_info': backup_info
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"创建备份失败: {str(e)}")
        return Response(
            {'error': '创建备份失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def cleanup_backups(request):
    """清理旧备份"""
    from .monitoring import monitoring_service
    
    keep_days = request.data.get('keep_days', 30)
    
    try:
        keep_days = int(keep_days)
        if keep_days < 1:
            return Response(
                {'error': '保留天数必须大于0'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': '无效的保留天数'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        result = monitoring_service.cleanup_old_backups(keep_days)
        
        return Response({
            'message': f'清理完成，删除了 {result["cleaned"]} 个旧备份',
            'cleaned_count': result['cleaned'],
            'errors': result['errors']
        })
    
    except Exception as e:
        logger.error(f"清理备份失败: {str(e)}")
        return Response(
            {'error': '清理备份失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def run_monitoring_check(request):
    """运行监控检查"""
    from .monitoring import monitoring_service
    
    try:
        results = monitoring_service.run_monitoring_check()
        
        if 'error' in results:
            return Response(
                {'error': results['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': '监控检查完成',
            'results': results
        })
    
    except Exception as e:
        logger.error(f"监控检查失败: {str(e)}")
        return Response(
            {'error': '监控检查失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
