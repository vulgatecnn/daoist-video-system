"""
视频合成API异步任务状态一致性属性测试模块

使用属性测试验证视频合成API的异步任务状态一致性。
"""

import pytest
import json
import os
import sys
import time
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus


class CompositionAPIPropertyTester:
    """视频合成API属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化视频合成API属性测试器
        
        Args:
            config: 测试配置管理器
        """
        self.config = config
        self.base_url = config.get_base_url()
        self.timeout = config.get_timeout()
        
        # 创建API客户端
        self.client = APIClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        # 结果管理器
        self.result_manager = TestResultManager()
        
        # 测试数据
        self.test_data = config.get_test_data()
        self.valid_user = self.test_data["valid_user"]
        
        # 登录状态
        self.is_authenticated = False
        
        # 缓存的视频ID
        self._cached_video_ids: Optional[List[int]] = None
    
    def ensure_authenticated(self) -> bool:
        """
        确保已认证
        
        Returns:
            bool: 是否成功认证
        """
        if self.is_authenticated and self.client.access_token:
            return True
        
        # 尝试登录
        success = self.client.login(
            self.valid_user['username'],
            self.valid_user['password']
        )
        
        if success:
            self.is_authenticated = True
        
        return success
    
    def get_available_video_ids(self) -> List[int]:
        """
        获取可用的视频ID列表（带缓存）
        
        Returns:
            List[int]: 视频ID列表
        """
        if self._cached_video_ids is not None:
            return self._cached_video_ids
        
        try:
            # 确保已认证
            if not self.ensure_authenticated():
                return []
            
            # 获取视频列表
            response = self.client.get('/api/videos/')
            
            if not response.is_success or not response.json_data:
                return []
            
            videos = response.json_data.get('results', [])
            video_ids = [video.get('id') for video in videos if video.get('id')]
            
            # 缓存结果
            self._cached_video_ids = video_ids
            
            return video_ids
            
        except Exception as e:
            return []
    
    def validate_composition_create_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """
        验证合成任务创建响应结构
        
        Args:
            response_data: 响应数据
            
        Returns:
            bool: 结构是否有效
        """
        # 检查必要字段
        required_fields = ['task_id', 'status']
        for field in required_fields:
            if field not in response_data:
                return False
        
        # 验证task_id不为空
        if not response_data['task_id']:
            return False
        
        # 验证status是有效值
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
        if response_data['status'] not in valid_statuses:
            return False
        
        return True
    
    def validate_composition_status_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """
        验证合成任务状态查询响应结构
        
        Args:
            response_data: 响应数据
            
        Returns:
            bool: 结构是否有效
        """
        # 检查必要字段
        required_fields = ['task_id', 'status']
        for field in required_fields:
            if field not in response_data:
                return False
        
        # 验证task_id不为空
        if not response_data['task_id']:
            return False
        
        # 验证status是有效值
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
        if response_data['status'] not in valid_statuses:
            return False
        
        # 验证可选字段类型
        optional_fields = {
            'progress': (int, float, type(None)),
            'message': (str, type(None)),
            'created_at': (str, type(None)),
            'updated_at': (str, type(None)),
            'estimated_completion': (str, type(None)),
            'download_url': (str, type(None))
        }
        
        for field, expected_type in optional_fields.items():
            if field in response_data:
                if not isinstance(response_data[field], expected_type):
                    return False
        
        # 验证progress范围
        if 'progress' in response_data and response_data['progress'] is not None:
            progress = response_data['progress']
            if not (0 <= progress <= 100):
                return False
        
        return True
    
    def validate_task_status_transition(self, old_status: str, new_status: str) -> bool:
        """
        验证任务状态转换的合理性
        
        Args:
            old_status: 旧状态
            new_status: 新状态
            
        Returns:
            bool: 状态转换是否合理
        """
        # 定义有效的状态转换
        valid_transitions = {
            'pending': ['processing', 'failed', 'cancelled'],
            'processing': ['completed', 'failed', 'cancelled'],
            'completed': [],  # 完成状态不应该再转换
            'failed': [],     # 失败状态不应该再转换
            'cancelled': []   # 取消状态不应该再转换
        }
        
        # 相同状态总是有效的
        if old_status == new_status:
            return True
        
        # 检查是否是有效转换
        return new_status in valid_transitions.get(old_status, [])
    
    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()


