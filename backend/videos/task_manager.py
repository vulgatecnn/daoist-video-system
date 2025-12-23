"""
异步视频合成任务管理器
提供线程安全的任务管理和进度跟踪功能
"""
import threading
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    status: TaskStatus
    progress: int  # 0-100
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    thread: Optional[threading.Thread] = None
    cancel_event: Optional[threading.Event] = None
    user_id: Optional[int] = None
    video_ids: Optional[list] = None


@dataclass
class ProgressInfo:
    """进度信息数据类"""
    task_id: str
    status: str
    progress: int
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_stage: Optional[str] = None  # 当前处理阶段描述
    estimated_time_remaining: Optional[int] = None  # 预计剩余时间（秒）


class ProgressTracker:
    """进度跟踪器 - 线程安全"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._progress_data: Dict[str, ProgressInfo] = {}
    
    def update_progress(self, task_id: str, progress: int, 
                       status: Optional[str] = None, 
                       output_file: Optional[str] = None,
                       error_message: Optional[str] = None,
                       current_stage: Optional[str] = None,
                       estimated_time_remaining: Optional[int] = None) -> None:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            status: 可选的状态更新
            output_file: 可选的输出文件路径
            error_message: 可选的错误信息
            current_stage: 可选的当前处理阶段描述
            estimated_time_remaining: 可选的预计剩余时间（秒）
        """
        with self._lock:
            self._update_progress_internal(
                task_id, progress, status, output_file, error_message, 
                current_stage, estimated_time_remaining
            )
    
    def _update_progress_internal(self, task_id: str, progress: int, 
                                 status: Optional[str] = None, 
                                 output_file: Optional[str] = None,
                                 error_message: Optional[str] = None,
                                 current_stage: Optional[str] = None,
                                 estimated_time_remaining: Optional[int] = None) -> None:
        """
        内部进度更新方法（不使用锁，由调用者确保线程安全）
        """
        # 确保进度值在有效范围内
        progress = max(0, min(100, progress))
        
        if task_id in self._progress_data:
            current_info = self._progress_data[task_id]
            
            # 确保进度单调递增
            if progress < current_info.progress:
                logger.warning(f"任务 {task_id} 进度回退: {current_info.progress} -> {progress}")
                progress = current_info.progress
            
            # 更新进度信息
            current_info.progress = progress
            if status is not None:
                current_info.status = status
            if output_file is not None:
                current_info.output_file = output_file
            if error_message is not None:
                current_info.error_message = error_message
            if current_stage is not None:
                current_info.current_stage = current_stage
            if estimated_time_remaining is not None:
                current_info.estimated_time_remaining = estimated_time_remaining
            
            # 更新时间戳
            if status == TaskStatus.PROCESSING.value and current_info.started_at is None:
                current_info.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                current_info.completed_at = datetime.now()
                # 任务完成时清除剩余时间和阶段描述
                current_info.estimated_time_remaining = None
                if status == TaskStatus.COMPLETED.value:
                    current_info.current_stage = "任务已完成"
                elif status == TaskStatus.FAILED.value:
                    current_info.current_stage = "任务执行失败"
                elif status == TaskStatus.CANCELLED.value:
                    current_info.current_stage = "任务已取消"
            
            logger.debug(f"更新任务 {task_id} 进度: {progress}%, 状态: {status}, 阶段: {current_stage}")
        else:
            logger.warning(f"尝试更新不存在的任务进度: {task_id}")
    
    def get_progress(self, task_id: str) -> Optional[ProgressInfo]:
        """获取任务进度信息"""
        with self._lock:
            return self._progress_data.get(task_id)
    
    def create_progress_entry(self, task_id: str, status: str = TaskStatus.PENDING.value) -> ProgressInfo:
        """创建进度条目"""
        with self._lock:
            progress_info = ProgressInfo(
                task_id=task_id,
                status=status,
                progress=0,
                created_at=datetime.now()
            )
            self._progress_data[task_id] = progress_info
            return progress_info
    
    def remove_progress_entry(self, task_id: str) -> None:
        """移除进度条目"""
        with self._lock:
            if task_id in self._progress_data:
                del self._progress_data[task_id]
                logger.debug(f"移除任务进度条目: {task_id}")


