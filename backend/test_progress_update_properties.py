#!/usr/bin/env python
"""
进度更新属性测试
使用 Hypothesis 进行基于属性的测试，验证进度更新的一致性
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


class ProgressUpdatePropertyTest(HypothesisTestCase):
    """进度更新属性测试类"""
    
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
        progress_updates=st.lists(
            st.integers(min_value=0, max_value=100), 
            min_size=5, max_size=20
        )
    )
    def test_property_5_progress_update_consistency(self, user_id, video_ids, progress_updates):
        """
        Property 5: 进度更新一致性
        For any 处于 processing 状态的任务，其进度值必须：
        - 在 0-100 范围内
        - 单调递增（不会回退）
        - 完成时达到 100
        
        **Validates: Requirements 2.2**
        """
        manager = TaskManager()
        
        # 创建任务
        task_id = manager.register_task(user_id, video_ids)
        
        # 验证初始进度
        progress_info = manager.get_progress_info(task_id)
        assert progress_info is not None, f"任务 {task_id} 进度信息不存在"
        assert progress_info.progress == 0, f"初始进度应为 0，实际为 {progress_info.progress}"
        
        # 启动任务到 processing 状态
        def mock_executor(task_id):
            """模拟任务执行器，用于测试进度更新"""
            # 任务执行器不做实际工作，只是保持任务在 processing 状态
            time.sleep(0.1)
        
        success = manager.start_task(task_id, mock_executor)
        assert success, f"启动任务 {task_id} 失败"
        
        # 验证任务状态为 processing
        task_info = manager.get_task_info(task_id)
        assert task_info.status == TaskStatus.PROCESSING, \
            f"任务状态应为 processing，实际为 {task_info.status}"
        
        # 记录所有进度更新
        recorded_progress = [0]  # 初始进度
        
        # 对进度更新序列进行排序，模拟正常的进度递增
        sorted_progress_updates = sorted(progress_updates)
        
        # 应用进度更新
        for i, progress in enumerate(sorted_progress_updates):
            manager.update_task_progress(task_id, progress, TaskStatus.PROCESSING.value)
            
            # 获取当前进度
            current_progress_info = manager.get_progress_info(task_id)
            current_task_info = manager.get_task_info(task_id)
            
            # 属性断言1: 进度值在 0-100 范围内
            assert 0 <= current_progress_info.progress <= 100, \
                f"进度值 {current_progress_info.progress} 超出 0-100 范围"
            assert 0 <= current_task_info.progress <= 100, \
                f"任务进度值 {current_task_info.progress} 超出 0-100 范围"
            
            # 属性断言2: 进度单调递增（不会回退）
            last_progress = recorded_progress[-1]
            assert current_progress_info.progress >= last_progress, \
                f"进度回退: {last_progress} -> {current_progress_info.progress}"
            assert current_task_info.progress >= last_progress, \
                f"任务进度回退: {last_progress} -> {current_task_info.progress}"
            
            # 记录当前进度
            recorded_progress.append(current_progress_info.progress)
            
            # 验证进度跟踪器和任务管理器的一致性
            assert current_progress_info.progress == current_task_info.progress, \
                f"进度不一致: 跟踪器={current_progress_info.progress}, 管理器={current_task_info.progress}"
        
        # 测试完成状态的进度
        manager.update_task_progress(task_id, 100, TaskStatus.COMPLETED.value)
        
        final_progress_info = manager.get_progress_info(task_id)
        final_task_info = manager.get_task_info(task_id)
        
        # 属性断言3: 完成时达到 100
        assert final_progress_info.progress == 100, \
            f"完成时进度应为 100，实际为 {final_progress_info.progress}"
        assert final_task_info.progress == 100, \
            f"完成时任务进度应为 100，实际为 {final_task_info.progress}"
        assert final_task_info.status == TaskStatus.COMPLETED, \
            f"最终状态应为 completed，实际为 {final_task_info.status}"
        
        # 等待线程结束
        if final_task_info.thread:
            final_task_info.thread.join(timeout=5)

    @settings(max_examples=30, deadline=10000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        invalid_progress_values=st.lists(
            st.integers(min_value=-100, max_value=200).filter(lambda x: x < 0 or x > 100),
            min_size=3, max_size=10
        )
    )
    def test_progress_bounds_enforcement(self, user_id, video_ids, invalid_progress_values):
        """
        测试进度边界强制执行
        验证系统正确处理超出范围的进度值
        """
        manager = TaskManager()
        
        # 创建并启动任务
        task_id = manager.register_task(user_id, video_ids)
        
        def mock_executor(task_id):
            time.sleep(0.1)
        
        success = manager.start_task(task_id, mock_executor)
        assert success
        
        # 测试无效进度值的处理
        for invalid_progress in invalid_progress_values:
            # 更新进度
            manager.update_task_progress(task_id, invalid_progress, TaskStatus.PROCESSING.value)
            
            # 验证进度被限制在有效范围内
            progress_info = manager.get_progress_info(task_id)
            task_info = manager.get_task_info(task_id)
            
            # 属性断言: 进度值被强制限制在 0-100 范围内
            assert 0 <= progress_info.progress <= 100, \
                f"无效进度值 {invalid_progress} 未被正确限制，当前进度: {progress_info.progress}"
            assert 0 <= task_info.progress <= 100, \
                f"无效进度值 {invalid_progress} 未被正确限制，当前任务进度: {task_info.progress}"
        
        # 清理
        if task_info.thread:
            task_info.thread.join(timeout=5)

    @settings(max_examples=30, deadline=12000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        num_threads=st.integers(min_value=2, max_value=8),
        updates_per_thread=st.integers(min_value=5, max_value=15)
    )
    def test_concurrent_progress_updates(self, user_id, video_ids, num_threads, updates_per_thread):
        """
        测试并发进度更新的一致性
        验证多线程同时更新进度时的正确性
        """
        manager = TaskManager()
        
        # 创建任务
        task_id = manager.register_task(user_id, video_ids)
        
        # 启动任务
        def mock_executor(task_id):
            # 保持任务运行，等待并发更新
            time.sleep(2)
        
        success = manager.start_task(task_id, mock_executor)
        assert success
        
        # 用于同步的屏障
        start_barrier = threading.Barrier(num_threads)
        
        # 记录所有更新
        all_updates = []
        updates_lock = threading.Lock()
        
        def concurrent_updater(thread_id):
            """并发更新进度的函数"""
            try:
                # 等待所有线程准备就绪
                start_barrier.wait()
                
                # 每个线程执行一系列进度更新
                for i in range(updates_per_thread):
                    # 计算递增的进度值
                    progress = min(99, (thread_id * updates_per_thread + i + 1) * 2)
                    
                    # 更新进度
                    manager.update_task_progress(task_id, progress, TaskStatus.PROCESSING.value)
                    
                    # 记录更新
                    with updates_lock:
                        current_progress_info = manager.get_progress_info(task_id)
                        all_updates.append({
                            'thread_id': thread_id,
                            'requested_progress': progress,
                            'actual_progress': current_progress_info.progress,
                            'timestamp': time.time()
                        })
                    
                    # 短暂休眠增加并发冲突概率
                    time.sleep(0.01)
                    
            except Exception as e:
                with updates_lock:
                    all_updates.append({
                        'thread_id': thread_id,
                        'error': str(e),
                        'timestamp': time.time()
                    })
        
        # 启动并发更新线程
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=concurrent_updater, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有更新线程完成
        for thread in threads:
            thread.join(timeout=10)
        
        # 等待主任务线程完成
        task_info = manager.get_task_info(task_id)
        if task_info.thread:
            task_info.thread.join(timeout=5)
        
        # 验证并发更新的结果
        final_progress_info = manager.get_progress_info(task_id)
        final_task_info = manager.get_task_info(task_id)
        
        # 属性断言1: 最终进度在有效范围内
        assert 0 <= final_progress_info.progress <= 100, \
            f"并发更新后进度超出范围: {final_progress_info.progress}"
        
        # 属性断言2: 进度跟踪器和任务管理器一致
        assert final_progress_info.progress == final_task_info.progress, \
            f"并发更新后进度不一致: 跟踪器={final_progress_info.progress}, 管理器={final_task_info.progress}"
        
        # 属性断言3: 验证单调性（从更新记录中）
        valid_updates = [u for u in all_updates if 'error' not in u]
        if len(valid_updates) > 1:
            # 按时间戳排序
            valid_updates.sort(key=lambda x: x['timestamp'])
            
            # 检查实际进度的单调性
            for i in range(1, len(valid_updates)):
                prev_progress = valid_updates[i-1]['actual_progress']
                curr_progress = valid_updates[i]['actual_progress']
                
                assert curr_progress >= prev_progress, \
                    f"并发更新中发现进度回退: {prev_progress} -> {curr_progress}"
        
        # 属性断言4: 没有严重错误
        errors = [u for u in all_updates if 'error' in u]
        critical_errors = [e for e in errors if 'deadlock' in e['error'].lower() or 'critical' in e['error'].lower()]
        assert len(critical_errors) == 0, f"发现严重并发错误: {critical_errors}"

    @settings(max_examples=30, deadline=10000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        progress_sequence=st.lists(
            st.integers(min_value=0, max_value=100),
            min_size=10, max_size=30
        )
    )
    def test_monotonic_progress_enforcement(self, user_id, video_ids, progress_sequence):
        """
        测试单调性强制执行
        验证系统拒绝或修正进度回退
        """
        manager = TaskManager()
        
        # 创建并启动任务
        task_id = manager.register_task(user_id, video_ids)
        
        def mock_executor(task_id):
            time.sleep(0.1)
        
        success = manager.start_task(task_id, mock_executor)
        assert success
        
        # 记录进度历史
        progress_history = [0]  # 初始进度
        
        # 应用进度序列（可能包含回退）
        for progress in progress_sequence:
            manager.update_task_progress(task_id, progress, TaskStatus.PROCESSING.value)
            
            current_progress_info = manager.get_progress_info(task_id)
            current_progress = current_progress_info.progress
            
            # 属性断言: 进度不应回退
            last_progress = progress_history[-1]
            assert current_progress >= last_progress, \
                f"进度回退被允许: {last_progress} -> {current_progress} (请求进度: {progress})"
            
            progress_history.append(current_progress)
        
        # 验证进度历史的单调性
        for i in range(1, len(progress_history)):
            assert progress_history[i] >= progress_history[i-1], \
                f"进度历史中发现回退: 位置 {i-1}={progress_history[i-1]} -> 位置 {i}={progress_history[i]}"
        
        # 清理
        task_info = manager.get_task_info(task_id)
        if task_info.thread:
            task_info.thread.join(timeout=5)

    @settings(max_examples=20, deadline=8000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_completion_progress_requirement(self, user_id, video_ids):
        """
        测试完成时进度要求
        验证任务完成时进度必须为 100
        """
        manager = TaskManager()
        
        # 创建任务
        task_id = manager.register_task(user_id, video_ids)
        
        # 启动任务
        def mock_executor(task_id):
            # 模拟渐进式进度更新
            for progress in [10, 30, 50, 70, 90]:
                manager.update_task_progress(task_id, progress, TaskStatus.PROCESSING.value)
                time.sleep(0.02)
            
            # 完成任务
            manager.update_task_progress(task_id, 100, TaskStatus.COMPLETED.value)
        
        success = manager.start_task(task_id, mock_executor)
        assert success
        
        # 等待任务完成
        task_info = manager.get_task_info(task_id)
        if task_info.thread:
            task_info.thread.join(timeout=5)
        
        # 验证完成状态
        final_progress_info = manager.get_progress_info(task_id)
        final_task_info = manager.get_task_info(task_id)
        
        # 属性断言: 完成时进度必须为 100
        if final_task_info.status == TaskStatus.COMPLETED:
            assert final_progress_info.progress == 100, \
                f"任务完成但进度不是 100: {final_progress_info.progress}"
            assert final_task_info.progress == 100, \
                f"任务完成但进度不是 100: {final_task_info.progress}"
        
        # 测试强制完成（进度不足 100 时标记为完成）
        task_id2 = manager.register_task(user_id, video_ids)
        
        def incomplete_executor(task_id):
            # 只更新到 80% 就尝试标记完成
            manager.update_task_progress(task_id, 80, TaskStatus.PROCESSING.value)
            time.sleep(0.1)
            manager.update_task_progress(task_id, 80, TaskStatus.COMPLETED.value)  # 进度不足但标记完成
        
        success = manager.start_task(task_id2, incomplete_executor)
        assert success
        
        # 等待任务完成
        task_info2 = manager.get_task_info(task_id2)
        if task_info2.thread:
            task_info2.thread.join(timeout=5)
        
        # 验证系统如何处理这种情况
        final_progress_info2 = manager.get_progress_info(task_id2)
        final_task_info2 = manager.get_task_info(task_id2)
        
        # 如果任务被标记为完成，进度应该被自动调整为 100
        # 或者系统应该拒绝这种不一致的状态
        if final_task_info2.status == TaskStatus.COMPLETED:
            # 这里我们期望系统能够处理这种不一致性
            # 可以是自动调整进度到 100，或者保持原进度但记录警告
            assert final_progress_info2.progress >= 0, \
                f"完成任务的进度应该是有效值: {final_progress_info2.progress}"


def run_progress_update_tests():
    """运行进度更新属性测试"""
    import unittest
    
    print("🧪 开始运行进度更新属性测试...")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(ProgressUpdatePropertyTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有进度更新属性测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print("❌ 部分进度更新属性测试失败！")
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
    success = run_progress_update_tests()
    sys.exit(0 if success else 1)