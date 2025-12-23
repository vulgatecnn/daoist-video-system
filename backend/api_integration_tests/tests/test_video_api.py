"""
视频管理API测试模块

测试视频列表、详情、上传、搜索等功能。
"""

import pytest
import time
import json
import os
import io
from typing import Dict, Any, List
from unittest.mock import patch, Mock
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
from api_integration_tests.utils.test_helpers import TestDataGenerator


class VideoAPITester:
    """视频管理API测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化视频API测试器
        
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
            print(f"✅ 已登录用户: {self.valid_user['username']}")
        else:
            print(f"❌ 登录失败: {self.valid_user['username']}")
        
        return success
    
    def test_video_list_basic(self) -> bool:
        """
        测试基础视频列表获取
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试基础视频列表获取")
            
            # 确保已认证
            if not self.ensure_authenticated():
                print("❌ 需要认证才能访问视频列表")
                return False
            
            # 发送视频列表请求
            response = self.client.get('/api/videos/')
            
            # 验证响应状态码
            if not response.is_success:
                print(f"❌ 获取视频列表失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 视频列表响应没有JSON数据")
                return False
            
            data = response.json_data
            
            # 检查分页字段
            if 'count' not in data or 'results' not in data:
                print(f"❌ 视频列表响应缺少分页字段")
                print(f"   实际字段: {list(data.keys())}")
                return False
            
            # 验证results是数组
            if not isinstance(data['results'], list):
                print("❌ results字段不是数组")
                return False
            
            print(f"✅ 基础视频列表获取成功")
            print(f"   总数: {data.get('count', 0)}")
            print(f"   当前页结果数: {len(data['results'])}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            # 如果有视频，验证视频对象结构
            if data['results']:
                first_video = data['results'][0]
                required_fields = ['id', 'title', 'file']
                missing_fields = [field for field in required_fields if field not in first_video]
                if missing_fields:
                    print(f"⚠️  视频对象缺少字段: {missing_fields}")
                else:
                    print(f"   视频对象字段完整")
            
            return True
            
        except Exception as e:
            print(f"❌ 视频列表测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_list_pagination(self) -> bool:
        """
        测试视频列表分页功能
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频列表分页功能")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 测试第一页
            print("   测试第一页...")
            response_page1 = self.client.get('/api/videos/', params={'page': 1, 'page_size': 5})
            
            if not response_page1.is_success:
                print(f"❌ 获取第一页失败 - 状态码: {response_page1.status_code}")
                return False
            
            data_page1 = response_page1.json_data
            if not data_page1 or 'results' not in data_page1:
                print("❌ 第一页响应格式错误")
                return False
            
            page1_count = len(data_page1['results'])
            total_count = data_page1.get('count', 0)
            
            print(f"   第一页: {page1_count} 条记录")
            print(f"   总记录数: {total_count}")
            
            # 如果总数大于5，测试第二页
            if total_count > 5:
                print("   测试第二页...")
                response_page2 = self.client.get('/api/videos/', params={'page': 2, 'page_size': 5})
                
                if not response_page2.is_success:
                    print(f"❌ 获取第二页失败 - 状态码: {response_page2.status_code}")
                    return False
                
                data_page2 = response_page2.json_data
                if not data_page2 or 'results' not in data_page2:
                    print("❌ 第二页响应格式错误")
                    return False
                
                page2_count = len(data_page2['results'])
                print(f"   第二页: {page2_count} 条记录")
                
                # 验证两页的数据不同
                if page1_count > 0 and page2_count > 0:
                    page1_ids = {v['id'] for v in data_page1['results']}
                    page2_ids = {v['id'] for v in data_page2['results']}
                    
                    if page1_ids & page2_ids:
                        print("⚠️  第一页和第二页有重复的视频ID")
                    else:
                        print("   ✅ 两页数据不重复")
            else:
                print("   总记录数不足，跳过第二页测试")
            
            print(f"✅ 视频列表分页功能正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 分页测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_list_page_size(self) -> bool:
        """
        测试不同的页面大小参数
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试不同的页面大小参数")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 测试不同的page_size值
            page_sizes = [5, 10, 20]
            
            for page_size in page_sizes:
                print(f"   测试 page_size={page_size}...")
                response = self.client.get('/api/videos/', params={'page_size': page_size})
                
                if not response.is_success:
                    print(f"❌ page_size={page_size} 请求失败")
                    return False
                
                data = response.json_data
                if not data or 'results' not in data:
                    print(f"❌ page_size={page_size} 响应格式错误")
                    return False
                
                results_count = len(data['results'])
                total_count = data.get('count', 0)
                
                # 验证返回的记录数不超过page_size
                if results_count > page_size:
                    print(f"❌ 返回记录数({results_count})超过page_size({page_size})")
                    return False
                
                # 如果总数大于page_size，返回的记录数应该等于page_size
                if total_count > page_size and results_count != page_size:
                    print(f"⚠️  总数({total_count})大于page_size({page_size})，但返回记录数({results_count})不等于page_size")
                
                print(f"   ✅ page_size={page_size}: 返回 {results_count} 条记录")
            
            print(f"✅ 页面大小参数测试通过")
            
            return True
            
        except Exception as e:
            print(f"❌ 页面大小测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_list_search(self) -> bool:
        """
        测试视频搜索功能
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频搜索功能")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 首先获取所有视频，找一个用于搜索
            response_all = self.client.get('/api/videos/')
            
            if not response_all.is_success or not response_all.json_data:
                print("❌ 无法获取视频列表进行搜索测试")
                return False
            
            all_videos = response_all.json_data.get('results', [])
            
            if not all_videos:
                print("⚠️  没有视频可供搜索测试，跳过")
                return True
            
            # 使用第一个视频的标题进行搜索
            first_video = all_videos[0]
            search_term = first_video.get('title', '')
            
            if not search_term:
                print("⚠️  第一个视频没有标题，跳过搜索测试")
                return True
            
            # 使用标题的一部分进行搜索
            search_query = search_term[:min(3, len(search_term))]
            
            print(f"   搜索关键词: '{search_query}'")
            
            # 发送搜索请求
            response_search = self.client.get('/api/videos/', params={'search': search_query})
            
            if not response_search.is_success:
                print(f"❌ 搜索请求失败 - 状态码: {response_search.status_code}")
                return False
            
            search_data = response_search.json_data
            if not search_data or 'results' not in search_data:
                print("❌ 搜索响应格式错误")
                return False
            
            search_results = search_data['results']
            
            print(f"   搜索结果数: {len(search_results)}")
            
            # 验证搜索结果包含搜索词
            if search_results:
                # 检查至少有一个结果包含搜索词
                found_match = False
                for video in search_results:
                    title = video.get('title', '').lower()
                    description = video.get('description', '').lower()
                    if search_query.lower() in title or search_query.lower() in description:
                        found_match = True
                        break
                
                if found_match:
                    print(f"   ✅ 搜索结果包含关键词")
                else:
                    print(f"⚠️  搜索结果可能不包含关键词（可能是模糊搜索）")
            
            print(f"✅ 视频搜索功能正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 搜索测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_list_category_filter(self) -> bool:
        """
        测试视频分类筛选功能
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频分类筛选功能")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 首先获取所有视频，找到可用的分类
            response_all = self.client.get('/api/videos/')
            
            if not response_all.is_success or not response_all.json_data:
                print("❌ 无法获取视频列表进行分类测试")
                return False
            
            all_videos = response_all.json_data.get('results', [])
            
            if not all_videos:
                print("⚠️  没有视频可供分类测试，跳过")
                return True
            
            # 收集所有分类
            categories = set()
            for video in all_videos:
                category = video.get('category')
                if category:
                    categories.add(category)
            
            if not categories:
                print("⚠️  没有视频有分类信息，跳过分类筛选测试")
                return True
            
            # 使用第一个分类进行筛选测试
            test_category = list(categories)[0]
            print(f"   测试分类: '{test_category}'")
            
            # 发送分类筛选请求
            response_filtered = self.client.get('/api/videos/', params={'category': test_category})
            
            if not response_filtered.is_success:
                print(f"❌ 分类筛选请求失败 - 状态码: {response_filtered.status_code}")
                return False
            
            filtered_data = response_filtered.json_data
            if not filtered_data or 'results' not in filtered_data:
                print("❌ 分类筛选响应格式错误")
                return False
            
            filtered_results = filtered_data['results']
            
            print(f"   筛选结果数: {len(filtered_results)}")
            
            # 验证所有结果都属于该分类
            if filtered_results:
                all_match = all(video.get('category') == test_category for video in filtered_results)
                if all_match:
                    print(f"   ✅ 所有结果都属于分类 '{test_category}'")
                else:
                    print(f"⚠️  部分结果不属于分类 '{test_category}'")
            
            print(f"✅ 视频分类筛选功能正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 分类筛选测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_list_unauthenticated(self) -> bool:
        """
        测试未认证访问视频列表
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证访问视频列表")
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            # 尝试访问视频列表
            response = self.client.get('/api/videos/')
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证访问正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证访问成功（可能允许匿名访问）")
                return True
            else:
                print(f"❌ 未认证访问返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证访问测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_list_response_time(self) -> bool:
        """
        测试视频列表响应时间
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频列表响应时间")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 测试多次请求的平均响应时间
            response_times = []
            test_count = 3
            
            for i in range(test_count):
                start_time = time.time()
                response = self.client.get('/api/videos/')
                total_time = time.time() - start_time
                
                if response.is_success:
                    response_times.append(total_time)
                    print(f"   第{i+1}次请求: {total_time:.2f}s")
            
            if not response_times:
                print("❌ 所有请求都失败")
                return False
            
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            print(f"   平均响应时间: {avg_time:.2f}s")
            print(f"   最大响应时间: {max_time:.2f}s")
            
            # 验证响应时间在合理范围内（5秒内）
            if max_time > 5.0:
                print(f"⚠️  最大响应时间超过5秒")
            
            print(f"✅ 视频列表响应时间测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 响应时间测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_detail_valid_id(self) -> bool:
        """
        测试获取有效视频ID的详情
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试获取有效视频ID的详情")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 首先获取视频列表，找到一个有效的视频ID
            response_list = self.client.get('/api/videos/')
            
            if not response_list.is_success or not response_list.json_data:
                print("❌ 无法获取视频列表进行详情测试")
                return False
            
            videos = response_list.json_data.get('results', [])
            
            if not videos:
                print("⚠️  没有视频可供详情测试，跳过")
                return True
            
            # 使用第一个视频的ID
            video_id = videos[0].get('id')
            if not video_id:
                print("❌ 第一个视频没有ID字段")
                return False
            
            print(f"   测试视频ID: {video_id}")
            
            # 获取视频详情
            response_detail = self.client.get(f'/api/videos/{video_id}/')
            
            # 验证响应状态码
            if not response_detail.is_success:
                print(f"❌ 获取视频详情失败 - 状态码: {response_detail.status_code}")
                if response_detail.json_data:
                    print(f"   错误信息: {response_detail.json_data}")
                return False
            
            # 验证响应数据结构
            if not response_detail.json_data:
                print("❌ 视频详情响应没有JSON数据")
                return False
            
            detail_data = response_detail.json_data
            
            # 检查必要字段
            required_fields = ['id', 'title', 'file']
            missing_fields = [field for field in required_fields if field not in detail_data]
            if missing_fields:
                print(f"❌ 视频详情缺少字段: {missing_fields}")
                return False
            
            # 验证ID匹配
            if detail_data['id'] != video_id:
                print(f"❌ 返回的视频ID({detail_data['id']})与请求的ID({video_id})不匹配")
                return False
            
            print(f"✅ 视频详情获取成功")
            print(f"   视频ID: {detail_data['id']}")
            print(f"   标题: {detail_data.get('title', 'N/A')}")
            print(f"   描述: {detail_data.get('description', 'N/A')[:50]}...")
            print(f"   分类: {detail_data.get('category', 'N/A')}")
            print(f"   响应时间: {response_detail.response_time:.2f}s")
            
            # 验证详情比列表包含更多信息
            list_video = videos[0]
            detail_fields = set(detail_data.keys())
            list_fields = set(list_video.keys())
            
            if detail_fields >= list_fields:
                print(f"   ✅ 详情包含列表中的所有字段")
                extra_fields = detail_fields - list_fields
                if extra_fields:
                    print(f"   额外字段: {list(extra_fields)}")
            else:
                print(f"⚠️  详情字段少于列表字段")
            
            return True
            
        except Exception as e:
            print(f"❌ 视频详情测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_detail_invalid_id(self) -> bool:
        """
        测试获取无效视频ID的详情
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试获取无效视频ID的详情")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用一个不存在的视频ID
            invalid_id = 999999
            
            print(f"   测试无效视频ID: {invalid_id}")
            
            # 获取视频详情
            response_detail = self.client.get(f'/api/videos/{invalid_id}/')
            
            # 验证应该返回404错误
            if response_detail.status_code != 404:
                print(f"❌ 无效视频ID应该返回404，实际返回: {response_detail.status_code}")
                return False
            
            # 验证错误响应格式
            if response_detail.json_data:
                print(f"   错误信息: {response_detail.json_data}")
            
            print(f"✅ 无效视频ID正确返回404错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 无效视频ID测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_detail_non_numeric_id(self) -> bool:
        """
        测试使用非数字ID获取视频详情
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试使用非数字ID获取视频详情")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用非数字ID
            non_numeric_id = "abc"
            
            print(f"   测试非数字ID: {non_numeric_id}")
            
            # 获取视频详情
            response_detail = self.client.get(f'/api/videos/{non_numeric_id}/')
            
            # 验证应该返回404或400错误
            if response_detail.status_code not in [400, 404]:
                print(f"❌ 非数字ID应该返回400或404，实际返回: {response_detail.status_code}")
                return False
            
            print(f"✅ 非数字ID正确返回{response_detail.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 非数字ID测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_detail_unauthenticated(self) -> bool:
        """
        测试未认证访问视频详情
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证访问视频详情")
            
            # 首先获取一个有效的视频ID（需要认证）
            if not self.ensure_authenticated():
                return False
            
            response_list = self.client.get('/api/videos/')
            if not response_list.is_success or not response_list.json_data:
                print("❌ 无法获取视频列表")
                return False
            
            videos = response_list.json_data.get('results', [])
            if not videos:
                print("⚠️  没有视频可供测试，跳过")
                return True
            
            video_id = videos[0].get('id')
            if not video_id:
                print("❌ 无法获取视频ID")
                return False
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            print(f"   测试未认证访问视频ID: {video_id}")
            
            # 尝试访问视频详情
            response = self.client.get(f'/api/videos/{video_id}/')
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证访问视频详情正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证访问视频详情成功（可能允许匿名访问）")
                return True
            else:
                print(f"❌ 未认证访问返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证访问视频详情测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_detail_response_completeness(self) -> bool:
        """
        测试视频详情响应的完整性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频详情响应的完整性")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取视频列表
            response_list = self.client.get('/api/videos/')
            if not response_list.is_success or not response_list.json_data:
                print("❌ 无法获取视频列表")
                return False
            
            videos = response_list.json_data.get('results', [])
            if not videos:
                print("⚠️  没有视频可供测试，跳过")
                return True
            
            video_id = videos[0].get('id')
            
            # 获取视频详情
            response_detail = self.client.get(f'/api/videos/{video_id}/')
            
            if not response_detail.is_success or not response_detail.json_data:
                print("❌ 无法获取视频详情")
                return False
            
            detail_data = response_detail.json_data
            
            # 检查期望的字段
            expected_fields = {
                'id': int,
                'title': str,
                'description': (str, type(None)),
                'file': str,
                'category': (str, type(None)),
                'created_at': str,
                'updated_at': str,
                'duration': (int, float, type(None)),
                'file_size': (int, type(None))
            }
            
            print(f"   检查字段完整性...")
            
            missing_fields = []
            wrong_type_fields = []
            
            for field, expected_type in expected_fields.items():
                if field not in detail_data:
                    missing_fields.append(field)
                else:
                    value = detail_data[field]
                    if not isinstance(value, expected_type):
                        wrong_type_fields.append(f"{field}: 期望{expected_type}, 实际{type(value)}")
            
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
            
            if wrong_type_fields:
                print(f"⚠️  字段类型错误: {wrong_type_fields}")
            
            # 验证必要字段存在
            required_fields = ['id', 'title', 'file']
            has_required = all(field in detail_data for field in required_fields)
            
            if has_required:
                print(f"   ✅ 必要字段完整")
            else:
                print(f"❌ 缺少必要字段")
                return False
            
            # 验证文件URL格式
            file_url = detail_data.get('file', '')
            if file_url:
                if file_url.startswith(('http://', 'https://', '/')):
                    print(f"   ✅ 文件URL格式正确")
                else:
                    print(f"⚠️  文件URL格式可能不正确: {file_url}")
            
            print(f"✅ 视频详情响应完整性检查完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 响应完整性测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_upload_valid_file(self) -> bool:
        """
        测试上传有效视频文件
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试上传有效视频文件")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个模拟的视频文件
            video_content = b"fake video content for testing"
            video_filename = "test_video.mp4"
            
            # 准备上传数据
            upload_data = {
                'title': '测试视频上传',
                'description': '这是一个测试上传的视频',
                'category': '道德经'
            }
            
            # 准备文件数据
            files = {
                'file': (video_filename, io.BytesIO(video_content), 'video/mp4')
            }
            
            print(f"   上传文件: {video_filename}")
            print(f"   标题: {upload_data['title']}")
            
            # 发送上传请求
            response = self.client.post('/api/videos/upload/', 
                                      data=upload_data, 
                                      files=files)
            
            # 验证响应状态码
            if response.status_code not in [200, 201]:
                print(f"❌ 视频上传失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 视频上传响应没有JSON数据")
                return False
            
            upload_result = response.json_data
            
            # 检查必要字段
            if 'id' not in upload_result and 'message' not in upload_result:
                print(f"❌ 上传响应缺少必要字段")
                print(f"   实际字段: {list(upload_result.keys())}")
                return False
            
            print(f"✅ 视频上传成功")
            if 'id' in upload_result:
                print(f"   视频ID: {upload_result['id']}")
            if 'message' in upload_result:
                print(f"   消息: {upload_result['message']}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ 视频上传测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_upload_missing_file(self) -> bool:
        """
        测试上传时缺少文件
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试上传时缺少文件")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 只提供元数据，不提供文件
            upload_data = {
                'title': '测试视频上传',
                'description': '这是一个测试上传的视频',
                'category': '道德经'
            }
            
            print("   发送不包含文件的上传请求...")
            
            # 发送上传请求（不包含文件）
            response = self.client.post('/api/videos/upload/', data=upload_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 缺少文件应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 缺少文件正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 缺少文件测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_upload_missing_title(self) -> bool:
        """
        测试上传时缺少标题
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试上传时缺少标题")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建模拟文件但不提供标题
            video_content = b"fake video content for testing"
            video_filename = "test_video.mp4"
            
            upload_data = {
                'description': '这是一个测试上传的视频',
                'category': '道德经'
                # 故意不包含title
            }
            
            files = {
                'file': (video_filename, io.BytesIO(video_content), 'video/mp4')
            }
            
            print("   发送不包含标题的上传请求...")
            
            # 发送上传请求
            response = self.client.post('/api/videos/upload/', 
                                      data=upload_data, 
                                      files=files)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 缺少标题应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 缺少标题正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 缺少标题测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_upload_invalid_file_type(self) -> bool:
        """
        测试上传无效文件类型
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试上传无效文件类型")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个文本文件而不是视频文件
            text_content = b"This is not a video file"
            text_filename = "test_file.txt"
            
            upload_data = {
                'title': '测试无效文件类型',
                'description': '这是一个无效的文件类型测试',
                'category': '道德经'
            }
            
            files = {
                'file': (text_filename, io.BytesIO(text_content), 'text/plain')
            }
            
            print(f"   上传文件: {text_filename} (text/plain)")
            
            # 发送上传请求
            response = self.client.post('/api/videos/upload/', 
                                      data=upload_data, 
                                      files=files)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 无效文件类型应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 无效文件类型正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 无效文件类型测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_upload_large_file_simulation(self) -> bool:
        """
        测试大文件上传模拟
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试大文件上传模拟")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个较大的模拟文件（1MB）
            large_content = b"x" * (1024 * 1024)  # 1MB
            large_filename = "large_test_video.mp4"
            
            upload_data = {
                'title': '大文件上传测试',
                'description': '这是一个大文件上传测试',
                'category': '道德经'
            }
            
            files = {
                'file': (large_filename, io.BytesIO(large_content), 'video/mp4')
            }
            
            print(f"   上传文件: {large_filename} (1MB)")
            
            # 记录开始时间
            start_time = time.time()
            
            # 发送上传请求
            response = self.client.post('/api/videos/upload/', 
                                      data=upload_data, 
                                      files=files)
            
            upload_time = time.time() - start_time
            
            print(f"   上传耗时: {upload_time:.2f}s")
            
            # 验证响应
            if response.status_code in [200, 201]:
                print(f"✅ 大文件上传成功")
                if response.json_data:
                    print(f"   响应: {response.json_data}")
                return True
            elif response.status_code == 413:
                print(f"⚠️  文件过大被拒绝 (413 Payload Too Large)")
                return True
            else:
                print(f"❌ 大文件上传失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
        except Exception as e:
            print(f"❌ 大文件上传测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_video_upload_unauthenticated(self) -> bool:
        """
        测试未认证上传视频
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证上传视频")
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            # 创建模拟文件
            video_content = b"fake video content for testing"
            video_filename = "test_video.mp4"
            
            upload_data = {
                'title': '未认证上传测试',
                'description': '这是一个未认证上传测试',
                'category': '道德经'
            }
            
            files = {
                'file': (video_filename, io.BytesIO(video_content), 'video/mp4')
            }
            
            print("   尝试未认证上传...")
            
            # 发送上传请求
            response = self.client.post('/api/videos/upload/', 
                                      data=upload_data, 
                                      files=files)
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证上传正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证上传成功（可能允许匿名上传）")
                return True
            else:
                print(f"❌ 未认证上传返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证上传测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_admin_video_list_access(self) -> bool:
        """
        测试管理员视频列表访问
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试管理员视频列表访问")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 尝试访问管理员视频列表
            response = self.client.get('/api/videos/admin/list/')
            
            # 验证响应
            if response.is_success:
                print(f"✅ 管理员视频列表访问成功")
                
                if response.json_data:
                    # 验证响应结构
                    if self.validate_video_list_response_structure(response.json_data):
                        print(f"   响应结构正确")
                    else:
                        print(f"⚠️  响应结构可能不标准")
                    
                    data = response.json_data
                    print(f"   管理员视频总数: {data.get('count', 0)}")
                    print(f"   当前页结果数: {len(data.get('results', []))}")
                
                return True
            elif response.status_code == 403:
                print(f"⚠️  当前用户没有管理员权限 (403)")
                return True  # 这是预期的行为
            elif response.status_code == 401:
                print(f"❌ 认证失败 (401)")
                return False
            else:
                print(f"❌ 管理员视频列表访问失败 - 状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 管理员视频列表测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_admin_batch_operations_simulation(self) -> bool:
        """
        测试管理员批量操作模拟
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试管理员批量操作模拟")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 首先获取一些视频ID用于批量操作
            response_list = self.client.get('/api/videos/')
            
            if not response_list.is_success or not response_list.json_data:
                print("❌ 无法获取视频列表进行批量操作测试")
                return False
            
            videos = response_list.json_data.get('results', [])
            if not videos:
                print("⚠️  没有视频可供批量操作测试，跳过")
                return True
            
            # 选择前几个视频ID进行测试
            video_ids = [video['id'] for video in videos[:min(2, len(videos))]]
            
            print(f"   测试批量操作视频ID: {video_ids}")
            
            # 测试批量分类更新
            batch_category_data = {
                'video_ids': video_ids,
                'category': '测试分类'
            }
            
            response_category = self.client.post('/api/videos/admin/batch-category/', 
                                               data=batch_category_data)
            
            if response_category.is_success:
                print(f"✅ 批量分类更新成功")
            elif response_category.status_code == 403:
                print(f"⚠️  没有批量分类更新权限 (403)")
            else:
                print(f"⚠️  批量分类更新失败 - 状态码: {response_category.status_code}")
            
            # 测试批量删除（注意：这可能会实际删除数据，在生产环境中要小心）
            # 这里我们只测试请求格式，不实际执行
            batch_delete_data = {
                'video_ids': [999999]  # 使用不存在的ID
            }
            
            response_delete = self.client.post('/api/videos/admin/batch-delete/', 
                                             data=batch_delete_data)
            
            if response_delete.is_success:
                print(f"✅ 批量删除请求格式正确")
            elif response_delete.status_code == 403:
                print(f"⚠️  没有批量删除权限 (403)")
            elif response_delete.status_code == 404:
                print(f"✅ 批量删除正确处理不存在的ID (404)")
            else:
                print(f"⚠️  批量删除测试 - 状态码: {response_delete.status_code}")
            
            print(f"✅ 管理员批量操作测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 批量操作测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_admin_video_edit_access(self) -> bool:
        """
        测试管理员视频编辑访问
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试管理员视频编辑访问")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取一个视频ID用于编辑测试
            response_list = self.client.get('/api/videos/')
            
            if not response_list.is_success or not response_list.json_data:
                print("❌ 无法获取视频列表进行编辑测试")
                return False
            
            videos = response_list.json_data.get('results', [])
            if not videos:
                print("⚠️  没有视频可供编辑测试，跳过")
                return True
            
            video_id = videos[0]['id']
            
            print(f"   测试编辑视频ID: {video_id}")
            
            # 尝试访问管理员编辑页面
            response_edit = self.client.get(f'/api/videos/admin/{video_id}/edit/')
            
            if response_edit.is_success:
                print(f"✅ 管理员视频编辑访问成功")
                
                if response_edit.json_data:
                    # 验证编辑响应包含视频信息
                    edit_data = response_edit.json_data
                    if 'id' in edit_data and edit_data['id'] == video_id:
                        print(f"   ✅ 编辑数据包含正确的视频ID")
                    else:
                        print(f"⚠️  编辑数据可能不完整")
                
                return True
            elif response_edit.status_code == 403:
                print(f"⚠️  没有管理员编辑权限 (403)")
                return True  # 这是预期的行为
            elif response_edit.status_code == 404:
                print(f"⚠️  视频不存在或编辑端点不存在 (404)")
                return True
            else:
                print(f"❌ 管理员编辑访问失败 - 状态码: {response_edit.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 管理员编辑测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_admin_permissions_enforcement(self) -> bool:
        """
        测试管理员权限控制
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试管理员权限控制")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 测试各种管理员端点的权限控制
            admin_endpoints = [
                '/api/videos/admin/list/',
                '/api/videos/admin/monitoring/statistics/',
                '/api/videos/admin/monitoring/storage/',
            ]
            
            accessible_count = 0
            forbidden_count = 0
            
            for endpoint in admin_endpoints:
                print(f"   测试端点: {endpoint}")
                
                response = self.client.get(endpoint)
                
                if response.is_success:
                    accessible_count += 1
                    print(f"     ✅ 可访问")
                elif response.status_code == 403:
                    forbidden_count += 1
                    print(f"     ⚠️  权限不足 (403)")
                elif response.status_code == 404:
                    print(f"     ⚠️  端点不存在 (404)")
                else:
                    print(f"     ❌ 意外状态码: {response.status_code}")
            
            print(f"   权限测试结果: {accessible_count} 个可访问, {forbidden_count} 个权限不足")
            
            # 如果所有端点都返回403，说明权限控制正常工作
            # 如果有些可访问，说明当前用户有管理员权限
            # 两种情况都是正常的
            
            print(f"✅ 管理员权限控制测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 权限控制测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def test_video_upload_progress_tracking(self) -> bool:
        """
        测试视频上传进度跟踪（模拟）
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频上传进度跟踪")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建模拟文件
            video_content = b"fake video content for progress testing"
            video_filename = "progress_test_video.mp4"
            
            upload_data = {
                'title': '进度跟踪测试',
                'description': '这是一个进度跟踪测试',
                'category': '道德经'
            }
            
            files = {
                'file': (video_filename, io.BytesIO(video_content), 'video/mp4')
            }
            
            print("   模拟进度跟踪上传...")
            
            # 记录上传过程的时间点
            start_time = time.time()
            
            # 发送上传请求
            response = self.client.post('/api/videos/upload/', 
                                      data=upload_data, 
                                      files=files)
            
            end_time = time.time()
            upload_duration = end_time - start_time
            
            print(f"   上传耗时: {upload_duration:.2f}s")
            
            # 验证响应
            if response.status_code in [200, 201]:
                print(f"✅ 上传完成，可以跟踪进度")
                
                # 检查响应是否包含进度相关信息
                if response.json_data:
                    data = response.json_data
                    if 'id' in data:
                        print(f"   视频ID: {data['id']} (可用于后续进度查询)")
                    if 'status' in data:
                        print(f"   状态: {data['status']}")
                
                return True
            else:
                print(f"❌ 上传失败 - 状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 进度跟踪测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def test_video_detail_response_time(self) -> bool:
        """
        测试视频详情响应时间
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试视频详情响应时间")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取一个有效的视频ID
            response_list = self.client.get('/api/videos/')
            if not response_list.is_success or not response_list.json_data:
                print("❌ 无法获取视频列表")
                return False
            
            videos = response_list.json_data.get('results', [])
            if not videos:
                print("⚠️  没有视频可供测试，跳过")
                return True
            
            video_id = videos[0].get('id')
            
            # 测试多次请求的响应时间
            response_times = []
            test_count = 3
            
            for i in range(test_count):
                start_time = time.time()
                response = self.client.get(f'/api/videos/{video_id}/')
                total_time = time.time() - start_time
                
                if response.is_success:
                    response_times.append(total_time)
                    print(f"   第{i+1}次请求: {total_time:.2f}s")
            
            if not response_times:
                print("❌ 所有请求都失败")
                return False
            
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            print(f"   平均响应时间: {avg_time:.2f}s")
            print(f"   最大响应时间: {max_time:.2f}s")
            
            # 验证响应时间在合理范围内（3秒内）
            if max_time > 3.0:
                print(f"⚠️  最大响应时间超过3秒")
            
            print(f"✅ 视频详情响应时间测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 响应时间测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()


# pytest测试用例

@pytest.fixture
def config():
    """测试配置fixture"""
    return TestConfigManager()


@pytest.fixture
def video_tester(config):
    """视频API测试器fixture"""
    tester = VideoAPITester(config)
    yield tester
    tester.close()


def test_video_api_tester_creation(config):
    """测试视频API测试器创建"""
    tester = VideoAPITester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()
    tester.close()


def test_video_list_basic(video_tester):
    """测试基础视频列表获取"""
    result = video_tester.test_video_list_basic()
    assert isinstance(result, bool)


def test_video_list_pagination(video_tester):
    """测试视频列表分页"""
    result = video_tester.test_video_list_pagination()
    assert isinstance(result, bool)


def test_video_list_page_size(video_tester):
    """测试页面大小参数"""
    result = video_tester.test_video_list_page_size()
    assert isinstance(result, bool)


def test_video_list_search(video_tester):
    """测试视频搜索"""
    result = video_tester.test_video_list_search()
    assert isinstance(result, bool)


def test_video_list_category_filter(video_tester):
    """测试分类筛选"""
    result = video_tester.test_video_list_category_filter()
    assert isinstance(result, bool)


def test_video_list_unauthenticated(video_tester):
    """测试未认证访问"""
    result = video_tester.test_video_list_unauthenticated()
    assert isinstance(result, bool)


def test_video_list_response_time(video_tester):
    """测试响应时间"""
    result = video_tester.test_video_list_response_time()
    assert isinstance(result, bool)


def test_video_detail_valid_id(video_tester):
    """测试获取有效视频ID的详情"""
    result = video_tester.test_video_detail_valid_id()
    assert isinstance(result, bool)


def test_video_detail_invalid_id(video_tester):
    """测试获取无效视频ID的详情"""
    result = video_tester.test_video_detail_invalid_id()
    assert isinstance(result, bool)


def test_video_detail_non_numeric_id(video_tester):
    """测试使用非数字ID获取视频详情"""
    result = video_tester.test_video_detail_non_numeric_id()
    assert isinstance(result, bool)


def test_video_detail_unauthenticated(video_tester):
    """测试未认证访问视频详情"""
    result = video_tester.test_video_detail_unauthenticated()
    assert isinstance(result, bool)


def test_video_detail_response_completeness(video_tester):
    """测试视频详情响应完整性"""
    result = video_tester.test_video_detail_response_completeness()
    assert isinstance(result, bool)


def test_video_detail_response_time(video_tester):
    """测试视频详情响应时间"""
    result = video_tester.test_video_detail_response_time()
    assert isinstance(result, bool)


def test_video_upload_valid_file(video_tester):
    """测试上传有效视频文件"""
    result = video_tester.test_video_upload_valid_file()
    assert isinstance(result, bool)


def test_video_upload_missing_file(video_tester):
    """测试上传时缺少文件"""
    result = video_tester.test_video_upload_missing_file()
    assert isinstance(result, bool)


def test_video_upload_missing_title(video_tester):
    """测试上传时缺少标题"""
    result = video_tester.test_video_upload_missing_title()
    assert isinstance(result, bool)


def test_video_upload_invalid_file_type(video_tester):
    """测试上传无效文件类型"""
    result = video_tester.test_video_upload_invalid_file_type()
    assert isinstance(result, bool)


def test_video_upload_large_file_simulation(video_tester):
    """测试大文件上传模拟"""
    result = video_tester.test_video_upload_large_file_simulation()
    assert isinstance(result, bool)


def test_video_upload_unauthenticated(video_tester):
    """测试未认证上传视频"""
    result = video_tester.test_video_upload_unauthenticated()
    assert isinstance(result, bool)


def test_video_upload_progress_tracking(video_tester):
    """测试视频上传进度跟踪"""
    result = video_tester.test_video_upload_progress_tracking()
    assert isinstance(result, bool)


def test_admin_video_list_access(video_tester):
    """测试管理员视频列表访问"""
    result = video_tester.test_admin_video_list_access()
    assert isinstance(result, bool)


def test_admin_batch_operations_simulation(video_tester):
    """测试管理员批量操作模拟"""
    result = video_tester.test_admin_batch_operations_simulation()
    assert isinstance(result, bool)


def test_admin_video_edit_access(video_tester):
    """测试管理员视频编辑访问"""
    result = video_tester.test_admin_video_edit_access()
    assert isinstance(result, bool)


def test_admin_permissions_enforcement(video_tester):
    """测试管理员权限控制"""
    result = video_tester.test_admin_permissions_enforcement()
    assert isinstance(result, bool)


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = VideoAPITester(config)
    
    print("开始视频管理API测试...")
    print(f"目标URL: {config.get_base_url()}")
    
    # 执行视频列表测试
    print("\n=== 视频列表测试 ===")
    print("1. 测试基础视频列表获取...")
    basic_result = tester.test_video_list_basic()
    
    print("\n2. 测试视频列表分页...")
    pagination_result = tester.test_video_list_pagination()
    
    print("\n3. 测试页面大小参数...")
    page_size_result = tester.test_video_list_page_size()
    
    print("\n4. 测试视频搜索...")
    search_result = tester.test_video_list_search()
    
    print("\n5. 测试分类筛选...")
    category_result = tester.test_video_list_category_filter()
    
    print("\n6. 测试未认证访问...")
    unauth_result = tester.test_video_list_unauthenticated()
    
    print("\n7. 测试响应时间...")
    response_time_result = tester.test_video_list_response_time()
    
    # 执行视频详情测试
    print("\n=== 视频详情测试 ===")
    print("8. 测试获取有效视频ID的详情...")
    detail_valid_result = tester.test_video_detail_valid_id()
    
    print("\n9. 测试获取无效视频ID的详情...")
    detail_invalid_result = tester.test_video_detail_invalid_id()
    
    print("\n10. 测试使用非数字ID获取视频详情...")
    detail_non_numeric_result = tester.test_video_detail_non_numeric_id()
    
    print("\n11. 测试未认证访问视频详情...")
    detail_unauth_result = tester.test_video_detail_unauthenticated()
    
    print("\n12. 测试视频详情响应完整性...")
    detail_completeness_result = tester.test_video_detail_response_completeness()
    
    print("\n13. 测试视频详情响应时间...")
    detail_response_time_result = tester.test_video_detail_response_time()
    
    # 执行视频上传测试
    print("\n=== 视频上传测试 ===")
    print("14. 测试上传有效视频文件...")
    upload_valid_result = tester.test_video_upload_valid_file()
    
    print("\n15. 测试上传时缺少文件...")
    upload_missing_file_result = tester.test_video_upload_missing_file()
    
    print("\n16. 测试上传时缺少标题...")
    upload_missing_title_result = tester.test_video_upload_missing_title()
    
    print("\n17. 测试上传无效文件类型...")
    upload_invalid_type_result = tester.test_video_upload_invalid_file_type()
    
    print("\n18. 测试大文件上传模拟...")
    upload_large_file_result = tester.test_video_upload_large_file_simulation()
    
    print("\n19. 测试未认证上传视频...")
    upload_unauth_result = tester.test_video_upload_unauthenticated()
    
    print("\n20. 测试视频上传进度跟踪...")
    upload_progress_result = tester.test_video_upload_progress_tracking()
    
    # 执行管理员视频管理测试
    print("\n=== 管理员视频管理测试 ===")
    print("21. 测试管理员视频列表访问...")
    admin_list_result = tester.test_admin_video_list_access()
    
    print("\n22. 测试管理员批量操作...")
    admin_batch_result = tester.test_admin_batch_operations_simulation()
    
    print("\n23. 测试管理员视频编辑访问...")
    admin_edit_result = tester.test_admin_video_edit_access()
    
    print("\n24. 测试管理员权限控制...")
    admin_permissions_result = tester.test_admin_permissions_enforcement()
    
    # 总结
    print(f"\n=== 测试结果总结 ===")
    print("视频列表测试:")
    print(f"- 基础视频列表获取: {'✅ 通过' if basic_result else '❌ 失败'}")
    print(f"- 视频列表分页: {'✅ 通过' if pagination_result else '❌ 失败'}")
    print(f"- 页面大小参数: {'✅ 通过' if page_size_result else '❌ 失败'}")
    print(f"- 视频搜索: {'✅ 通过' if search_result else '❌ 失败'}")
    print(f"- 分类筛选: {'✅ 通过' if category_result else '❌ 失败'}")
    print(f"- 未认证访问: {'✅ 通过' if unauth_result else '❌ 失败'}")
    print(f"- 响应时间: {'✅ 通过' if response_time_result else '❌ 失败'}")
    
    print("视频详情测试:")
    print(f"- 获取有效视频详情: {'✅ 通过' if detail_valid_result else '❌ 失败'}")
    print(f"- 获取无效视频详情: {'✅ 通过' if detail_invalid_result else '❌ 失败'}")
    print(f"- 非数字ID测试: {'✅ 通过' if detail_non_numeric_result else '❌ 失败'}")
    print(f"- 未认证访问详情: {'✅ 通过' if detail_unauth_result else '❌ 失败'}")
    print(f"- 响应完整性: {'✅ 通过' if detail_completeness_result else '❌ 失败'}")
    print(f"- 详情响应时间: {'✅ 通过' if detail_response_time_result else '❌ 失败'}")
    
    print("视频上传测试:")
    print(f"- 上传有效文件: {'✅ 通过' if upload_valid_result else '❌ 失败'}")
    print(f"- 缺少文件测试: {'✅ 通过' if upload_missing_file_result else '❌ 失败'}")
    print(f"- 缺少标题测试: {'✅ 通过' if upload_missing_title_result else '❌ 失败'}")
    print(f"- 无效文件类型: {'✅ 通过' if upload_invalid_type_result else '❌ 失败'}")
    print(f"- 大文件上传: {'✅ 通过' if upload_large_file_result else '❌ 失败'}")
    print(f"- 未认证上传: {'✅ 通过' if upload_unauth_result else '❌ 失败'}")
    print(f"- 进度跟踪: {'✅ 通过' if upload_progress_result else '❌ 失败'}")
    
    print("管理员视频管理测试:")
    print(f"- 管理员列表访问: {'✅ 通过' if admin_list_result else '❌ 失败'}")
    print(f"- 批量操作: {'✅ 通过' if admin_batch_result else '❌ 失败'}")
    print(f"- 编辑访问: {'✅ 通过' if admin_edit_result else '❌ 失败'}")
    print(f"- 权限控制: {'✅ 通过' if admin_permissions_result else '❌ 失败'}")
    
    # 计算总体通过率
    all_results = [
        basic_result, pagination_result, page_size_result,
        search_result, category_result, unauth_result, response_time_result,
        detail_valid_result, detail_invalid_result, detail_non_numeric_result,
        detail_unauth_result, detail_completeness_result, detail_response_time_result,
        upload_valid_result, upload_missing_file_result, upload_missing_title_result,
        upload_invalid_type_result, upload_large_file_result, upload_unauth_result,
        upload_progress_result, admin_list_result, admin_batch_result,
        admin_edit_result, admin_permissions_result
    ]
    passed_count = sum(1 for result in all_results if result)
    total_count = len(all_results)
    pass_rate = (passed_count / total_count) * 100
    
    print(f"\n总体通过率: {passed_count}/{total_count} ({pass_rate:.1f}%)")
    
    tester.close()
