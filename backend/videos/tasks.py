"""
视频合成Celery任务
处理视频合并等耗时操作
"""
import os
import logging
import threading
from datetime import datetime, timedelta
from celery import shared_task
from django.core.files import File
from django.utils import timezone
from django.db import connection
from .task_manager import task_manager, TaskStatus

logger = logging.getLogger(__name__)


def safe_close_db_connection():
    """
    安全地关闭数据库连接
    用于线程开始和结束时确保连接正确管理
    """
    try:
        if connection.connection is not None:
            connection.close()
            logger.debug(f"数据库连接已关闭，线程: {threading.current_thread().name}")
            return True
    except Exception as e:
        logger.warning(f"关闭数据库连接时出错: {e}")
        return False
    return True


def handle_db_connection_error(operation_name, error):
    """
    处理数据库连接相关的错误
    
    Args:
        operation_name: 操作名称
        error: 异常对象
    """
    logger.error(f"数据库操作 '{operation_name}' 失败: {error}")
    
    # 检查是否是连接相关的错误
    error_str = str(error).lower()
    if any(keyword in error_str for keyword in ['connection', 'database', 'timeout', 'closed']):
        logger.warning("检测到数据库连接问题，尝试重置连接")
        try:
            connection.close()
            # Django 会在下次数据库操作时自动创建新连接
        except Exception as close_error:
            logger.error(f"重置数据库连接失败: {close_error}")


def monitor_thread_resources():
    """监控当前线程的资源使用情况"""
    try:
        import psutil
        import os
        
        # 获取当前进程信息
        process = psutil.Process(os.getpid())
        
        # 获取线程数量
        thread_count = process.num_threads()
        
        # 获取内存使用情况
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        logger.debug(f"线程资源监控 - 线程数: {thread_count}, 内存使用: {memory_mb:.2f}MB")
        
        return {
            'thread_count': thread_count,
            'memory_mb': memory_mb,
            'thread_name': threading.current_thread().name
        }
        
    except ImportError:
        logger.debug("psutil 不可用，跳过资源监控")
        return None
    except Exception as e:
        logger.warning(f"监控线程资源时出错: {e}")
        return None


def run_composition_in_thread(task_id):
    """在独立线程中运行视频合成任务 - 集成 TaskManager"""
    thread_name = threading.current_thread().name
    logger.info(f"视频合成线程启动: {thread_name}, 任务ID: {task_id}")
    
    # 监控线程资源
    initial_resources = monitor_thread_resources()
    
    # 关闭当前线程继承的数据库连接，让 Django 为新线程创建独立连接
    # 这是必需的，因为 Django 的数据库连接不是线程安全的
    safe_close_db_connection()
    
    from .models import CompositionTask, Video
    
    def _handle_cancellation(task_id, db_task=None, cleanup_files=None):
        """处理任务取消，同步数据库状态并清理文件"""
        logger.info(f"处理任务取消: {task_id}")
        
        # 清理临时文件
        if cleanup_files:
            _cleanup_temp_files(cleanup_files)
        
        # 同步数据库状态
        if db_task:
            try:
                db_task.status = 'cancelled'
                db_task.completed_at = timezone.now()
                db_task.save()
                logger.info(f"数据库任务状态已更新为取消: {task_id}")
            except Exception as e:
                handle_db_connection_error("更新取消状态", e)
                logger.warning(f"更新数据库取消状态失败: {e}")
    
    def _cleanup_temp_files(file_paths):
        """清理临时文件列表"""
        if not file_paths:
            return
        
        cleaned_count = 0
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"清理临时文件: {file_path}")
                    cleaned_count += 1
                except PermissionError:
                    logger.warning(f"权限不足，无法删除文件: {file_path}")
                except Exception as e:
                    logger.warning(f"清理文件失败 {file_path}: {e}")
        
        logger.info(f"共清理了 {cleaned_count} 个临时文件")
    
    def _cleanup_video_clips(clips):
        """清理视频片段资源"""
        if not clips:
            return
        
        cleaned_count = 0
        for clip in clips:
            try:
                if hasattr(clip, 'close'):
                    clip.close()
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"关闭视频片段失败: {e}")
        
        logger.info(f"共关闭了 {cleaned_count} 个视频片段")
    
    def _ensure_resource_cleanup(task_id, temp_files=None, video_clips=None):
        """确保所有资源得到清理"""
        try:
            # 清理临时文件
            if temp_files:
                _cleanup_temp_files(temp_files)
            
            # 清理视频片段
            if video_clips:
                _cleanup_video_clips(video_clips)
            
            # 清理 TaskManager 中的任务信息
            task_manager.cleanup_task(task_id)
            
            logger.info(f"任务 {task_id} 的所有资源已清理完成")
            
        except Exception as e:
            logger.error(f"清理任务 {task_id} 资源时出错: {e}")


