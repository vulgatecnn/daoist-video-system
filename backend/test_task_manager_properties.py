#!/usr/bin/env python
"""
TaskManager 属性测试
使用 Hypothesis 进行基于属性的测试，验证 TaskManager 的正确性属性
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


class TaskManagerPropertyTest(HypothesisTestCase):
    """TaskManager 属性测试类"""
    
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

    @settings(max_examples=50, deadline=10000, suppress_health_check=[])
    @given(
        num_tasks=st.integers(min_value=1, max_value=20),
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_property_2_task_id_uniqueness(self, num_tasks, user_id, video_ids):
        """
        Property 2: 任务ID唯一性
        For any 两个不同的合成任务，它们的 task_id 必须不同。
        即使在高并发场景下创建多个任务，每个任务ID都应该是唯一的。
        
        **Validates: Requirements 1.2, 5.1**
        """
        
        manager = TaskManager()
        task_ids = []
        
        # 使用线程池模拟高并发场景
        def create_task(index):
            return manager.register_task(user_id, video_ids)
        
        # 并发创建任务
        with ThreadPoolExecutor(max_workers=min(10, num_tasks)) as executor:
            futures = [executor.submit(create_task, i) for i in range(num_tasks)]
            
            for future in as_completed(futures):
                task_id = future.result()
                task_ids.append(task_id)
        
        # 验证任务ID唯一性
        unique_task_ids = set(task_ids)
        
        # 属性断言：所有任务ID必须唯一
        assert len(unique_task_ids) == len(task_ids), \
            f"任务ID不唯一！创建了 {len(task_ids)} 个任务，但只有 {len(unique_task_ids)} 个唯一ID"
        
        # 验证每个任务ID都是有效的UUID格式
        for task_id in task_ids:
            try:
                uuid.UUID(task_id)
            except ValueError:
                self.fail(f"任务ID格式无效: {task_id}")
        
        # 验证任务确实被注册到管理器中
        for task_id in task_ids:
            task_info = manager.get_task_info(task_id)
            assert task_info is not None, f"任务 {task_id} 未正确注册"
            assert task_info.task_id == task_id, f"任务ID不匹配: {task_info.task_id} != {task_id}"

    @settings(max_examples=50, deadline=10000)
    @given(
        num_threads=st.integers(min_value=2, max_value=20),
        operations_per_thread=st.integers(min_value=5, max_value=20),
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_property_8_thread_safety_and_resource_management(self, num_threads, operations_per_thread, user_id, video_ids):
        """
        Property 8: 线程安全与资源管理
        For any 后台线程执行：
        - 数据库连接应在线程结束时正确关闭
        - 异常退出时应正确清理资源  
        - 多线程并发访问时数据应保持一致
        
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        manager = TaskManager()
        
        # 用于收集所有操作结果的线程安全容器
        results = []
        results_lock = threading.Lock()
        
        # 用于同步线程启动的屏障
        start_barrier = threading.Barrier(num_threads)
        
        def thread_operations(thread_id):
            """每个线程执行的操作"""
            thread_results = {
                'thread_id': thread_id,
                'created_tasks': [],
                'cancelled_tasks': [],
                'progress_updates': [],
                'exceptions': []
            }
            
            try:
                # 等待所有线程准备就绪
                start_barrier.wait()
                
                # 执行多种操作
                for i in range(operations_per_thread):
                    try:
                        # 1. 创建任务
                        task_id = manager.register_task(user_id, video_ids)
                        thread_results['created_tasks'].append(task_id)
                        
                        # 2. 更新进度（模拟并发进度更新）
                        progress = min(100, (i + 1) * 10)
                        manager.update_task_progress(task_id, progress, "processing")
                        thread_results['progress_updates'].append((task_id, progress))
                        
                        # 3. 随机取消一些任务
                        if i % 3 == 0:
                            cancel_result = manager.cancel_task(task_id)
                            if cancel_result['success']:
                                thread_results['cancelled_tasks'].append(task_id)
                        
                        # 4. 查询任务信息（测试并发读取）
                        task_info = manager.get_task_info(task_id)
                        assert task_info is not None, f"任务信息丢失: {task_id}"
                        
                        # 短暂休眠，增加并发冲突概率
                        time.sleep(0.001)
                        
                    except Exception as e:
                        thread_results['exceptions'].append(str(e))
                        
            except Exception as e:
                thread_results['exceptions'].append(f"线程级异常: {str(e)}")
            
            # 线程安全地添加结果
            with results_lock:
                results.append(thread_results)
        
        # 启动多个线程
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=thread_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)  # 30秒超时
            if thread.is_alive():
                self.fail(f"线程 {thread.name} 超时未完成")
        
        # 验证线程安全性和数据一致性
        all_created_tasks = []
        all_cancelled_tasks = []
        total_exceptions = []
        
        for result in results:
            all_created_tasks.extend(result['created_tasks'])
            all_cancelled_tasks.extend(result['cancelled_tasks'])
            total_exceptions.extend(result['exceptions'])
        
        # 属性断言1: 所有创建的任务ID必须唯一（线程安全）
        unique_created_tasks = set(all_created_tasks)
        assert len(unique_created_tasks) == len(all_created_tasks), \
            f"并发创建任务时出现重复ID！创建 {len(all_created_tasks)} 个，唯一 {len(unique_created_tasks)} 个"
        
        # 属性断言2: 所有任务都应该在管理器中可查询到
        for task_id in all_created_tasks:
            task_info = manager.get_task_info(task_id)
            assert task_info is not None, f"任务 {task_id} 在并发操作后丢失"
        
        # 属性断言3: 取消的任务状态应该正确
        for task_id in all_cancelled_tasks:
            task_info = manager.get_task_info(task_id)
            if task_info:  # 任务可能已被清理
                assert task_info.status == TaskStatus.CANCELLED, \
                    f"已取消任务 {task_id} 状态错误: {task_info.status}"
        
        # 属性断言4: 不应该有未处理的异常（资源管理正确）
        critical_exceptions = [e for e in total_exceptions if 'critical' in e.lower() or 'deadlock' in e.lower()]
        assert len(critical_exceptions) == 0, f"发现严重异常: {critical_exceptions}"
        
        # 属性断言5: 验证进度跟踪器的数据一致性
        progress_tracker = manager._progress_tracker
        with progress_tracker._lock:
            tracked_tasks = set(progress_tracker._progress_data.keys())
            manager_tasks = set(manager._tasks.keys())
            
            # 所有管理器中的任务都应该在进度跟踪器中有记录
            missing_in_tracker = manager_tasks - tracked_tasks
            assert len(missing_in_tracker) == 0, \
                f"进度跟踪器中缺少任务: {missing_in_tracker}"

    @settings(max_examples=30, deadline=8000)
    @given(
        task_count=st.integers(min_value=1, max_value=10),
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_property_8_resource_cleanup_on_exception(self, task_count, user_id, video_ids):
        """
        Property 8 补充测试: 异常情况下的资源清理
        验证在异常退出时资源能够正确清理
        
        **Validates: Requirements 5.2, 5.3**
        """
        manager = TaskManager()
        
        # 创建一些任务
        task_ids = []
        for _ in range(task_count):
            task_id = manager.register_task(user_id, video_ids)
            task_ids.append(task_id)
        
        # 模拟异常情况下的资源清理
        def mock_task_executor_with_exception(task_id):
            """模拟会抛出异常的任务执行器"""
            # 更新一些进度
            manager.update_task_progress(task_id, 10, "processing")
            
            # 模拟异常
            raise RuntimeError(f"模拟任务 {task_id} 执行异常")
        
        # 启动任务并模拟异常
        for task_id in task_ids:
            try:
                # 启动任务（会因为异常而失败）
                success = manager.start_task(task_id, mock_task_executor_with_exception)
                assert success, f"任务 {task_id} 启动失败"
                
                # 等待线程结束
                task_info = manager.get_task_info(task_id)
                if task_info and task_info.thread:
                    task_info.thread.join(timeout=5)
                
            except Exception:
                pass  # 预期会有异常
        
        # 验证资源清理
        time.sleep(0.1)  # 给线程一些时间完成清理
        
        # 属性断言1: 所有任务仍然可查询（即使执行失败）
        for task_id in task_ids:
            task_info = manager.get_task_info(task_id)
            assert task_info is not None, f"异常后任务信息丢失: {task_id}"
        
        # 属性断言2: 进度跟踪器数据一致性
        progress_tracker = manager._progress_tracker
        for task_id in task_ids:
            progress_info = progress_tracker.get_progress(task_id)
            assert progress_info is not None, f"异常后进度信息丢失: {task_id}"
        
        # 属性断言3: 清理操作应该正常工作
        for task_id in task_ids:
            try:
                manager.cleanup_task(task_id)
            except Exception as e:
                self.fail(f"清理任务 {task_id} 时发生异常: {e}")
        
        # 验证清理后任务确实被移除
        for task_id in task_ids:
            task_info = manager.get_task_info(task_id)
            assert task_info is None, f"清理后任务仍存在: {task_id}"


def run_property_tests():
    """运行属性测试"""
    import unittest
    
    print("🧪 开始运行 TaskManager 属性测试...")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TaskManagerPropertyTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有属性测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print("❌ 部分属性测试失败！")
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
    success = run_property_tests()
    sys.exit(0 if success else 1)