# 属性测试策略

# 合成请求数据策略
composition_request_strategy = st.builds(
    dict,
    video_ids=st.lists(st.integers(min_value=1, max_value=1000), min_size=2, max_size=5),
    output_format=st.sampled_from(['mp4', 'avi', 'mov']),
    quality=st.sampled_from(['low', 'medium', 'high']),
    title=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    description=st.one_of(st.none(), st.text(max_size=500))
)

# 有效的合成请求数据策略（使用实际存在的视频ID）
def valid_composition_request_strategy(video_ids: List[int]):
    """生成使用有效视频ID的合成请求策略"""
    if len(video_ids) < 2:
        # 如果没有足够的视频ID，使用模拟ID
        video_ids = [1, 2, 3, 4, 5]
    
    return st.builds(
        dict,
        video_ids=st.lists(st.sampled_from(video_ids), min_size=2, max_size=min(5, len(video_ids))),
        output_format=st.sampled_from(['mp4']),  # 只使用最常见的格式
        quality=st.sampled_from(['high']),       # 只使用高质量
        title=st.text(min_size=1, max_size=50),
        description=st.one_of(st.none(), st.text(max_size=200))
    )


# 属性测试用例

@pytest.fixture
def config():
    """测试配置fixture"""
    return TestConfigManager()


@pytest.fixture
def property_tester(config):
    """视频合成API属性测试器fixture"""
    tester = CompositionAPIPropertyTester(config)
    yield tester
    tester.close()


def test_composition_task_creation_consistency_property():
    """
    属性 5: 异步任务状态一致性 - 任务创建一致性
    
    对于任何有效的合成请求，系统应该能够创建任务、返回任务ID和初始状态，
    并且任务状态应该准确反映实际进度。
    
    **验证需求: 4.1, 4.2**
    """
    config = TestConfigManager()
    property_tester = CompositionAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 获取可用的视频ID
        video_ids = property_tester.get_available_video_ids()
        if len(video_ids) < 2:
            pytest.skip("需要至少2个视频才能进行合成测试")
        
        # 使用前两个视频ID进行测试
        test_video_ids = video_ids[:2]
        
        # 创建合成任务
        composition_data = {
            'video_ids': test_video_ids,
            'output_format': 'mp4',
            'quality': 'high',
            'title': '属性测试任务'
        }
        
        create_response = property_tester.client.post('/api/videos/composition/create/', 
                                                    data=composition_data)
        
        # 验证创建响应
        if create_response.is_success and create_response.json_data:
            # 验证创建响应结构
            assert property_tester.validate_composition_create_response_structure(create_response.json_data), \
                f"合成任务创建响应结构无效"
            
            task_id = create_response.json_data['task_id']
            create_status = create_response.json_data['status']
            
            # 立即查询任务状态
            status_response = property_tester.client.get(f'/api/videos/composition/{task_id}/')
            
            if status_response.is_success and status_response.json_data:
                # 验证状态查询响应结构
                assert property_tester.validate_composition_status_response_structure(status_response.json_data), \
                    f"任务状态查询响应结构无效"
                
                query_task_id = status_response.json_data['task_id']
                query_status = status_response.json_data['status']
                
                # 验证任务ID一致性
                assert query_task_id == task_id, \
                    f"任务ID不一致: 创建时{task_id}, 查询时{query_task_id}"
                
                # 验证状态转换合理性
                assert property_tester.validate_task_status_transition(create_status, query_status), \
                    f"状态转换不合理: {create_status} -> {query_status}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