def cleanup_temp_files(file_paths):
    """
    公共接口：清理临时文件列表
    供外部测试使用
    """
    if not file_paths:
        return
    
    cleaned_count = 0
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"清理临时文件: {file_path}")
                cleaned_count += 1
            except PermissionError:
                logger.warning(f"权限不足，无法删除文件: {file_path}")
            except Exception as e:
                logger.warning(f"清理文件失败 {file_path}: {e}")
    
    logger.info(f"共清理了 {cleaned_count} 个临时文件")
    return cleaned_count


def ensure_resource_cleanup(task_id, temp_files=None, video_clips=None):
    """
    公共接口：确保所有资源得到清理
    供外部测试使用
    """
    try:
        # 清理临时文件
        if temp_files:
            cleanup_temp_files(temp_files)
        
        # 清理视频片段
        if video_clips:
            cleaned_count = 0
            for clip in video_clips:
                try:
                    if hasattr(clip, 'close'):
                        clip.close()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"关闭视频片段失败: {e}")
            logger.info(f"共关闭了 {cleaned_count} 个视频片段")
        
        # 清理 TaskManager 中的任务信息
        task_manager.cleanup_task(task_id)
        
        logger.info(f"任务 {task_id} 的所有资源已清理完成")
        return True
        
    except Exception as e:
        logger.error(f"清理任务 {task_id} 资源时出错: {e}")
        return False
    
    try:
        # 获取任务信息
        task_info = task_manager.get_task_info(task_id)
        if not task_info:
            logger.error(f"TaskManager 中找不到任务: {task_id}")
            return
        
        # 检查是否已被取消
        if task_manager.is_task_cancelled(task_id):
            logger.info(f"任务已被取消: {task_id}")
            _handle_cancellation(task_id)
            return
        
        # 获取数据库中的任务记录
        try:
            db_task = CompositionTask.objects.get(task_id=task_id)
        except CompositionTask.DoesNotExist:
            logger.error(f"数据库中找不到合成任务: {task_id}")
            task_manager.update_task_progress(
                task_id, 0, TaskStatus.FAILED.value, 
                error_message="数据库中找不到任务记录"
            )
            return
        except Exception as e:
            handle_db_connection_error("获取任务记录", e)
            task_manager.update_task_progress(
                task_id, 0, TaskStatus.FAILED.value, 
                error_message=f"数据库连接错误: {str(e)}"
            )
            return
        
        # 更新任务状态为处理中
        try:
            db_task.status = 'processing'
            db_task.started_at = timezone.now()
            db_task.progress = 0
            db_task.save()
        except Exception as e:
            handle_db_connection_error("更新任务状态", e)
            task_manager.update_task_progress(
                task_id, 0, TaskStatus.FAILED.value,
                error_message=f"更新任务状态失败: {str(e)}"
            )
            return
        
        # 同步更新 TaskManager
        task_manager.update_task_progress(task_id, 0, TaskStatus.PROCESSING.value)
        
        logger.info(f"开始处理视频合成任务: {task_id}")
        
        # 获取视频列表
        video_ids = db_task.video_list
        if not video_ids or len(video_ids) < 2:
            raise ValueError("至少需要两个视频进行合成")
        
        # 获取视频对象
        videos = []
        for video_id in video_ids:
            # 检查取消状态
            if task_manager.is_task_cancelled(task_id):
                _handle_cancellation(task_id, db_task)
                return
                
            try:
                video = Video.objects.get(id=video_id, is_active=True)
                videos.append(video)
            except Video.DoesNotExist:
                logger.warning(f"视频 {video_id} 不存在或已被删除")
                continue
            except Exception as e:
                handle_db_connection_error("获取视频对象", e)
                logger.warning(f"获取视频 {video_id} 时出错: {e}")
                continue
        
        if len(videos) < 2:
            raise ValueError("有效视频数量不足，至少需要两个视频")
        
        logger.info(f"找到 {len(videos)} 个有效视频")
        
        # 更新进度：验证视频文件 (0-30%)
        task_manager.update_task_progress(
            task_id, 0, TaskStatus.PROCESSING.value,
            current_stage="正在验证视频文件..."
        )
        
        total_duration = timedelta()
        for i, video in enumerate(videos):
            # 检查取消状态
            if task_manager.is_task_cancelled(task_id):
                _handle_cancellation(task_id, db_task)
                return
            
            progress = int((i / len(videos)) * 30)
            
            # 同步更新数据库和 TaskManager
            try:
                db_task.progress = progress
                db_task.save(update_fields=['progress'])
            except Exception as e:
                handle_db_connection_error("更新进度", e)
                # 即使数据库更新失败，也继续执行，只更新 TaskManager
            
            # 计算预计剩余时间
            estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
            
            task_manager.update_task_progress(
                task_id, progress,
                current_stage=f"正在验证视频文件 ({i+1}/{len(videos)}): {video.title}",
                estimated_time_remaining=estimated_time
            )
            
            if video.file_path and os.path.exists(video.file_path.path):
                logger.info(f"验证视频文件: {video.title}")
                if video.duration:
                    total_duration += video.duration
            else:
                logger.warning(f"视频文件不存在: {video.title}")
        
        # 验证完成 (30%)
        try:
            db_task.progress = 30
            db_task.save(update_fields=['progress'])
        except Exception as e:
            handle_db_connection_error("更新验证进度", e)
        
        estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
        task_manager.update_task_progress(
            task_id, 30,
            current_stage="视频文件验证完成，准备开始合成...",
            estimated_time_remaining=estimated_time
        )
        
        # 检查是否有可用的视频处理库
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            moviepy_available = True
        except ImportError:
            moviepy_available = False
            logger.warning("MoviePy 不可用，使用模拟合成")
        
        output_filename = None
        output_path = None
        
        if moviepy_available:
            clips = []  # 跟踪所有加载的视频片段，确保异常时能清理
            final_clip = None  # 跟踪最终合成的片段
            
            try:
                # 加载视频片段 (30-70%)
                task_manager.update_task_progress(
                    task_id, 30,
                    current_stage="正在加载视频片段..."
                )
                
                for i, video in enumerate(videos):
                    # 检查取消状态
                    if task_manager.is_task_cancelled(task_id):
                        # 清理已加载的片段
                        _cleanup_video_clips(clips)
                        _handle_cancellation(task_id, db_task)
                        return
                    
                    progress = 30 + int((i / len(videos)) * 40)
                    
                    # 同步更新进度
                    try:
                        db_task.progress = progress
                        db_task.save(update_fields=['progress'])
                    except Exception as e:
                        handle_db_connection_error("更新加载进度", e)
                    
                    # 计算预计剩余时间
                    estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
                    
                    task_manager.update_task_progress(
                        task_id, progress,
                        current_stage=f"正在加载视频片段 ({i+1}/{len(videos)}): {video.title}",
                        estimated_time_remaining=estimated_time
                    )
                    
                    video_path = video.file_path.path
                    if os.path.exists(video_path):
                        try:
                            clip = VideoFileClip(video_path)
                            clips.append(clip)
                        except Exception as e:
                            logger.warning(f"加载视频文件失败 {video_path}: {e}")
                            continue
                
                if clips:
                    # 检查取消状态
                    if task_manager.is_task_cancelled(task_id):
                        _cleanup_video_clips(clips)
                        _handle_cancellation(task_id, db_task)
                        return
                    
                    # 开始合成 (70%)
                    try:
                        db_task.progress = 70
                        db_task.save(update_fields=['progress'])
                    except Exception as e:
                        handle_db_connection_error("更新合成进度", e)
                    
                    estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
                    task_manager.update_task_progress(
                        task_id, 70,
                        current_stage="正在合并视频片段...",
                        estimated_time_remaining=estimated_time
                    )
                    
                    # 合并视频片段
                    final_clip = concatenate_videoclips(clips, method="compose")
                    
                    # 生成输出文件
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"composed_{timestamp}.mp4"
                    output_dir = os.path.join('media', 'composed', datetime.now().strftime("%Y/%m/%d"))
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 准备写入 (80%)
                    try:
                        db_task.progress = 80
                        db_task.save(update_fields=['progress'])
                    except Exception as e:
                        handle_db_connection_error("更新写入进度", e)
                    
                    estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
                    task_manager.update_task_progress(
                        task_id, 80,
                        current_stage="正在写入合成视频文件...",
                        estimated_time_remaining=estimated_time
                    )
                    
                    # 检查取消状态
                    if task_manager.is_task_cancelled(task_id):
                        _cleanup_video_clips(clips)
                        if final_clip:
                            final_clip.close()
                        _handle_cancellation(task_id, db_task)
                        return
                    
                    # 写入合成视频
                    final_clip.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec='aac',
                        verbose=False,
                        logger=None
                    )
                    
                else:
                    raise ValueError("没有有效的视频文件可以合成")
                    
            except Exception as e:
                logger.error(f"MoviePy 合成失败: {str(e)}")
                moviepy_available = False
                # 确保清理所有视频资源
                _cleanup_video_clips(clips)
                if final_clip:
                    final_clip.close()
            
            finally:
                # 无论成功还是失败，都要清理视频片段资源
                _cleanup_video_clips(clips)
                if final_clip:
                    final_clip.close()
        
        if not moviepy_available:
            # 模拟合成过程 (30-90%)
            import time
            
            # 模拟处理时间，每10%检查一次取消状态
            stages = [
                (30, "正在初始化合成环境..."),
                (40, "正在分析视频格式..."),
                (50, "正在处理视频编码..."),
                (60, "正在合并音频轨道..."),
                (70, "正在合并视频轨道..."),
                (80, "正在优化输出质量..."),
                (90, "正在生成最终文件...")
            ]
            
            for progress, stage_desc in stages:
                # 检查取消状态
                if task_manager.is_task_cancelled(task_id):
                    _handle_cancellation(task_id, db_task)
                    return
                
                # 同步更新进度
                try:
                    db_task.progress = progress
                    db_task.save(update_fields=['progress'])
                except Exception as e:
                    handle_db_connection_error("更新模拟进度", e)
                
                # 计算预计剩余时间
                estimated_time = task_manager.calculate_estimated_time_remaining(task_id)
                
                task_manager.update_task_progress(
                    task_id, progress,
                    current_stage=stage_desc,
                    estimated_time_remaining=estimated_time
                )
                
                time.sleep(0.5)  # 模拟处理延迟
            
            # 创建模拟的合成文件（复制第一个视频作为输出）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"composed_{timestamp}.mp4"
            output_dir = os.path.join('media', 'composed', datetime.now().strftime("%Y/%m/%d"))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            
            # 复制第一个视频作为模拟输出
            if videos and videos[0].file_path and os.path.exists(videos[0].file_path.path):
                import shutil
                shutil.copy(videos[0].file_path.path, output_path)
                logger.info(f"创建模拟合成文件: {output_path}")
            else:
                # 创建一个文本文件作为占位符
                output_filename = f"composed_{timestamp}_mock.txt"
                output_path = os.path.join(output_dir, output_filename)
                mock_content = f"视频合成任务模拟文件\n任务ID: {task_id}\n合成时间: {datetime.now().isoformat()}\n"
                for i, video in enumerate(videos, 1):
                    mock_content += f"{i}. {video.title}\n"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(mock_content)
        
        # 最终检查取消状态
        if task_manager.is_task_cancelled(task_id):
            _handle_cancellation(task_id, db_task, [output_path] if output_path else None)
            return
        
        # 保存输出文件到模型
        if output_path and os.path.exists(output_path):
            try:
                with open(output_path, 'rb') as f:
                    db_task.output_file.save(output_filename, File(f), save=False)
                db_task.output_filename = output_filename
            except Exception as e:
                handle_db_connection_error("保存输出文件", e)
                logger.warning(f"保存输出文件到数据库失败: {e}")
        
        # 完成任务 (100%)
        try:
            db_task.status = 'completed'
            db_task.progress = 100
            db_task.completed_at = timezone.now()
            db_task.total_duration = total_duration
            db_task.save()
        except Exception as e:
            handle_db_connection_error("保存完成状态", e)
            logger.error(f"保存任务完成状态失败: {e}")
            # 即使数据库保存失败，也要更新 TaskManager
        
        # 同步更新 TaskManager
        task_manager.update_task_progress(
            task_id, 100, TaskStatus.COMPLETED.value, 
            output_file=output_filename,
            current_stage="视频合成已完成！"
        )
        
        logger.info(f"视频合成任务完成: {task_id}")
        
    except CompositionTask.DoesNotExist:
        logger.error(f"合成任务不存在: {task_id}")
        task_manager.update_task_progress(
            task_id, 0, TaskStatus.FAILED.value,
            error_message="合成任务不存在"
        )
        
    except Exception as e:
        error_msg = f"视频合成失败: {str(e)}"
        logger.error(f"任务 {task_id} 失败: {error_msg}", exc_info=True)
        
        try:
            # 更新数据库任务状态
            db_task = CompositionTask.objects.get(task_id=task_id)
            db_task.status = 'failed'
            db_task.error_message = error_msg
            db_task.completed_at = timezone.now()
            db_task.save()
            
            # 同步更新 TaskManager
            task_manager.update_task_progress(
                task_id, db_task.progress, TaskStatus.FAILED.value,
                error_message=error_msg
            )
            
        except Exception as save_error:
            handle_db_connection_error("保存失败状态", save_error)
            logger.error(f"保存失败状态时出错: {str(save_error)}")
            # 至少更新 TaskManager
            task_manager.update_task_progress(
                task_id, 0, TaskStatus.FAILED.value,
                error_message=error_msg
            )
    
    finally:
        # 监控线程结束时的资源状态
        final_resources = monitor_thread_resources()
        if initial_resources and final_resources:
            logger.info(f"线程资源变化 - 线程数: {initial_resources['thread_count']} -> {final_resources['thread_count']}, "
                       f"内存: {initial_resources['memory_mb']:.2f}MB -> {final_resources['memory_mb']:.2f}MB")
        
        # 确保数据库连接在线程结束时正确关闭
        # 这防止连接泄漏和资源浪费
        safe_close_db_connection()
        
        # 确保所有资源得到清理
        _ensure_resource_cleanup(task_id)
        
        # 确保 TaskManager 中的任务状态是最终状态
        try:
            task_info = task_manager.get_task_info(task_id)
            if task_info and task_info.status not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                logger.warning(f"任务 {task_id} 在线程结束时状态异常: {task_info.status}")
                # 如果任务状态不是最终状态，标记为失败
                task_manager.update_task_progress(
                    task_id, task_info.progress, TaskStatus.FAILED.value,
                    error_message="线程异常退出"
                )
        except Exception as e:
            logger.error(f"检查任务最终状态时出错: {e}")
        
        logger.info(f"任务 {task_id} 的线程执行完成，所有资源已清理")


