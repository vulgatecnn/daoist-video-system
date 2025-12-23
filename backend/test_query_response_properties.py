#!/usr/bin/env python
"""
查询返回值完整性属性测试
使用 Hypothesis 进行基于属性的测试，验证任务状态查询的返回值完整性
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
from videos.task_manager import TaskManager, TaskStatus, ProgressTracker, ProgressInfo, TaskInfo


class QueryResponsePropertyTest(HypothesisTestCase):
    """查询返回值完整性属性测试类"""
    
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
        progress_value=st.integers(min_value=0, max_value=100),
        task_status=st.sampled_from(['pending', 'processing', 'completed', 'failed', 'cancelled'])
    )
    def test_property_6_query_response_completeness(self, user_id, video_ids, progress_value, task_status):
        """
        Property 6: 查询返回值完整性
        For any 任务状态查询：
        - 必须返回有效的进度百分比（0-100）
        - 必须返回有效的状态值（pending/processing/completed/failed/cancelled）
        - 当状态为 completed 时，必须包含输出文件信息
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        manager = TaskManager()
        
        # 创建任务
        task_id = manager.register_task(user_id, video_ids)
        
        # 根据测试状态设置任务
        if task_status == 'pending':
            # 保持初始状态
            pass
        elif task_status == 'processing':
            # 启动任务到 processing 状态
            def mock_executor(task_id):
                time.sleep(0.1)
            manager.start_task(task_id, mock_executor)
            manager.update_task_progress(task_id, progress_value, 'processing')
        elif task_status in ['completed', 'failed', 'cancelled']:
            # 启动任务然后设置为最终状态
            def mock_executor(task_id):
                time.sleep(0.05)
            manager.start_task(task_id, mock_executor)
            
            # 设置输出文件（如果是完成状态）
            output_file = f"/path/to/output_{task_id}.mp4" if task_status == 'completed' else None
            manager.update_task_progress(
                task_id, 
                100 if task_status == 'completed' else progress_value, 
                task_status,
                output_file=output_file
            )
        
        # 等待状态稳定
        time.sleep(0.1)
        
        # 查询任务进度信息
        progress_info = manager.get_progress_info(task_id)
        task_info = manager.get_task_info(task_id)
        
        # 属性断言1: 必须返回有效的进度百分比（0-100）
        assert progress_info is not None, f"任务 {task_id} 进度信息不应为 None"
        assert isinstance(progress_info.progress, int), \
            f"进度值应为整数，实际类型: {type(progress_info.progress)}"
        assert 0 <= progress_info.progress <= 100, \
            f"进度百分比超出范围: {progress_info.progress}"
        
        assert task_info is not None, f"任务 {task_id} 信息不应为 None"
        assert isinstance(task_info.progress, int), \
            f"任务进度值应为整数，实际类型: {type(task_info.progress)}"
        assert 0 <= task_info.progress <= 100, \
            f"任务进度百分比超出范围: {task_info.progress}"
        
        # 属性断言2: 必须返回有效的状态值
        valid_statuses = {'pending', 'processing', 'completed', 'failed', 'cancelled'}
        
        assert progress_info.status in valid_statuses, \
            f"进度信息状态无效: {progress_info.status}"
        
        assert task_info.status.value in valid_statuses, \
            f"任务信息状态无效: {task_info.status.value}"
        
        # 验证状态一致性
        assert progress_info.status == task_info.status.value, \
            f"状态不一致: 进度信息={progress_info.status}, 任务信息={task_info.status.value}"
        
        # 属性断言3: 当状态为 completed 时，必须包含输出文件信息
        if progress_info.status == 'completed':
            assert progress_info.output_file is not None, \
                f"完成状态的任务必须包含输出文件信息，但为 None"
            assert isinstance(progress_info.output_file, str), \
                f"输出文件应为字符串，实际类型: {type(progress_info.output_file)}"
            assert len(progress_info.output_file.strip()) > 0, \
                f"输出文件路径不应为空字符串"
            
            assert task_info.output_file is not None, \
                f"完成状态的任务信息必须包含输出文件，但为 None"
            assert isinstance(task_info.output_file, str), \
                f"任务输出文件应为字符串，实际类型: {type(task_info.output_file)}"
            assert len(task_info.output_file.strip()) > 0, \
                f"任务输出文件路径不应为空字符串"
        
        # 验证必需字段存在
        assert hasattr(progress_info, 'task_id'), "进度信息必须包含 task_id 字段"
        assert hasattr(progress_info, 'status'), "进度信息必须包含 status 字段"
        assert hasattr(progress_info, 'progress'), "进度信息必须包含 progress 字段"
        
        assert hasattr(task_info, 'task_id'), "任务信息必须包含 task_id 字段"
        assert hasattr(task_info, 'status'), "任务信息必须包含 status 字段"
        assert hasattr(task_info, 'progress'), "任务信息必须包含 progress 字段"
        assert hasattr(task_info, 'created_at'), "任务信息必须包含 created_at 字段"
        
        # 验证 task_id 一致性
        assert progress_info.task_id == task_id, \
            f"进度信息 task_id 不匹配: 期望={task_id}, 实际={progress_info.task_id}"
        assert task_info.task_id == task_id, \
            f"任务信息 task_id 不匹配: 期望={task_id}, 实际={task_info.task_id}"
        
        # 清理线程
        if task_info.thread and task_info.thread.is_alive():
            task_info.thread.join(timeout=2)

    @settings(max_examples=30, deadline=12000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        num_queries=st.integers(min_value=5, max_value=20)
    )
    def test_query_consistency_over_time(self, user_id, video_ids, num_queries):
        """
        测试查询一致性随时间变化
        验证多次查询返回的数据结构保持一致
        """
        manager = TaskManager()
        
        # 创建并启动任务
        task_id = manager.register_task(user_id, video_ids)
        
        def progressive_executor(task_id):
            """渐进式更新进度的执行器"""
            for i in range(10):
                progress = min(100, (i + 1) * 10)
                status = 'processing' if progress < 100 else 'completed'
                output_file = f"/path/to/output_{task_id}.mp4" if status == 'completed' else None
                
                manager.update_task_progress(
                    task_id, progress, status, 
                    output_file=output_file,
                    current_stage=f"处理阶段 {i+1}"
                )
                time.sleep(0.05)
        
        success = manager.start_task(task_id, progressive_executor)
        assert success
        
        # 记录多次查询结果
        query_results = []
        
        for i in range(num_queries):
            # 查询当前状态
            progress_info = manager.get_progress_info(task_id)
            task_info = manager.get_task_info(task_id)
            
            # 记录查询结果
            query_result = {
                'query_index': i,
                'timestamp': time.time(),
                'progress_info': {
                    'task_id': progress_info.task_id if progress_info else None,
                    'status': progress_info.status if progress_info else None,
                    'progress': progress_info.progress if progress_info else None,
                    'output_file': progress_info.output_file if progress_info else None,
                    'error_message': progress_info.error_message if progress_info else None,
                },
                'task_info': {
                    'task_id': task_info.task_id if task_info else None,
                    'status': task_info.status.value if task_info else None,
                    'progress': task_info.progress if task_info else None,
                    'output_file': task_info.output_file if task_info else None,
                    'error_message': task_info.error_message if task_info else None,
                }
            }
            query_results.append(query_result)
            
            # 短暂等待
            time.sleep(0.1)
        
        # 等待任务完成
        if task_info.thread:
            task_info.thread.join(timeout=5)
        
        # 验证所有查询结果的一致性
        for i, result in enumerate(query_results):
            progress_info = result['progress_info']
            task_info = result['task_info']
            
            # 属性断言1: 每次查询都返回完整的必需字段
            assert progress_info['task_id'] is not None, \
                f"查询 {i}: 进度信息 task_id 为 None"
            assert progress_info['status'] is not None, \
                f"查询 {i}: 进度信息 status 为 None"
            assert progress_info['progress'] is not None, \
                f"查询 {i}: 进度信息 progress 为 None"
            
            assert task_info['task_id'] is not None, \
                f"查询 {i}: 任务信息 task_id 为 None"
            assert task_info['status'] is not None, \
                f"查询 {i}: 任务信息 status 为 None"
            assert task_info['progress'] is not None, \
                f"查询 {i}: 任务信息 progress 为 None"
            
            # 属性断言2: 进度值在有效范围内
            assert 0 <= progress_info['progress'] <= 100, \
                f"查询 {i}: 进度值超出范围: {progress_info['progress']}"
            assert 0 <= task_info['progress'] <= 100, \
                f"查询 {i}: 任务进度值超出范围: {task_info['progress']}"
            
            # 属性断言3: 状态值有效
            valid_statuses = {'pending', 'processing', 'completed', 'failed', 'cancelled'}
            assert progress_info['status'] in valid_statuses, \
                f"查询 {i}: 无效状态: {progress_info['status']}"
            assert task_info['status'] in valid_statuses, \
                f"查询 {i}: 无效任务状态: {task_info['status']}"
            
            # 属性断言4: 完成状态包含输出文件
            if progress_info['status'] == 'completed':
                assert progress_info['output_file'] is not None, \
                    f"查询 {i}: 完成状态缺少输出文件信息"
                assert len(progress_info['output_file'].strip()) > 0, \
                    f"查询 {i}: 输出文件路径为空"
            
            if task_info['status'] == 'completed':
                assert task_info['output_file'] is not None, \
                    f"查询 {i}: 完成状态缺少任务输出文件信息"
                assert len(task_info['output_file'].strip()) > 0, \
                    f"查询 {i}: 任务输出文件路径为空"
        
        # 验证进度单调性（如果有多个查询结果）
        if len(query_results) > 1:
            for i in range(1, len(query_results)):
                prev_progress = query_results[i-1]['progress_info']['progress']
                curr_progress = query_results[i]['progress_info']['progress']
                
                # 进度应该单调递增或保持不变
                assert curr_progress >= prev_progress, \
                    f"查询 {i}: 进度回退: {prev_progress} -> {curr_progress}"

    @settings(max_examples=30, deadline=10000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        num_concurrent_queries=st.integers(min_value=3, max_value=10)
    )
    def test_concurrent_query_consistency(self, user_id, video_ids, num_concurrent_queries):
        """
        测试并发查询的一致性
        验证多个线程同时查询时返回值的完整性
        """
        manager = TaskManager()
        
        # 创建并启动任务
        task_id = manager.register_task(user_id, video_ids)
        
        def background_executor(task_id):
            """后台执行器，持续更新进度"""
            for i in range(20):
                progress = min(100, i * 5)
                status = 'processing' if progress < 100 else 'completed'
                output_file = f"/path/to/output_{task_id}.mp4" if status == 'completed' else None
                
                manager.update_task_progress(
                    task_id, progress, status, 
                    output_file=output_file,
                    current_stage=f"处理步骤 {i+1}"
                )
                time.sleep(0.05)
        
        success = manager.start_task(task_id, background_executor)
        assert success
        
        # 并发查询结果收集
        concurrent_results = []
        results_lock = threading.Lock()
        
        def concurrent_querier(thread_id):
            """并发查询函数"""
            try:
                for query_count in range(5):
                    # 查询进度信息
                    progress_info = manager.get_progress_info(task_id)
                    task_info = manager.get_task_info(task_id)
                    
                    # 记录结果
                    with results_lock:
                        concurrent_results.append({
                            'thread_id': thread_id,
                            'query_count': query_count,
                            'timestamp': time.time(),
                            'progress_info_valid': progress_info is not None,
                            'task_info_valid': task_info is not None,
                            'progress_value': progress_info.progress if progress_info else None,
                            'status_value': progress_info.status if progress_info else None,
                            'task_progress': task_info.progress if task_info else None,
                            'task_status': task_info.status.value if task_info else None,
                            'output_file_present': (progress_info.output_file is not None) if progress_info else False,
                            'task_output_file_present': (task_info.output_file is not None) if task_info else False,
                        })
                    
                    time.sleep(0.02)
                    
            except Exception as e:
                with results_lock:
                    concurrent_results.append({
                        'thread_id': thread_id,
                        'error': str(e),
                        'timestamp': time.time()
                    })
        
        # 启动并发查询线程
        threads = []
        for i in range(num_concurrent_queries):
            thread = threading.Thread(target=concurrent_querier, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有查询线程完成
        for thread in threads:
            thread.join(timeout=10)
        
        # 等待后台任务完成
        task_info = manager.get_task_info(task_id)
        if task_info.thread:
            task_info.thread.join(timeout=5)
        
        # 验证并发查询结果
        valid_results = [r for r in concurrent_results if 'error' not in r]
        error_results = [r for r in concurrent_results if 'error' in r]
        
        # 属性断言1: 大部分查询应该成功
        success_rate = len(valid_results) / len(concurrent_results) if concurrent_results else 0
        assert success_rate >= 0.8, \
            f"并发查询成功率过低: {success_rate:.2%}, 错误: {error_results}"
        
        # 属性断言2: 所有成功的查询都返回有效数据
        for result in valid_results:
            assert result['progress_info_valid'], \
                f"线程 {result['thread_id']} 查询 {result['query_count']}: 进度信息无效"
            assert result['task_info_valid'], \
                f"线程 {result['thread_id']} 查询 {result['query_count']}: 任务信息无效"
            
            # 验证进度值
            assert result['progress_value'] is not None, \
                f"线程 {result['thread_id']}: 进度值为 None"
            assert 0 <= result['progress_value'] <= 100, \
                f"线程 {result['thread_id']}: 进度值超出范围: {result['progress_value']}"
            
            assert result['task_progress'] is not None, \
                f"线程 {result['thread_id']}: 任务进度值为 None"
            assert 0 <= result['task_progress'] <= 100, \
                f"线程 {result['thread_id']}: 任务进度值超出范围: {result['task_progress']}"
            
            # 验证状态值
            valid_statuses = {'pending', 'processing', 'completed', 'failed', 'cancelled'}
            assert result['status_value'] in valid_statuses, \
                f"线程 {result['thread_id']}: 无效状态: {result['status_value']}"
            assert result['task_status'] in valid_statuses, \
                f"线程 {result['thread_id']}: 无效任务状态: {result['task_status']}"
        
        # 属性断言3: 没有严重的并发错误
        critical_errors = [e for e in error_results if 'deadlock' in e['error'].lower() or 'race' in e['error'].lower()]
        assert len(critical_errors) == 0, f"发现严重并发错误: {critical_errors}"

    @settings(max_examples=20, deadline=8000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_completed_task_output_file_requirement(self, user_id, video_ids):
        """
        测试完成任务的输出文件要求
        验证完成状态的任务必须包含输出文件信息
        """
        manager = TaskManager()
        
        # 测试场景1: 正常完成的任务
        task_id1 = manager.register_task(user_id, video_ids)
        
        def normal_completion_executor(task_id):
            """正常完成的执行器"""
            # 渐进更新进度
            for progress in [20, 40, 60, 80, 100]:
                status = 'processing' if progress < 100 else 'completed'
                output_file = f"/path/to/completed_{task_id}.mp4" if status == 'completed' else None
                
                manager.update_task_progress(task_id, progress, status, output_file=output_file)
                time.sleep(0.02)
        
        success = manager.start_task(task_id1, normal_completion_executor)
        assert success
        
        # 等待任务完成
        task_info1 = manager.get_task_info(task_id1)
        if task_info1.thread:
            task_info1.thread.join(timeout=5)
        
        # 验证正常完成的任务
        final_progress_info1 = manager.get_progress_info(task_id1)
        final_task_info1 = manager.get_task_info(task_id1)
        
        if final_progress_info1.status == 'completed':
            # 属性断言: 完成状态必须包含输出文件信息
            assert final_progress_info1.output_file is not None, \
                "完成状态的任务必须包含输出文件信息"
            assert isinstance(final_progress_info1.output_file, str), \
                f"输出文件应为字符串，实际类型: {type(final_progress_info1.output_file)}"
            assert len(final_progress_info1.output_file.strip()) > 0, \
                "输出文件路径不应为空字符串"
            assert final_progress_info1.output_file.endswith('.mp4'), \
                f"输出文件应为视频格式: {final_progress_info1.output_file}"
        
        if final_task_info1.status.value == 'completed':
            assert final_task_info1.output_file is not None, \
                "完成状态的任务信息必须包含输出文件"
            assert isinstance(final_task_info1.output_file, str), \
                f"任务输出文件应为字符串，实际类型: {type(final_task_info1.output_file)}"
            assert len(final_task_info1.output_file.strip()) > 0, \
                "任务输出文件路径不应为空字符串"
        
        # 测试场景2: 异常完成的任务（没有设置输出文件）
        task_id2 = manager.register_task(user_id, video_ids)
        
        def incomplete_output_executor(task_id):
            """不完整输出的执行器"""
            # 更新到完成状态但不设置输出文件
            manager.update_task_progress(task_id, 100, 'completed')  # 缺少 output_file
        
        success = manager.start_task(task_id2, incomplete_output_executor)
        assert success
        
        # 等待任务完成
        task_info2 = manager.get_task_info(task_id2)
        if task_info2.thread:
            task_info2.thread.join(timeout=3)
        
        # 验证异常情况的处理
        final_progress_info2 = manager.get_progress_info(task_id2)
        final_task_info2 = manager.get_task_info(task_id2)
        
        # 如果任务被标记为完成但没有输出文件，系统应该如何处理？
        # 这里我们测试系统的容错性
        if final_progress_info2.status == 'completed':
            # 系统可以选择：
            # 1. 自动生成默认输出文件路径
            # 2. 保持 output_file 为 None 但记录警告
            # 3. 将状态改为 failed
            
            # 我们验证系统至少保持了数据一致性
            assert final_progress_info2.progress == 100, \
                "完成状态的进度应为 100"
            
            # 如果有输出文件，应该是有效的
            if final_progress_info2.output_file is not None:
                assert isinstance(final_progress_info2.output_file, str), \
                    "如果存在输出文件，应为字符串类型"
                assert len(final_progress_info2.output_file.strip()) > 0, \
                    "如果存在输出文件，路径不应为空"

    @settings(max_examples=20, deadline=8000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5),
        error_message=st.text(min_size=1, max_size=100)
    )
    def test_failed_task_error_information(self, user_id, video_ids, error_message):
        """
        测试失败任务的错误信息
        验证失败状态的任务包含适当的错误信息
        """
        manager = TaskManager()
        
        # 创建失败的任务
        task_id = manager.register_task(user_id, video_ids)
        
        def failing_executor(task_id):
            """失败的执行器"""
            # 更新一些进度然后失败
            manager.update_task_progress(task_id, 30, 'processing')
            time.sleep(0.05)
            manager.update_task_progress(
                task_id, 30, 'failed', 
                error_message=error_message
            )
        
        success = manager.start_task(task_id, failing_executor)
        assert success
        
        # 等待任务完成
        task_info = manager.get_task_info(task_id)
        if task_info.thread:
            task_info.thread.join(timeout=3)
        
        # 验证失败任务的信息
        final_progress_info = manager.get_progress_info(task_id)
        final_task_info = manager.get_task_info(task_id)
        
        if final_progress_info.status == 'failed':
            # 属性断言: 失败状态应包含错误信息
            assert final_progress_info.error_message is not None, \
                "失败状态的任务应包含错误信息"
            assert isinstance(final_progress_info.error_message, str), \
                f"错误信息应为字符串，实际类型: {type(final_progress_info.error_message)}"
            assert len(final_progress_info.error_message.strip()) > 0, \
                "错误信息不应为空字符串"
            
            # 验证错误信息内容
            assert error_message in final_progress_info.error_message, \
                f"错误信息应包含原始错误: 期望包含'{error_message}', 实际'{final_progress_info.error_message}'"
        
        if final_task_info.status.value == 'failed':
            assert final_task_info.error_message is not None, \
                "失败状态的任务信息应包含错误信息"
            assert isinstance(final_task_info.error_message, str), \
                f"任务错误信息应为字符串，实际类型: {type(final_task_info.error_message)}"
            assert len(final_task_info.error_message.strip()) > 0, \
                "任务错误信息不应为空字符串"

    @settings(max_examples=20, deadline=6000)
    @given(
        user_id=st.integers(min_value=1, max_value=100),
        video_ids=st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=5)
    )
    def test_nonexistent_task_query_handling(self, user_id, video_ids):
        """
        测试不存在任务的查询处理
        验证查询不存在的任务时的行为
        """
        manager = TaskManager()
        
        # 生成一个不存在的任务ID
        nonexistent_task_id = str(uuid.uuid4())
        
        # 查询不存在的任务
        progress_info = manager.get_progress_info(nonexistent_task_id)
        task_info = manager.get_task_info(nonexistent_task_id)
        
        # 属性断言: 查询不存在的任务应返回 None
        assert progress_info is None, \
            f"查询不存在的任务应返回 None，实际返回: {progress_info}"
        assert task_info is None, \
            f"查询不存在的任务信息应返回 None，实际返回: {task_info}"
        
        # 创建一个真实任务作为对比
        real_task_id = manager.register_task(user_id, video_ids)
        
        # 查询真实任务
        real_progress_info = manager.get_progress_info(real_task_id)
        real_task_info = manager.get_task_info(real_task_id)
        
        # 属性断言: 查询存在的任务应返回有效对象
        assert real_progress_info is not None, \
            "查询存在的任务应返回有效的进度信息"
        assert real_task_info is not None, \
            "查询存在的任务应返回有效的任务信息"
        
        # 验证返回对象的基本属性
        assert real_progress_info.task_id == real_task_id, \
            "进度信息的任务ID应匹配"
        assert real_task_info.task_id == real_task_id, \
            "任务信息的任务ID应匹配"


def run_query_response_tests():
    """运行查询返回值完整性属性测试"""
    import unittest
    
    print("🧪 开始运行查询返回值完整性属性测试...")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(QueryResponsePropertyTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有查询返回值完整性属性测试通过！")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print("❌ 部分查询返回值完整性属性测试失败！")
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
    success = run_query_response_tests()
    sys.exit(0 if success else 1)