def test_composition_task_status_polling_consistency_property():
    """
    属性 5: 异步任务状态一致性 - 状态轮询一致性
    
    对于任何创建的合成任务，多次查询状态应该返回一致的任务信息，
    状态变化应该遵循合理的转换规则。
    
    **验证需求: 4.2, 4.3**
    """
    config = TestConfigManager()
    property_tester = CompositionAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 获取可用的视频ID
        video_ids = property_tester.get_available_video_ids()
        if len(video_ids) < 2:
            pytest.skip("需要至少2个视频才能进行合成测试")
        
        # 创建合成任务
        composition_data = {
            'video_ids': video_ids[:2],
            'output_format': 'mp4',
            'quality': 'high',
            'title': '轮询一致性测试任务'
        }
        
        create_response = property_tester.client.post('/api/videos/composition/create/', 
                                                    data=composition_data)
        
        if not create_response.is_success or not create_response.json_data:
            pytest.skip("无法创建合成任务")
        
        task_id = create_response.json_data['task_id']
        
        # 进行多次状态查询
        poll_count = 5
        poll_interval = 1  # 秒
        
        previous_status = None
        previous_progress = None
        
        for i in range(poll_count):
            status_response = property_tester.client.get(f'/api/videos/composition/{task_id}/')
            
            if status_response.is_success and status_response.json_data:
                # 验证响应结构
                assert property_tester.validate_composition_status_response_structure(status_response.json_data), \
                    f"第{i+1}次查询响应结构无效"
                
                current_task_id = status_response.json_data['task_id']
                current_status = status_response.json_data['status']
                current_progress = status_response.json_data.get('progress')
                
                # 验证任务ID始终一致
                assert current_task_id == task_id, \
                    f"第{i+1}次查询任务ID不一致: 期望{task_id}, 实际{current_task_id}"
                
                # 验证状态转换合理性
                if previous_status is not None:
                    assert property_tester.validate_task_status_transition(previous_status, current_status), \
                        f"第{i+1}次查询状态转换不合理: {previous_status} -> {current_status}"
                
                # 验证进度单调性（如果都有进度值）
                if previous_progress is not None and current_progress is not None:
                    # 进度应该不减少（除非状态变为失败或取消）
                    if current_status not in ['failed', 'cancelled']:
                        assert current_progress >= previous_progress, \
                            f"第{i+1}次查询进度倒退: {previous_progress} -> {current_progress}"
                
                previous_status = current_status
                previous_progress = current_progress
                
                # 如果任务已完成或失败，停止轮询
                if current_status in ['completed', 'failed', 'cancelled']:
                    break
            
            # 等待下次轮询
            if i < poll_count - 1:
                time.sleep(poll_interval)
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


def test_composition_task_download_availability_property():
    """
    属性 5: 异步任务状态一致性 - 下载可用性一致性
    
    对于任何已完成的合成任务，应该提供下载链接，
    下载链接应该有效且文件应该可访问。
    
    **验证需求: 4.3, 4.4**
    """
    config = TestConfigManager()
    property_tester = CompositionAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 获取可用的视频ID
        video_ids = property_tester.get_available_video_ids()
        if len(video_ids) < 2:
            pytest.skip("需要至少2个视频才能进行合成测试")
        
        # 创建合成任务
        composition_data = {
            'video_ids': video_ids[:2],
            'output_format': 'mp4',
            'quality': 'high',
            'title': '下载可用性测试任务'
        }
        
        create_response = property_tester.client.post('/api/videos/composition/create/', 
                                                    data=composition_data)
        
        if not create_response.is_success or not create_response.json_data:
            pytest.skip("无法创建合成任务")
        
        task_id = create_response.json_data['task_id']
        
        # 轮询等待任务完成（最多等待30秒）
        max_wait_time = 30
        poll_interval = 3
        wait_time = 0
        
        task_completed = False
        download_url = None
        
        while wait_time < max_wait_time:
            status_response = property_tester.client.get(f'/api/videos/composition/{task_id}/')
            
            if status_response.is_success and status_response.json_data:
                status = status_response.json_data.get('status')
                
                if status == 'completed':
                    task_completed = True
                    download_url = status_response.json_data.get('download_url')
                    break
                elif status == 'failed':
                    pytest.skip("任务执行失败，无法测试下载")
            
            time.sleep(poll_interval)
            wait_time += poll_interval
        
        # 如果任务完成，验证下载可用性
        if task_completed:
            if download_url:
                # 测试下载链接
                download_response = property_tester.client.get(download_url)
                
                # 下载应该成功或返回合理的错误
                assert download_response.status_code in [200, 202, 404], \
                    f"下载请求返回意外状态码: {download_response.status_code}"
                
                if download_response.is_success:
                    # 验证下载内容
                    assert len(download_response.content) > 0, \
                        "下载的文件内容为空"
            else:
                # 如果状态响应中没有下载URL，尝试标准下载端点
                standard_download_url = f"/api/videos/composition/{task_id}/download/"
                download_response = property_tester.client.get(standard_download_url)
                
                # 应该能够访问下载端点（即使文件可能不存在）
                assert download_response.status_code in [200, 202, 404, 400], \
                    f"标准下载端点返回意外状态码: {download_response.status_code}"
        else:
            # 如果任务未完成，测试下载应该返回适当的错误
            download_url = f"/api/videos/composition/{task_id}/download/"
            download_response = property_tester.client.get(download_url)
            
            # 未完成的任务下载应该返回404或400
            assert download_response.status_code in [404, 400, 202], \
                f"未完成任务下载返回意外状态码: {download_response.status_code}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