class TaskManager:
    """任务管理器 - 线程安全的单例"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化任务管理器"""
        if self._initialized:
            return
        
        self._tasks: Dict[str, TaskInfo] = {}
        self._tasks_lock = threading.Lock()
        self._progress_tracker = ProgressTracker()
        self._initialized = True
        
        logger.info("TaskManager 单例已初始化")
    
    def generate_task_id(self) -> str:
        """生成唯一的任务ID"""
        return str(uuid.uuid4())
    
    def register_task(self, user_id: int, video_ids: list, 
                     task_executor: Optional[Callable] = None) -> str:
        """
        注册新任务
        
        Args:
            user_id: 用户ID
            video_ids: 视频ID列表
            task_executor: 可选的任务执行函数
            
        Returns:
            str: 任务ID
        """
        task_id = self.generate_task_id()
        
        with self._tasks_lock:
            # 创建取消事件
            cancel_event = threading.Event()
            
            # 创建任务信息
            task_info = TaskInfo(
                task_id=task_id,
                status=TaskStatus.PENDING,
                progress=0,
                created_at=datetime.now(),
                cancel_event=cancel_event,
                user_id=user_id,
                video_ids=video_ids
            )
            
            self._tasks[task_id] = task_info
            
            # 在进度跟踪器中创建条目
            self._progress_tracker.create_progress_entry(task_id, TaskStatus.PENDING.value)
            
            logger.info(f"注册新任务: {task_id}, 用户: {user_id}, 视频数量: {len(video_ids)}")
        
        return task_id
    
    def start_task(self, task_id: str, task_executor: Callable[[str], None]) -> bool:
        """
        启动后台合成线程
        
        Args:
            task_id: 任务ID
            task_executor: 任务执行函数
            
        Returns:
            bool: 是否成功启动
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            task_info = self._tasks[task_id]
            
            if task_info.status != TaskStatus.PENDING:
                logger.warning(f"任务 {task_id} 状态不是 pending，无法启动: {task_info.status}")
                return False
            
            # 创建并启动线程
            thread = threading.Thread(
                target=task_executor,
                args=(task_id,),
                name=f"CompositionTask-{task_id[:8]}"
            )
            thread.daemon = True
            
            # 更新任务信息
            task_info.thread = thread
            task_info.status = TaskStatus.PROCESSING
            task_info.started_at = datetime.now()
            
            # 更新进度跟踪器
            self._progress_tracker.update_progress(
                task_id, 0, TaskStatus.PROCESSING.value
            )
            
            # 启动线程
            thread.start()
            
            logger.info(f"启动任务线程: {task_id}")
            return True
    
    def cancel_task(self, task_id: str) -> dict:
        """
        取消任务（仅限pending/processing状态）
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 取消结果
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                return {
                    'success': False,
                    'message': f'任务不存在: {task_id}'
                }
            
            task_info = self._tasks[task_id]
            
            # 检查任务状态
            if task_info.status not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                return {
                    'success': False,
                    'message': f'任务状态为 {task_info.status.value}，无法取消'
                }
            
            # 设置取消标志
            if task_info.cancel_event:
                task_info.cancel_event.set()
            
            # 更新任务状态
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.now()
            
            # 更新进度跟踪器
            self._progress_tracker.update_progress(
                task_id, task_info.progress, TaskStatus.CANCELLED.value
            )
            
            logger.info(f"取消任务: {task_id}")
            
            return {
                'success': True,
                'message': '任务已取消'
            }
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def get_progress_info(self, task_id: str) -> Optional[ProgressInfo]:
        """获取任务进度信息"""
        return self._progress_tracker.get_progress(task_id)
    
    def update_task_progress(self, task_id: str, progress: int, 
                           status: Optional[str] = None,
                           output_file: Optional[str] = None,
                           error_message: Optional[str] = None,
                           current_stage: Optional[str] = None,
                           estimated_time_remaining: Optional[int] = None) -> None:
        """更新任务进度"""
        # 使用单一锁确保原子性更新
        with self._tasks_lock:
            if task_id in self._tasks:
                task_info = self._tasks[task_id]
                
                # 确保进度值在有效范围内
                normalized_progress = max(0, min(100, progress))
                
                # 确保进度单调递增
                if normalized_progress < task_info.progress:
                    logger.warning(f"任务 {task_id} 进度回退被阻止: {task_info.progress} -> {normalized_progress}")
                    normalized_progress = task_info.progress
                
                # 更新任务信息
                task_info.progress = normalized_progress
                
                if status:
                    try:
                        task_info.status = TaskStatus(status)
                    except ValueError:
                        logger.warning(f"无效的任务状态: {status}")
                
                if output_file:
                    task_info.output_file = output_file
                
                if error_message:
                    task_info.error_message = error_message
                
                # 在同一个锁内更新进度跟踪器，确保一致性
                self._progress_tracker._update_progress_internal(
                    task_id, normalized_progress, status, output_file, error_message,
                    current_stage, estimated_time_remaining
                )
            else:
                logger.warning(f"尝试更新不存在的任务进度: {task_id}")
    
    def cleanup_task(self, task_id: str) -> None:
        """清理任务资源"""
        with self._tasks_lock:
            if task_id in self._tasks:
                task_info = self._tasks[task_id]
                
                # 如果线程还在运行，等待其结束
                if task_info.thread and task_info.thread.is_alive():
                    logger.info(f"等待任务线程结束: {task_id}")
                    # 不使用 join() 避免阻塞，让线程自然结束
                
                # 移除任务信息
                del self._tasks[task_id]
                
                # 移除进度跟踪信息
                self._progress_tracker.remove_progress_entry(task_id)
                
                logger.info(f"清理任务资源: {task_id}")
    
    def is_task_cancelled(self, task_id: str) -> bool:
        """检查任务是否被取消"""
        with self._tasks_lock:
            if task_id in self._tasks:
                task_info = self._tasks[task_id]
                return (task_info.cancel_event and task_info.cancel_event.is_set()) or \
                       task_info.status == TaskStatus.CANCELLED
        return False
    
    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """获取所有任务信息（用于调试）"""
        with self._tasks_lock:
            return self._tasks.copy()
    
    def calculate_estimated_time_remaining(self, task_id: str) -> Optional[int]:
        """
        计算预计剩余时间
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[int]: 预计剩余时间（秒），如果无法计算则返回None
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                return None
            
            task_info = self._tasks[task_id]
            
            # 只有处理中的任务才计算剩余时间
            if task_info.status != TaskStatus.PROCESSING or not task_info.started_at:
                return None
            
            # 如果进度为0，无法计算
            if task_info.progress <= 0:
                return None
            
            # 计算已用时间
            elapsed_time = (datetime.now() - task_info.started_at).total_seconds()
            
            # 计算平均每百分比用时
            time_per_percent = elapsed_time / task_info.progress
            
            # 计算剩余百分比
            remaining_percent = 100 - task_info.progress
            
            # 计算预计剩余时间
            estimated_remaining = int(time_per_percent * remaining_percent)
            
            return estimated_remaining

    def get_task_count_by_status(self, status: TaskStatus) -> int:
        """获取指定状态的任务数量"""
        with self._tasks_lock:
            return sum(1 for task in self._tasks.values() if task.status == status)


# 全局单例实例
task_manager = TaskManager()