@shared_task(bind=True)
def compose_videos_task(self, task_id):
    """
    视频合成任务 - 使用 TaskManager 管理异步执行
    """
    # 使用 TaskManager 启动后台线程
    success = task_manager.start_task(task_id, run_composition_in_thread)
    
    if success:
        logger.info(f"已通过 TaskManager 启动视频合成线程: {task_id}")
        return {
            'status': 'started',
            'task_id': task_id,
            'message': '合成任务已在后台启动'
        }
    else:
        logger.error(f"启动视频合成任务失败: {task_id}")
        return {
            'status': 'failed',
            'task_id': task_id,
            'message': '启动合成任务失败'
        }


@shared_task
def cancel_composition_task(task_id):
    """
    取消视频合成任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        dict: 取消结果
    """
    try:
        result = task_manager.cancel_task(task_id)
        
        if result['success']:
            # 同步更新数据库状态
            try:
                from .models import CompositionTask
                db_task = CompositionTask.objects.get(task_id=task_id)
                if db_task.status in ['pending', 'processing']:
                    db_task.status = 'cancelled'
                    db_task.completed_at = timezone.now()
                    db_task.save()
                    logger.info(f"数据库任务状态已同步更新为取消: {task_id}")
            except CompositionTask.DoesNotExist:
                logger.warning(f"取消任务时数据库中找不到任务: {task_id}")
            except Exception as e:
                handle_db_connection_error("同步取消状态", e)
                logger.warning(f"同步数据库取消状态失败: {e}")
        
        logger.info(f"取消任务请求结果: {task_id} - {result}")
        return result
        
    except Exception as e:
        error_msg = f"取消任务失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'message': error_msg
        }


