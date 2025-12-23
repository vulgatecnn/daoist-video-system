"""
视频API响应完整性属性测试模块

使用属性测试验证视频API响应的完整性和一致性。
"""

import pytest
import json
import os
import sys
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus


class VideoAPIPropertyTester:
    """视频API属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化视频API属性测试器
        
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
    
    def validate_video_list_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """
        验证视频列表响应结构
        
        Args:
            response_data: 响应数据
            
        Returns:
            bool: 结构是否有效
        """
        # 检查必要的分页字段
        required_fields = ['count', 'results']
        for field in required_fields:
            if field not in response_data:
                return False
        
        # 验证count是整数
        if not isinstance(response_data['count'], int):
            return False
        
        # 验证results是列表
        if not isinstance(response_data['results'], list):
            return False
        
        # 验证每个视频对象的结构
        for video in response_data['results']:
            if not self.validate_video_object_structure(video):
                return False
        
        return True
    
    def validate_video_object_structure(self, video_data: Dict[str, Any]) -> bool:
        """
        验证视频对象结构
        
        Args:
            video_data: 视频数据
            
        Returns:
            bool: 结构是否有效
        """
        # 检查必要字段
        required_fields = ['id', 'title', 'file']
        for field in required_fields:
            if field not in video_data:
                return False
        
        # 验证字段类型
        if not isinstance(video_data['id'], int):
            return False
        
        if not isinstance(video_data['title'], str):
            return False
        
        if not isinstance(video_data['file'], str):
            return False
        
        # 验证可选字段类型
        optional_fields = {
            'description': (str, type(None)),
            'category': (str, type(None)),
            'created_at': str,
            'updated_at': str,
            'duration': (int, float, type(None)),
            'file_size': (int, type(None))
        }
        
        for field, expected_type in optional_fields.items():
            if field in video_data:
                if not isinstance(video_data[field], expected_type):
                    return False
        
        return True
    
    def validate_video_detail_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """
        验证视频详情响应结构
        
        Args:
            response_data: 响应数据
            
        Returns:
            bool: 结构是否有效
        """
        # 视频详情应该包含更多信息
        return self.validate_video_object_structure(response_data)
    
    def validate_upload_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """
        验证上传响应结构
        
        Args:
            response_data: 响应数据
            
        Returns:
            bool: 结构是否有效
        """
        # 上传响应应该包含ID或消息
        if 'id' not in response_data and 'message' not in response_data:
            return False
        
        # 如果有ID，应该是整数
        if 'id' in response_data and not isinstance(response_data['id'], int):
            return False
        
        # 如果有消息，应该是字符串
        if 'message' in response_data and not isinstance(response_data['message'], str):
            return False
        
        return True
    
    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()


# 属性测试策略

# 分页参数策略
pagination_params_strategy = st.builds(
    dict,
    page=st.integers(min_value=1, max_value=10),
    page_size=st.integers(min_value=1, max_value=50)
)

# 搜索参数策略
search_params_strategy = st.builds(
    dict,
    search=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))
)

# 视频上传数据策略
video_upload_data_strategy = st.builds(
    dict,
    title=st.text(min_size=1, max_size=100),
    description=st.one_of(st.none(), st.text(max_size=500)),
    category=st.sampled_from(['道德经', '庄子', '太极', '养生', None])
)


# 属性测试用例

@pytest.fixture
def config():
    """测试配置fixture"""
    return TestConfigManager()


@pytest.fixture
def property_tester(config):
    """视频API属性测试器fixture"""
    tester = VideoAPIPropertyTester(config)
    yield tester
    tester.close()


@given(pagination_params_strategy)
@settings(max_examples=10, deadline=30000)
def test_video_list_pagination_consistency_property(pagination_params):
    """
    属性 4: 视频API响应完整性 - 分页一致性
    
    对于任何有效的分页参数，视频列表API应该返回符合预期格式的响应数据，
    包括正确的分页信息和一致的视频对象结构。
    
    **验证需求: 3.1, 3.2**
    """
    config = TestConfigManager()
    property_tester = VideoAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 发送分页请求
        response = property_tester.client.get('/api/videos/', params=pagination_params)
        
        # 如果请求成功，验证响应结构
        if response.is_success and response.json_data:
            # 验证响应结构完整性
            assert property_tester.validate_video_list_response_structure(response.json_data), \
                f"视频列表响应结构无效，参数: {pagination_params}"
            
            # 验证分页逻辑
            data = response.json_data
            results_count = len(data['results'])
            page_size = pagination_params.get('page_size', 10)
            total_count = data.get('count', 0)
            
            # 返回的记录数不应超过page_size
            assert results_count <= page_size, \
                f"返回记录数({results_count})超过page_size({page_size})"
            
            # 如果不是最后一页，返回的记录数应该等于page_size（假设有足够的数据）
            page = pagination_params.get('page', 1)
            expected_start = (page - 1) * page_size
            
            if expected_start < total_count:
                expected_count = min(page_size, total_count - expected_start)
                if total_count > expected_start:
                    assert results_count <= expected_count, \
                        f"分页逻辑错误: 期望最多{expected_count}条，实际{results_count}条"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


@given(search_params_strategy)
@settings(max_examples=5, deadline=30000)
def test_video_search_response_consistency_property(search_params):
    """
    属性 4: 视频API响应完整性 - 搜索响应一致性
    
    对于任何搜索查询，视频搜索API应该返回符合预期格式的响应数据，
    所有返回的视频对象都应该具有一致的结构。
    
    **验证需求: 3.4**
    """
    config = TestConfigManager()
    property_tester = VideoAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 发送搜索请求
        response = property_tester.client.get('/api/videos/', params=search_params)
        
        # 如果请求成功，验证响应结构
        if response.is_success and response.json_data:
            # 验证响应结构完整性
            assert property_tester.validate_video_list_response_structure(response.json_data), \
                f"搜索响应结构无效，查询: {search_params}"
            
            # 验证搜索结果的一致性
            data = response.json_data
            results = data.get('results', [])
            
            # 所有结果都应该有相同的字段结构
            if results:
                first_video_fields = set(results[0].keys())
                for i, video in enumerate(results[1:], 1):
                    video_fields = set(video.keys())
                    # 允许某些可选字段不存在，但核心字段必须一致
                    core_fields = {'id', 'title', 'file'}
                    assert core_fields.issubset(video_fields), \
                        f"第{i}个视频缺少核心字段，期望: {core_fields}, 实际: {video_fields}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


def test_video_detail_response_completeness_property():
    """
    属性 4: 视频API响应完整性 - 详情响应完整性
    
    对于任何有效的视频ID，视频详情API应该返回比列表更完整的信息，
    并且响应结构应该一致。
    
    **验证需求: 3.2, 3.3**
    """
    config = TestConfigManager()
    property_tester = VideoAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 首先获取视频列表
        list_response = property_tester.client.get('/api/videos/')
        
        if not list_response.is_success or not list_response.json_data:
            pytest.skip("无法获取视频列表进行详情测试")
        
        videos = list_response.json_data.get('results', [])
        if not videos:
            pytest.skip("没有视频可供详情测试")
        
        # 测试前几个视频的详情
        test_count = min(3, len(videos))
        
        for i in range(test_count):
            video_id = videos[i]['id']
            
            # 获取视频详情
            detail_response = property_tester.client.get(f'/api/videos/{video_id}/')
            
            if detail_response.is_success and detail_response.json_data:
                # 验证详情响应结构
                assert property_tester.validate_video_detail_response_structure(detail_response.json_data), \
                    f"视频详情响应结构无效，ID: {video_id}"
                
                # 验证详情包含列表中的基本信息
                detail_data = detail_response.json_data
                list_video = videos[i]
                
                # 核心字段应该匹配
                assert detail_data['id'] == list_video['id'], \
                    f"详情ID({detail_data['id']})与列表ID({list_video['id']})不匹配"
                
                assert detail_data['title'] == list_video['title'], \
                    f"详情标题与列表标题不匹配"
                
                # 详情应该包含列表中的所有字段
                list_fields = set(list_video.keys())
                detail_fields = set(detail_data.keys())
                
                missing_fields = list_fields - detail_fields
                assert not missing_fields, \
                    f"详情缺少列表中的字段: {missing_fields}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


@given(video_upload_data_strategy)
@settings(max_examples=3, deadline=60000)
def test_video_upload_response_consistency_property(upload_data):
    """
    属性 4: 视频API响应完整性 - 上传响应一致性
    
    对于任何有效的上传数据，视频上传API应该返回一致的响应格式，
    包含必要的标识信息。
    
    **验证需求: 3.1, 3.5**
    """
    config = TestConfigManager()
    property_tester = VideoAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 过滤掉空标题
        assume(upload_data.get('title') and upload_data['title'].strip())
        
        # 创建模拟文件
        import io
        video_content = b"fake video content for property testing"
        video_filename = "property_test_video.mp4"
        
        files = {
            'file': (video_filename, io.BytesIO(video_content), 'video/mp4')
        }
        
        # 发送上传请求
        response = property_tester.client.post('/api/videos/upload/', 
                                             data=upload_data, 
                                             files=files)
        
        # 如果上传成功，验证响应结构
        if response.status_code in [200, 201] and response.json_data:
            # 验证上传响应结构
            assert property_tester.validate_upload_response_structure(response.json_data), \
                f"上传响应结构无效，数据: {upload_data}"
            
            upload_result = response.json_data
            
            # 如果返回了视频ID，应该能够获取该视频的详情
            if 'id' in upload_result:
                video_id = upload_result['id']
                
                # 尝试获取刚上传视频的详情
                detail_response = property_tester.client.get(f'/api/videos/{video_id}/')
                
                if detail_response.is_success and detail_response.json_data:
                    detail_data = detail_response.json_data
                    
                    # 验证上传的数据与详情中的数据一致
                    assert detail_data['title'] == upload_data['title'], \
                        f"上传标题与详情标题不匹配"
                    
                    if upload_data.get('description'):
                        assert detail_data.get('description') == upload_data['description'], \
                            f"上传描述与详情描述不匹配"
                    
                    if upload_data.get('category'):
                        assert detail_data.get('category') == upload_data['category'], \
                            f"上传分类与详情分类不匹配"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


def test_video_api_error_response_consistency_property():
    """
    属性 4: 视频API响应完整性 - 错误响应一致性
    
    对于任何无效的请求，视频API应该返回一致的错误响应格式。
    
    **验证需求: 3.1, 3.2, 3.3**
    """
    config = TestConfigManager()
    property_tester = VideoAPIPropertyTester(config)
    
    try:
        # 确保已认证
        if not property_tester.ensure_authenticated():
            pytest.skip("无法认证，跳过属性测试")
        
        # 测试各种错误场景
        error_scenarios = [
            # 无效视频ID
            ('/api/videos/999999/', 'GET', None, 404),
            # 非数字视频ID
            ('/api/videos/abc/', 'GET', None, [400, 404]),
            # 缺少文件的上传
            ('/api/videos/upload/', 'POST', {'title': '测试'}, 400),
        ]
        
        for endpoint, method, data, expected_status in error_scenarios:
            if method == 'GET':
                response = property_tester.client.get(endpoint)
            elif method == 'POST':
                response = property_tester.client.post(endpoint, data=data)
            
            # 验证错误状态码
            if isinstance(expected_status, list):
                assert response.status_code in expected_status, \
                    f"错误状态码不符合预期，端点: {endpoint}, 期望: {expected_status}, 实际: {response.status_code}"
            else:
                assert response.status_code == expected_status, \
                    f"错误状态码不符合预期，端点: {endpoint}, 期望: {expected_status}, 实际: {response.status_code}"
            
            # 错误响应应该有JSON格式（如果有内容）
            if response.content and response.headers.get('Content-Type', '').startswith('application/json'):
                assert response.json_data is not None, \
                    f"错误响应应该有JSON数据，端点: {endpoint}"
    
    except Exception as e:
        # 如果是网络错误或服务不可用，跳过测试
        if "Connection" in str(e) or "timeout" in str(e).lower():
            pytest.skip(f"网络连接问题，跳过测试: {e}")
        else:
            raise
    finally:
        property_tester.close()


# 单元测试用例

def test_video_property_tester_creation(config):
    """测试视频API属性测试器创建"""
    tester = VideoAPIPropertyTester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()
    tester.close()


def test_video_list_response_structure_validation():
    """测试视频列表响应结构验证"""
    config = TestConfigManager()
    tester = VideoAPIPropertyTester(config)
    
    # 测试有效结构
    valid_response = {
        'count': 10,
        'results': [
            {
                'id': 1,
                'title': '测试视频',
                'file': '/media/test.mp4',
                'description': '测试描述',
                'category': '道德经'
            }
        ]
    }
    
    assert tester.validate_video_list_response_structure(valid_response)
    
    # 测试无效结构
    invalid_response = {
        'count': 10
        # 缺少results字段
    }
    
    assert not tester.validate_video_list_response_structure(invalid_response)
    
    tester.close()


def test_video_object_structure_validation():
    """测试视频对象结构验证"""
    config = TestConfigManager()
    tester = VideoAPIPropertyTester(config)
    
    # 测试有效对象
    valid_video = {
        'id': 1,
        'title': '测试视频',
        'file': '/media/test.mp4',
        'description': '测试描述',
        'category': '道德经',
        'created_at': '2023-01-01T00:00:00Z',
        'updated_at': '2023-01-01T00:00:00Z'
    }
    
    assert tester.validate_video_object_structure(valid_video)
    
    # 测试无效对象
    invalid_video = {
        'id': '1',  # 应该是整数
        'title': '测试视频',
        'file': '/media/test.mp4'
    }
    
    assert not tester.validate_video_object_structure(invalid_video)
    
    tester.close()


if __name__ == "__main__":
    # 直接运行属性测试
    pytest.main([__file__, "-v", "--tb=short"])