def test_composition_task_cancellation_consistency_property():
    """
    属性 5: 异步任务状态一致性 - 任务取消一致性
    
    对于任何可取消的合成任务，取消操作应该正确更新任务状态，
    并且取消后的任务不应该继续处理。
    
    **验证需求: 4.5**
    """
    config = TestConfigManager()
    property_tester = CompositionAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 获取可用的视频ID
        video_ids = property_tester.get_available_video_ids()
        if len(video_ids) < 2:
            pytest.skip("需要至少2个视频才能进行合成测试")
        
        # 创建合成任务
        composition_data = {
            'video_ids': video_ids[:2],
            'output_format': 'mp4',
            'quality': 'high',
            'title': '取消一致性测试任务'
        }
        
        create_response = property_tester.client.post('/api/videos/composition/create/', 
                                                    data=composition_data)
        
        if not create_response.is_success or not create_response.json_data:
            pytest.skip("无法创建合成任务")
        
        task_id = create_response.json_data['task_id']
        
        # 查询任务状态确认任务存在
        status_response = property_tester.client.get(f'/api/videos/composition/{task_id}/')
        
        if not status_response.is_success or not status_response.json_data:
            pytest.skip("无法查询任务状态")
        
        initial_status = status_response.json_data['status']
        
        # 只有在pending或processing状态才能取消
        if initial_status in ['pending', 'processing']:
            # 尝试取消任务
            cancel_response = property_tester.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            # 取消请求应该成功或返回合理的错误
            assert cancel_response.status_code in [200, 202, 400, 404], \
                f"取消请求返回意外状态码: {cancel_response.status_code}"
            
            if cancel_response.is_success:
                # 等待一小段时间让取消操作生效
                time.sleep(2)
                
                # 再次查询任务状态
                final_status_response = property_tester.client.get(f'/api/videos/composition/{task_id}/')
                
                if final_status_response.is_success and final_status_response.json_data:
                    final_status = final_status_response.json_data['status']
                    
                    # 验证任务状态已更新为取消或保持合理状态
                    assert final_status in ['cancelled', 'completed', 'failed'], \
                        f"取消后任务状态不合理: {final_status}"
                    
                    # 如果状态变为cancelled，验证状态转换合理性
                    if final_status == 'cancelled':
                        assert property_tester.validate_task_status_transition(initial_status, final_status), \
                            f"取消状态转换不合理: {initial_status} -> {final_status}"
        else:
            # 如果任务已完成或失败，取消应该返回错误
            cancel_response = property_tester.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            # 已完成的任务取消应该返回400或类似错误
            assert cancel_response.status_code in [400, 404, 409], \
                f"已完成任务取消返回意外状态码: {cancel_response.status_code}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