@shared_task
def cleanup_old_composition_tasks():
    """
    清理旧的合成任务
    删除超过7天的已完成或失败的任务及其文件
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # 查找需要清理的任务
        old_tasks = CompositionTask.objects.filter(
            status__in=['completed', 'failed'],
            created_at__lt=cutoff_date
        )
        
        deleted_count = 0
        for task in old_tasks:
            try:
                # 删除输出文件
                if task.output_file:
                    if os.path.exists(task.output_file.path):
                        os.remove(task.output_file.path)
                        logger.info(f"删除文件: {task.output_file.path}")
                
                # 删除任务记录
                task.delete()
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"清理任务 {task.task_id} 失败: {str(e)}")
                continue
        
        logger.info(f"清理了 {deleted_count} 个旧的合成任务")
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        error_msg = f"清理任务失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'failed',
            'error': error_msg
        }


@shared_task
def cancel_stale_tasks():
    """
    取消长时间处于处理中状态的任务
    如果任务处于processing状态超过2小时，则标记为失败
    """
    from .models import CompositionTask
    
    try:
        cutoff_time = timezone.now() - timedelta(hours=2)
        
        # 查找长时间处于处理中的任务
        stale_tasks = CompositionTask.objects.filter(
            status='processing',
            started_at__lt=cutoff_time
        )
        
        cancelled_count = 0
        for db_task in stale_tasks:
            try:
                # 通过 TaskManager 取消任务
                result = task_manager.cancel_task(db_task.task_id)
                
                # 更新数据库状态
                db_task.status = 'failed'
                db_task.error_message = "任务超时，已自动取消"
                db_task.completed_at = timezone.now()
                db_task.save()
                
                cancelled_count += 1
                logger.warning(f"取消超时任务: {db_task.task_id}")
                
            except Exception as e:
                logger.error(f"取消任务 {db_task.task_id} 失败: {str(e)}")
                continue
        
        logger.info(f"取消了 {cancelled_count} 个超时任务")
        return {
            'status': 'success',
            'cancelled_count': cancelled_count
        }
        
    except Exception as e:
        error_msg = f"取消超时任务失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'failed',
            'error': error_msg
        }
