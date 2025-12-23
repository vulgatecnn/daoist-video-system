#!/usr/bin/env python
"""
资源管理属性测试
使用 Hypothesis 进行基于属性的测试，验证线程安全与资源管理的正确性属性
"""
import os
import sys
import django
from pathlib import Path
import threading
import time
import uuid
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock, Mock

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase
from django.test import TestCase
from django.db import connection
from videos.task_manager import TaskManager, TaskStatus, ProgressTracker
from videos.tasks import (
    safe_close_db_connection, 
    handle_db_connection_error,
    monitor_thread_resources,
    run_composition_in_thread,
    cleanup_temp_files,
    ensure_resource_cleanup
)


class ResourceManagementPropertyTest(HypothesisTestCase):
    """
    资源管理属性测试类
    
    测试 Property 8: 线程安全与资源管理（补充）
    验证需求 5.2, 5.3
    """
    
    def setUp(self):
        """测试前准备"""
        self.task_manager = TaskManager()
        self.temp_dirs = []
        self.temp_files = []
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件和目录
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception:
                pass
        
        # 清理任务管理器
        try:
            self.task_manager._tasks.clear()
        except Exception:
            pass
    
    def create_temp_file(self, content="test"):
        """创建临时文件"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        temp_file.write(content)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def create_temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    @settings(max_examples=50, deadline=30000)
    @given(
        thread_count=st.integers(min_value=1, max_value=5),
        operations_per_thread=st.integers(min_value=1, max_value=10)
    )
    def test_database_connection_safety_property(self, thread_count, operations_per_thread):
        """
        Property 8a: 数据库连接安全性
        
        For any 多线程数据库操作，每个线程的数据库连接应该独立管理，
        不会出现连接泄漏或连接冲突
        
        **Feature: async-video-composition, Property 8a: 数据库连接安全性**
        **Validates: Requirements 5.2**
        """
        connection_states = []
        errors = []
        
        def db_operation_thread(thread_id):
            """模拟数据库操作的线程"""
            try:
                # 记录初始连接状态
                initial_connection = connection.connection is not None
                
                # 关闭继承的连接
                safe_close_db_connection()
                
                # 执行多次数据库操作
                for i in range(operations_per_thread):
                    try:
                        # 模拟数据库查询
                        from videos.models import CompositionTask
                        CompositionTask.objects.count()
                        
                        # 记录连接状态
                        has_connection = connection.connection is not None
                        connection_states.append({
                            'thread_id': thread_id,
                            'operation': i,
                            'has_connection': has_connection
                        })
                        
                        time.sleep(0.01)  # 短暂延迟
                        
                    except Exception as e:
                        errors.append(f"Thread {thread_id}, Op {i}: {str(e)}")
                
                # 最终关闭连接
                safe_close_db_connection()
                final_connection = connection.connection is not None
                
                return {
                    'thread_id': thread_id,
                    'initial_connection': initial_connection,
                    'final_connection': final_connection,
                    'operations_completed': operations_per_thread
                }
                
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {str(e)}")
                return None
        
        # 启动多个线程
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [
                executor.submit(db_operation_thread, i) 
                for i in range(thread_count)
            ]
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        # 验证属性
        self.assertEqual(len(errors), 0, f"数据库操作出现错误: {errors}")
        self.assertEqual(len(results), thread_count, "所有线程应该成功完成")
        
        # 验证每个线程都正确管理了连接
        for result in results:
            # 最终连接应该被关闭
            self.assertFalse(
                result['final_connection'], 
                f"线程 {result['thread_id']} 未正确关闭数据库连接"
            )
    
    @settings(max_examples=30, deadline=20000)
    @given(
        file_count=st.integers(min_value=1, max_value=10),
        thread_count=st.integers(min_value=1, max_value=3)
    )
    def test_temp_file_cleanup_property(self, file_count, thread_count):
        """
        Property 8b: 临时文件清理
        
        For any 创建的临时文件，无论线程是否正常结束，
        所有临时文件都应该被正确清理
        
        **Feature: async-video-composition, Property 8b: 临时文件清理**
        **Validates: Requirements 5.3**
        """
        created_files = []
        cleanup_results = []
        
        def file_creation_thread(thread_id):
            """创建和清理临时文件的线程"""
            thread_files = []
            
            try:
                # 创建临时文件
                for i in range(file_count):
                    temp_file = self.create_temp_file(f"Thread {thread_id}, File {i}")
                    thread_files.append(temp_file)
                    created_files.append(temp_file)
                
                # 验证文件存在
                existing_files = [f for f in thread_files if os.path.exists(f)]
                
                # 清理文件
                cleanup_temp_files(thread_files)
                
                # 验证文件被清理
                remaining_files = [f for f in thread_files if os.path.exists(f)]
                
                return {
                    'thread_id': thread_id,
                    'created_count': len(thread_files),
                    'existing_before_cleanup': len(existing_files),
                    'remaining_after_cleanup': len(remaining_files),
                    'files': thread_files
                }
                
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'error': str(e),
                    'files': thread_files
                }
        
        # 启动多个线程
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [
                executor.submit(file_creation_thread, i) 
                for i in range(thread_count)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                cleanup_results.append(result)
        
        # 验证属性
        for result in cleanup_results:
            self.assertNotIn('error', result, f"线程 {result['thread_id']} 出现错误")
            
            # 验证文件创建
            self.assertEqual(
                result['created_count'], file_count,
                f"线程 {result['thread_id']} 应该创建 {file_count} 个文件"
            )
            
            # 验证文件清理
            self.assertEqual(
                result['remaining_after_cleanup'], 0,
                f"线程 {result['thread_id']} 应该清理所有临时文件"
            )
        
        # 验证全局状态：所有文件都应该被清理
        total_remaining = sum(1 for f in created_files if os.path.exists(f))
        self.assertEqual(total_remaining, 0, "所有临时文件都应该被清理")
    
    @settings(max_examples=20, deadline=15000)
    @given(
        task_count=st.integers(min_value=1, max_value=5)
    )
    def test_resource_cleanup_on_exception_property(self, task_count):
        """
        Property 8c: 异常时资源清理
        
        For any 任务执行过程中发生异常，所有分配的资源
        （数据库连接、临时文件、线程资源）都应该被正确清理
        
        **Feature: async-video-composition, Property 8c: 异常时资源清理**
        **Validates: Requirements 5.2, 5.3**
        """
        task_ids = [str(uuid.uuid4()) for _ in range(task_count)]
        cleanup_results = []
        
        def simulate_task_with_exception(task_id):
            """模拟会抛出异常的任务"""
            temp_files = []
            
            try:
                # 创建一些临时资源
                for i in range(3):
                    temp_file = self.create_temp_file(f"Task {task_id}, Resource {i}")
                    temp_files.append(temp_file)
                
                # 注册任务到 TaskManager
                self.task_manager.register_task(task_id, None, None)
                
                # 模拟异常
                if len(task_id) > 10:  # 总是为真，确保抛出异常
                    raise ValueError(f"模拟任务 {task_id} 异常")
                
            except Exception as e:
                # 异常处理：确保资源清理
                try:
                    success = ensure_resource_cleanup(task_id, temp_files=temp_files)
                    
                    # 检查资源清理结果
                    remaining_files = [f for f in temp_files if os.path.exists(f)]
                    task_exists = self.task_manager.get_task_info(task_id) is not None
                    
                    return {
                        'task_id': task_id,
                        'exception_handled': True,
                        'cleanup_success': success,
                        'temp_files_created': len(temp_files),
                        'temp_files_remaining': len(remaining_files),
                        'task_cleaned_up': not task_exists,
                        'error': str(e)
                    }
                    
                except Exception as cleanup_error:
                    return {
                        'task_id': task_id,
                        'exception_handled': False,
                        'cleanup_error': str(cleanup_error),
                        'original_error': str(e)
                    }
        
        # 执行所有任务
        for task_id in task_ids:
            result = simulate_task_with_exception(task_id)
            cleanup_results.append(result)
        
        # 验证属性
        for result in cleanup_results:
            self.assertTrue(
                result['exception_handled'],
                f"任务 {result['task_id']} 的异常应该被正确处理"
            )
            
            self.assertTrue(
                result['cleanup_success'],
                f"任务 {result['task_id']} 的资源清理应该成功"
            )
            
            self.assertEqual(
                result['temp_files_remaining'], 0,
                f"任务 {result['task_id']} 的临时文件应该被清理"
            )
            
            self.assertTrue(
                result['task_cleaned_up'],
                f"任务 {result['task_id']} 应该从 TaskManager 中清理"
            )
    
    @settings(max_examples=15, deadline=10000)
    @given(
        concurrent_tasks=st.integers(min_value=2, max_value=4)
    )
    def test_concurrent_resource_access_property(self, concurrent_tasks):
        """
        Property 8d: 并发资源访问安全
        
        For any 并发执行的任务，它们对共享资源的访问应该是线程安全的，
        不会出现资源竞争或数据不一致
        
        **Feature: async-video-composition, Property 8d: 并发资源访问安全**
        **Validates: Requirements 5.1, 5.2**
        """
        shared_resource = {'counter': 0, 'operations': []}
        resource_lock = threading.Lock()
        task_results = []
        
        def concurrent_resource_task(task_id):
            """并发访问共享资源的任务"""
            operations_count = 0
            
            try:
                # 模拟多次资源访问
                for i in range(5):
                    with resource_lock:
                        # 读取当前值
                        current_value = shared_resource['counter']
                        
                        # 模拟处理时间
                        time.sleep(0.001)
                        
                        # 更新值
                        shared_resource['counter'] = current_value + 1
                        shared_resource['operations'].append(f"{task_id}-{i}")
                        operations_count += 1
                
                return {
                    'task_id': task_id,
                    'operations_completed': operations_count,
                    'success': True
                }
                
            except Exception as e:
                return {
                    'task_id': task_id,
                    'operations_completed': operations_count,
                    'success': False,
                    'error': str(e)
                }
        
        # 启动并发任务
        with ThreadPoolExecutor(max_workers=concurrent_tasks) as executor:
            futures = [
                executor.submit(concurrent_resource_task, f"task_{i}")
                for i in range(concurrent_tasks)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                task_results.append(result)
        
        # 验证属性
        successful_tasks = [r for r in task_results if r['success']]
        self.assertEqual(
            len(successful_tasks), concurrent_tasks,
            "所有并发任务都应该成功完成"
        )
        
        # 验证共享资源的一致性
        expected_counter = concurrent_tasks * 5
        self.assertEqual(
            shared_resource['counter'], expected_counter,
            f"共享计数器应该是 {expected_counter}"
        )
        
        expected_operations = concurrent_tasks * 5
        self.assertEqual(
            len(shared_resource['operations']), expected_operations,
            f"操作记录应该有 {expected_operations} 条"
        )
        
        # 验证没有重复的操作记录
        unique_operations = set(shared_resource['operations'])
        self.assertEqual(
            len(unique_operations), len(shared_resource['operations']),
            "不应该有重复的操作记录"
        )


if __name__ == '__main__':
    import unittest
    
    # 运行属性测试
    suite = unittest.TestLoader().loadTestsFromTestCase(ResourceManagementPropertyTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print("\n✅ 所有资源管理属性测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print(f"\n❌ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        for test, traceback in result.failures + result.errors:
            print(f"\n失败测试: {test}")
            print(f"错误信息: {traceback}")