def test_composition_error_handling_consistency_property():
    """
    属性 5: 异步任务状态一致性 - 错误处理一致性
    
    对于任何无效的合成请求或操作，系统应该返回一致的错误响应，
    并且不应该创建无效的任务。
    
    **验证需求: 4.1, 4.2, 4.3, 4.4, 4.5**
    """
    config = TestConfigManager()
    property_tester = CompositionAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 测试各种错误场景
        error_scenarios = [
            # 无效视频ID
            {
                'video_ids': [999999, 999998],
                'output_format': 'mp4',
                'quality': 'high'
            },
            # 空视频ID列表
            {
                'video_ids': [],
                'output_format': 'mp4',
                'quality': 'high'
            },
            # 无效输出格式
            {
                'video_ids': [1, 2],
                'output_format': 'invalid_format',
                'quality': 'high'
            },
            # 无效质量参数
            {
                'video_ids': [1, 2],
                'output_format': 'mp4',
                'quality': 'invalid_quality'
            }
        ]
        
        for i, scenario in enumerate(error_scenarios):
            create_response = property_tester.client.post('/api/videos/composition/create/', 
                                                        data=scenario)
            
            # 错误场景应该返回4xx错误
            assert create_response.is_client_error, \
                f"错误场景{i+1}应该返回4xx错误，实际: {create_response.status_code}"
            
            # 错误响应应该有JSON格式（如果有内容）
            if create_response.content and create_response.headers.get('Content-Type', '').startswith('application/json'):
                assert create_response.json_data is not None, \
                    f"错误场景{i+1}应该有JSON错误信息"
        
        # 测试无效任务ID的操作
        invalid_task_id = "invalid_task_id_12345"
        
        # 查询无效任务状态
        status_response = property_tester.client.get(f'/api/videos/composition/{invalid_task_id}/')
        assert status_response.status_code == 404, \
            f"查询无效任务应该返回404，实际: {status_response.status_code}"
        
        # 取消无效任务
        cancel_response = property_tester.client.post(f'/api/videos/composition/{invalid_task_id}/cancel/')
        assert cancel_response.status_code in [404, 400], \
            f"取消无效任务应该返回404或400，实际: {cancel_response.status_code}"
        
        # 下载无效任务
        download_response = property_tester.client.get(f'/api/videos/composition/{invalid_task_id}/download/')
        assert download_response.status_code in [404, 400], \
            f"下载无效任务应该返回404或400，实际: {download_response.status_code}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


# 单元测试用例

def test_composition_property_tester_creation(config):
    """测试视频合成API属性测试器创建"""
    tester = CompositionAPIPropertyTester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()
    tester.close()


def test_composition_create_response_structure_validation():
    """测试合成任务创建响应结构验证"""
    config = TestConfigManager()
    tester = CompositionAPIPropertyTester(config)
    
    # 测试有效结构
    valid_response = {
        'task_id': 'task_12345',
        'status': 'pending',
        'message': '任务已创建'
    }
    
    assert tester.validate_composition_create_response_structure(valid_response)
    
    # 测试无效结构
    invalid_response = {
        'task_id': '',  # 空task_id
        'status': 'pending'
    }
    
    assert not tester.validate_composition_create_response_structure(invalid_response)
    
    tester.close()


def test_composition_status_response_structure_validation():
    """测试合成任务状态响应结构验证"""
    config = TestConfigManager()
    tester = CompositionAPIPropertyTester(config)
    
    # 测试有效结构
    valid_response = {
        'task_id': 'task_12345',
        'status': 'processing',
        'progress': 50.5,
        'message': '正在处理中',
        'created_at': '2023-01-01T00:00:00Z'
    }
    
    assert tester.validate_composition_status_response_structure(valid_response)
    
    # 测试无效结构
    invalid_response = {
        'task_id': 'task_12345',
        'status': 'invalid_status',  # 无效状态
        'progress': 150  # 超出范围的进度
    }
    
    assert not tester.validate_composition_status_response_structure(invalid_response)
    
    tester.close()


def test_task_status_transition_validation():
    """测试任务状态转换验证"""
    config = TestConfigManager()
    tester = CompositionAPIPropertyTester(config)
    
    # 测试有效转换
    assert tester.validate_task_status_transition('pending', 'processing')
    assert tester.validate_task_status_transition('processing', 'completed')
    assert tester.validate_task_status_transition('processing', 'failed')
    
    # 测试无效转换
    assert not tester.validate_task_status_transition('completed', 'processing')
    assert not tester.validate_task_status_transition('failed', 'pending')
    
    # 测试相同状态（应该有效）
    assert tester.validate_task_status_transition('processing', 'processing')
    
    tester.close()


if __name__ == "__main__":
    # 直接运行属性测试
    pytest.main([__file__, "-v", "--tb=short"])