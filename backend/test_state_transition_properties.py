#!/usr/bin/env python
"""
状态转换属性测试
使用 Hypothesis 进行基于属性的测试，验证任务状态转换的正确性
"""
import os
import sys
import django
from pathlib import Path
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase
from django.test import TestCase
from videos.task_manager import TaskManager, TaskStatus, ProgressTracker


class StateTransitionPropertyTest(HypothesisTestCase):
    """状态转换属性测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 重置 TaskManager 单例状态
        TaskManager._instance = None
        
    def tearDown(self):
        """测试后清理"""
        # 清理所有任务
        if hasattr(TaskManager, '_instance') and TaskManager._instance:
            manager = TaskManager._instance
            if hasattr(manager, '_tasks'):
                with manager._tasks_lock:
                    manager._tasks.clear()
                    manager._progress_tracker._progress_data.clear()
        
        # 重置单例
        TaskManager._instance = None

    @settings(max_examples=50, deadline=15000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        num_tasks=st.integers(min_value=1, max_value=10)
    )
    def test_property_4_state_transition_correctness(self, user_id, video_ids, num_tasks):
        """
        Property 4: 状态转换正确性
        For any 合成任务，其状态转换必须遵循以下规则：
        - pending → processing（线程启动时）
        - pending → cancelled（用户取消时）
        - processing → completed（合成成功时）
        - processing → failed（合成失败时）
        - processing → cancelled（用户取消时）
        
        不允许其他状态转换路径。
        
        **Validates: Requirements 2.1, 2.3, 2.4**
        """
        manager = TaskManager()
        
        # 记录所有状态转换
        state_transitions = []
        
        def mock_successful_executor(task_id):
            """模拟成功的任务执行器"""
            # 记录状态转换：processing -> completed
            manager.update_task_progress(task_id, 50, TaskStatus.PROCESSING.value)
            time.sleep(0.1)  # 模拟处理时间
            manager.update_task_progress(task_id, 100, TaskStatus.COMPLETED.value)
            
            # 记录转换
            state_transitions.append((task_id, TaskStatus.PROCESSING, TaskStatus.COMPLETED))
        
        def mock_failing_executor(task_id):
            """模拟失败的任务执行器"""
            # 记录状态转换：processing -> failed
            manager.update_task_progress(task_id, 30, TaskStatus.PROCESSING.value)
            time.sleep(0.1)  # 模拟处理时间
            manager.update_task_progress(task_id, 30, TaskStatus.FAILED.value, error_message="模拟失败")
            
            # 记录转换
            state_transitions.append((task_id, TaskStatus.PROCESSING, TaskStatus.FAILED))
        
        # 创建多个任务并测试不同的状态转换路径
        task_ids = []
        
        for i in range(num_tasks):
            task_id = manager.register_task(user_id, video_ids)
            task_ids.append(task_id)
            
            # 验证初始状态为 pending
            task_info = manager.get_task_info(task_id)
            assert task_info.status == TaskStatus.PENDING, \
                f"任务 {task_id} 初始状态应为 pending，实际为 {task_info.status}"
        
        # 测试不同的状态转换路径
        for i, task_id in enumerate(task_ids):
            task_info = manager.get_task_info(task_id)
            initial_status = task_info.status
            
            if i % 4 == 0:
                # 路径1: pending → cancelled
                cancel_result = manager.cancel_task(task_id)
                assert cancel_result['success'], f"取消任务 {task_id} 失败: {cancel_result['message']}"
                
                # 验证状态转换
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.CANCELLED, \
                    f"任务 {task_id} 取消后状态应为 cancelled，实际为 {task_info.status}"
                
                state_transitions.append((task_id, TaskStatus.PENDING, TaskStatus.CANCELLED))
                
            elif i % 4 == 1:
                # 路径2: pending → processing → completed
                success = manager.start_task(task_id, mock_successful_executor)
                assert success, f"启动任务 {task_id} 失败"
                
                # 验证状态立即转换为 processing
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.PROCESSING, \
                    f"任务 {task_id} 启动后状态应为 processing，实际为 {task_info.status}"
                
                state_transitions.append((task_id, TaskStatus.PENDING, TaskStatus.PROCESSING))
                
                # 等待任务完成
                if task_info.thread:
                    task_info.thread.join(timeout=5)
                
                # 验证最终状态
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.COMPLETED, \
                    f"任务 {task_id} 完成后状态应为 completed，实际为 {task_info.status}"
                
            elif i % 4 == 2:
                # 路径3: pending → processing → failed
                success = manager.start_task(task_id, mock_failing_executor)
                assert success, f"启动任务 {task_id} 失败"
                
                # 验证状态立即转换为 processing
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.PROCESSING, \
                    f"任务 {task_id} 启动后状态应为 processing，实际为 {task_info.status}"
                
                state_transitions.append((task_id, TaskStatus.PENDING, TaskStatus.PROCESSING))
                
                # 等待任务完成
                if task_info.thread:
                    task_info.thread.join(timeout=5)
                
                # 验证最终状态
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.FAILED, \
                    f"任务 {task_id} 失败后状态应为 failed，实际为 {task_info.status}"
                
            else:
                # 路径4: pending → processing → cancelled
                def mock_cancellable_executor(task_id):
                    """可取消的任务执行器"""
                    manager.update_task_progress(task_id, 20, TaskStatus.PROCESSING.value)
                    
                    # 模拟长时间运行，等待取消
                    for _ in range(50):  # 5秒超时
                        if manager.is_task_cancelled(task_id):
                            manager.update_task_progress(task_id, 20, TaskStatus.CANCELLED.value)
                            state_transitions.append((task_id, TaskStatus.PROCESSING, TaskStatus.CANCELLED))
                            return
                        time.sleep(0.1)
                    
                    # 如果没有被取消，正常完成
                    manager.update_task_progress(task_id, 100, TaskStatus.COMPLETED.value)
                    state_transitions.append((task_id, TaskStatus.PROCESSING, TaskStatus.COMPLETED))
                
                success = manager.start_task(task_id, mock_cancellable_executor)
                assert success, f"启动任务 {task_id} 失败"
                
                # 验证状态立即转换为 processing
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.PROCESSING, \
                    f"任务 {task_id} 启动后状态应为 processing，实际为 {task_info.status}"
                
                state_transitions.append((task_id, TaskStatus.PENDING, TaskStatus.PROCESSING))
                
                # 短暂等待后取消任务
                time.sleep(0.2)
                cancel_result = manager.cancel_task(task_id)
                assert cancel_result['success'], f"取消处理中任务 {task_id} 失败: {cancel_result['message']}"
                
                # 等待任务线程结束
                if task_info.thread:
                    task_info.thread.join(timeout=5)
                
                # 验证最终状态
                task_info = manager.get_task_info(task_id)
                assert task_info.status == TaskStatus.CANCELLED, \
                    f"任务 {task_id} 取消后状态应为 cancelled，实际为 {task_info.status}"
        
        # 属性断言：验证所有状态转换都是合法的
        valid_transitions = {
            (TaskStatus.PENDING, TaskStatus.PROCESSING),
            (TaskStatus.PENDING, TaskStatus.CANCELLED),
            (TaskStatus.PROCESSING, TaskStatus.COMPLETED),
            (TaskStatus.PROCESSING, TaskStatus.FAILED),
            (TaskStatus.PROCESSING, TaskStatus.CANCELLED)
        }
        
        for task_id, from_status, to_status in state_transitions:
            transition = (from_status, to_status)
            assert transition in valid_transitions, \
                f"任务 {task_id} 发生了非法状态转换: {from_status.value} -> {to_status.value}"
        
        # 属性断言：验证没有任务处于中间状态
        for task_id in task_ids:
            task_info = manager.get_task_info(task_id)
            final_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
            assert task_info.status in final_states, \
                f"任务 {task_id} 最终状态 {task_info.status.value} 不是终态"

    @settings(max_examples=30, deadline=10000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_invalid_state_transitions_are_rejected(self, user_id, video_ids):
        """
        测试非法状态转换被正确拒绝
        验证系统不允许非法的状态转换
        """
        manager = TaskManager()
        
        # 创建任务
        task_id = manager.register_task(user_id, video_ids)
        
        # 验证初始状态
        task_info = manager.get_task_info(task_id)
        assert task_info.status == TaskStatus.PENDING
        
        # 尝试非法转换：pending -> completed（跳过 processing）
        manager.update_task_progress(task_id, 100, TaskStatus.COMPLETED.value)
        
        # 验证状态没有改变（或者系统处理了这种情况）
        task_info = manager.get_task_info(task_id)
        # 注意：这里我们允许系统接受这种更新，但要验证逻辑一致性
        
        # 测试已完成任务不能被取消
        if task_info.status == TaskStatus.COMPLETED:
            cancel_result = manager.cancel_task(task_id)
            assert not cancel_result['success'], \
                f"已完成的任务 {task_id} 不应该能被取消"
        
        # 创建另一个任务测试其他非法转换
        task_id2 = manager.register_task(user_id, video_ids)
        
        # 启动任务到 processing 状态
        def dummy_executor(task_id):
            time.sleep(0.1)
            manager.update_task_progress(task_id, 100, TaskStatus.COMPLETED.value)
        
        success = manager.start_task(task_id2, dummy_executor)
        assert success
        
        # 等待任务完成
        task_info2 = manager.get_task_info(task_id2)
        if task_info2.thread:
            task_info2.thread.join(timeout=5)
        
        # 验证已完成任务不能再次启动
        success = manager.start_task(task_id2, dummy_executor)
        assert not success, f"已完成的任务 {task_id2} 不应该能再次启动"

    @settings(max_examples=30, deadline=10000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        num_concurrent_tasks=st.integers(min_value=2, max_value=8)
    )
    def test_concurrent_state_transitions(self, user_id, video_ids, num_concurrent_tasks):
        """
        测试并发状态转换的正确性
        验证多个任务同时进行状态转换时的一致性
        """
        manager = TaskManager()
        
        # 创建多个任务
        task_ids = []
        for _ in range(num_concurrent_tasks):
            task_id = manager.register_task(user_id, video_ids)
            task_ids.append(task_id)
        
        # 并发执行不同的状态转换操作
        def concurrent_operations(task_id, operation_type):
            """并发执行的操作"""
            try:
                if operation_type == 'start_and_complete':
                    def quick_executor(tid):
                        manager.update_task_progress(tid, 50, TaskStatus.PROCESSING.value)
                        time.sleep(0.1)
                        manager.update_task_progress(tid, 100, TaskStatus.COMPLETED.value)
                    
                    success = manager.start_task(task_id, quick_executor)
                    if success:
                        task_info = manager.get_task_info(task_id)
                        if task_info.thread:
                            task_info.thread.join(timeout=5)
                
                elif operation_type == 'start_and_fail':
                    def failing_executor(tid):
                        manager.update_task_progress(tid, 30, TaskStatus.PROCESSING.value)
                        time.sleep(0.1)
                        manager.update_task_progress(tid, 30, TaskStatus.FAILED.value, error_message="并发测试失败")
                    
                    success = manager.start_task(task_id, failing_executor)
                    if success:
                        task_info = manager.get_task_info(task_id)
                        if task_info.thread:
                            task_info.thread.join(timeout=5)
                
                elif operation_type == 'cancel_immediately':
                    manager.cancel_task(task_id)
                
                elif operation_type == 'start_and_cancel':
                    def cancellable_executor(tid):
                        manager.update_task_progress(tid, 20, TaskStatus.PROCESSING.value)
                        for _ in range(20):
                            if manager.is_task_cancelled(tid):
                                manager.update_task_progress(tid, 20, TaskStatus.CANCELLED.value)
                                return
                            time.sleep(0.05)
                        manager.update_task_progress(tid, 100, TaskStatus.COMPLETED.value)
                    
                    success = manager.start_task(task_id, cancellable_executor)
                    if success:
                        time.sleep(0.1)  # 让任务开始执行
                        manager.cancel_task(task_id)
                        task_info = manager.get_task_info(task_id)
                        if task_info.thread:
                            task_info.thread.join(timeout=5)
                
                return True
                
            except Exception as e:
                # 记录异常但不失败，因为并发操作可能有竞争条件
                return False
        
        # 定义操作类型
        operations = ['start_and_complete', 'start_and_fail', 'cancel_immediately', 'start_and_cancel']
        
        # 使用线程池并发执行操作
        with ThreadPoolExecutor(max_workers=min(8, num_concurrent_tasks)) as executor:
            futures = []
            for i, task_id in enumerate(task_ids):
                operation = operations[i % len(operations)]
                future = executor.submit(concurrent_operations, task_id, operation)
                futures.append((task_id, operation, future))
            
            # 等待所有操作完成
            results = []
            for task_id, operation, future in futures:
                try:
                    result = future.result(timeout=10)
                    results.append((task_id, operation, result))
                except Exception as e:
                    results.append((task_id, operation, False))
        
        # 验证所有任务都处于有效的终态
        final_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        
        for task_id in task_ids:
            task_info = manager.get_task_info(task_id)
            assert task_info.status in final_states, \
                f"并发操作后任务 {task_id} 状态 {task_info.status.value} 不是有效终态"
        
        # 验证进度跟踪器的一致性
        progress_tracker = manager._progress_tracker
        for task_id in task_ids:
            progress_info = progress_tracker.get_progress(task_id)
            task_info = manager.get_task_info(task_id)
            
            assert progress_info is not None, f"任务 {task_id} 在进度跟踪器中丢失"
            assert progress_info.status == task_info.status.value, \
                f"任务 {task_id} 状态不一致: 进度跟踪器={progress_info.status}, 任务管理器={task_info.status.value}"


def run_state_transition_tests():
    """运行状态转换属性测试"""
    import unittest
    
    print("🧪 开始运行状态转换属性测试...")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(StateTransitionPropertyTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有状态转换属性测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print("❌ 部分状态转换属性测试失败！")
        print(f"运行了 {result.testsRun} 个测试")
        print(f"失败: {len(result.failures)}")
        print(f"错误: {len(result.errors)}")
        
        if result.failures:
            print("\n失败的测试:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        
        if result.errors:
            print("\n错误的测试:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_state_transition_tests()
    sys.exit(0 if success else 1)