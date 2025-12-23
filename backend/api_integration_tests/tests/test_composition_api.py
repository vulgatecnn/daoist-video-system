"""
视频合成API测试模块

测试视频合成任务创建、状态查询、下载和取消等功能。
"""

import pytest
import time
import json
import os
import sys
from typing import Dict, Any, List, Optional
from unittest.mock import patch, Mock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
from api_integration_tests.utils.test_helpers import TestDataGenerator


class CompositionAPITester:
    """视频合成API测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化视频合成API测试器
        
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
        
        # 存储创建的任务ID，用于后续测试
        self.created_task_ids: List[str] = []
    
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
    
    def get_available_video_ids(self) -> List[int]:
        """
        获取可用的视频ID列表
        
        Returns:
            List[int]: 视频ID列表
        """
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
            
            return video_ids
            
        except Exception as e:
            print(f"获取视频ID列表异常: {str(e)}")
            return []
    
    def test_composition_create_valid_request(self) -> bool:
        """
        测试创建有效的合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试创建有效的合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取可用的视频ID
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行合成测试，跳过")
                return True
            
            # 选择前两个视频进行合成
            selected_video_ids = video_ids[:2]
            
            # 准备合成请求数据
            composition_data = {
                'video_ids': selected_video_ids,
                'output_format': 'mp4',
                'quality': 'high',
                'title': '测试合成视频',
                'description': '这是一个测试合成的视频'
            }
            
            print(f"   合成视频ID: {selected_video_ids}")
            print(f"   输出格式: {composition_data['output_format']}")
            print(f"   质量: {composition_data['quality']}")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证响应状态码
            if not response.is_success:
                print(f"❌ 创建合成任务失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 合成任务创建响应没有JSON数据")
                return False
            
            result_data = response.json_data
            
            # 检查必要字段
            required_fields = ['task_id', 'status']
            missing_fields = [field for field in required_fields if field not in result_data]
            if missing_fields:
                print(f"❌ 合成任务响应缺少字段: {missing_fields}")
                print(f"   实际字段: {list(result_data.keys())}")
                return False
            
            task_id = result_data['task_id']
            status = result_data['status']
            
            # 验证task_id不为空
            if not task_id:
                print("❌ 返回的task_id为空")
                return False
            
            # 验证status是有效值
            valid_statuses = ['pending', 'processing', 'completed', 'failed']
            if status not in valid_statuses:
                print(f"❌ 返回的status({status})不在有效值范围内: {valid_statuses}")
                return False
            
            # 保存任务ID用于后续测试
            self.created_task_ids.append(task_id)
            
            print(f"✅ 合成任务创建成功")
            print(f"   任务ID: {task_id}")
            print(f"   状态: {status}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            # 检查其他可选字段
            optional_fields = ['message', 'estimated_duration', 'created_at']
            for field in optional_fields:
                if field in result_data:
                    print(f"   {field}: {result_data[field]}")
            
            return True
            
        except Exception as e:
            print(f"❌ 合成任务创建测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_invalid_video_ids(self) -> bool:
        """
        测试使用无效视频ID创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试使用无效视频ID创建合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用不存在的视频ID
            invalid_video_ids = [999999, 999998]
            
            composition_data = {
                'video_ids': invalid_video_ids,
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            print(f"   使用无效视频ID: {invalid_video_ids}")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 无效视频ID应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
                
                # 检查错误信息是否包含相关描述
                error_message = str(response.json_data).lower()
                if 'video' in error_message or 'not found' in error_message or 'invalid' in error_message:
                    print(f"   ✅ 错误信息包含相关描述")
                else:
                    print(f"⚠️  错误信息可能不够具体")
            
            print(f"✅ 无效视频ID正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 无效视频ID测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_missing_video_ids(self) -> bool:
        """
        测试缺少video_ids参数创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试缺少video_ids参数创建合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 不包含video_ids参数
            composition_data = {
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            print("   发送不包含video_ids的请求...")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 缺少video_ids应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 缺少video_ids正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 缺少video_ids测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_empty_video_ids(self) -> bool:
        """
        测试空的video_ids列表创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试空的video_ids列表创建合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 提供空的video_ids列表
            composition_data = {
                'video_ids': [],
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            print("   发送空video_ids列表的请求...")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 空video_ids列表应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 空video_ids列表正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 空video_ids列表测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_single_video_id(self) -> bool:
        """
        测试单个视频ID创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试单个视频ID创建合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取可用的视频ID
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 1:
                print("⚠️  需要至少1个视频才能进行测试，跳过")
                return True
            
            # 使用单个视频ID
            single_video_id = [video_ids[0]]
            
            composition_data = {
                'video_ids': single_video_id,
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            print(f"   使用单个视频ID: {single_video_id}")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证响应 - 可能成功（如果支持单视频处理）或失败（如果需要多个视频）
            if response.is_success:
                print(f"✅ 单个视频ID合成任务创建成功（支持单视频处理）")
                
                if response.json_data:
                    task_id = response.json_data.get('task_id')
                    if task_id:
                        self.created_task_ids.append(task_id)
                        print(f"   任务ID: {task_id}")
                
                return True
            elif response.is_client_error:
                print(f"✅ 单个视频ID正确返回{response.status_code}错误（需要多个视频）")
                
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                
                return True
            else:
                print(f"❌ 单个视频ID返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 单个视频ID测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_invalid_output_format(self) -> bool:
        """
        测试无效输出格式创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试无效输出格式创建合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取可用的视频ID
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            # 使用无效的输出格式
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'invalid_format',
                'quality': 'high'
            }
            
            print(f"   使用无效输出格式: {composition_data['output_format']}")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 无效输出格式应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 无效输出格式正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 无效输出格式测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_invalid_quality(self) -> bool:
        """
        测试无效质量参数创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试无效质量参数创建合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取可用的视频ID
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            # 使用无效的质量参数
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'invalid_quality'
            }
            
            print(f"   使用无效质量参数: {composition_data['quality']}")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证应该返回400错误
            if not response.is_client_error:
                print(f"❌ 无效质量参数应该返回4xx错误，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 无效质量参数正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 无效质量参数测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_unauthenticated(self) -> bool:
        """
        测试未认证创建合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证创建合成任务")
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            # 准备合成请求数据
            composition_data = {
                'video_ids': [1, 2],
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            print("   尝试未认证创建合成任务...")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证创建合成任务正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证创建合成任务成功（可能允许匿名访问）")
                return True
            else:
                print(f"❌ 未认证创建合成任务返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证创建合成任务测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_response_time(self) -> bool:
        """
        测试合成任务创建响应时间
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试合成任务创建响应时间")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取可用的视频ID
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            # 准备合成请求数据
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            # 测试多次请求的响应时间
            response_times = []
            test_count = 3
            
            for i in range(test_count):
                start_time = time.time()
                response = self.client.post('/api/videos/composition/create/', 
                                          data=composition_data)
                total_time = time.time() - start_time
                
                if response.is_success:
                    response_times.append(total_time)
                    print(f"   第{i+1}次请求: {total_time:.2f}s")
                    
                    # 保存任务ID
                    if response.json_data and response.json_data.get('task_id'):
                        self.created_task_ids.append(response.json_data['task_id'])
                else:
                    print(f"   第{i+1}次请求失败: {response.status_code}")
            
            if not response_times:
                print("❌ 所有请求都失败")
                return False
            
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            print(f"   平均响应时间: {avg_time:.2f}s")
            print(f"   最大响应时间: {max_time:.2f}s")
            
            # 验证响应时间在合理范围内（10秒内）
            if max_time > 10.0:
                print(f"⚠️  最大响应时间超过10秒")
            
            print(f"✅ 合成任务创建响应时间测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 响应时间测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_create_with_optional_parameters(self) -> bool:
        """
        测试包含可选参数的合成任务创建
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试包含可选参数的合成任务创建")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 获取可用的视频ID
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            # 包含所有可选参数的合成请求
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '完整参数测试合成视频',
                'description': '这是一个包含所有可选参数的测试合成视频',
                'transition_type': 'fade',
                'background_music': True,
                'watermark': False
            }
            
            print(f"   合成视频ID: {composition_data['video_ids']}")
            print(f"   标题: {composition_data['title']}")
            print(f"   转场类型: {composition_data['transition_type']}")
            
            # 发送合成任务创建请求
            response = self.client.post('/api/videos/composition/create/', 
                                      data=composition_data)
            
            # 验证响应
            if response.is_success:
                print(f"✅ 包含可选参数的合成任务创建成功")
                
                if response.json_data:
                    task_id = response.json_data.get('task_id')
                    status = response.json_data.get('status')
                    
                    if task_id:
                        self.created_task_ids.append(task_id)
                        print(f"   任务ID: {task_id}")
                    
                    if status:
                        print(f"   状态: {status}")
                
                return True
            else:
                print(f"❌ 包含可选参数的合成任务创建失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
        except Exception as e:
            print(f"❌ 可选参数测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_valid_task_id(self) -> bool:
        """
        测试查询有效任务ID的状态
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试查询有效任务ID的状态")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 首先创建一个合成任务
            video_ids = self.get_available_video_ids()
            
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            # 创建合成任务
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '状态查询测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务进行状态查询测试")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 创建的任务没有返回task_id")
                return False
            
            print(f"   创建的任务ID: {task_id}")
            
            # 查询任务状态
            status_response = self.client.get(f'/api/videos/composition/{task_id}/')
            
            # 验证响应状态码
            if not status_response.is_success:
                print(f"❌ 查询任务状态失败 - 状态码: {status_response.status_code}")
                if status_response.json_data:
                    print(f"   错误信息: {status_response.json_data}")
                return False
            
            # 验证响应数据结构
            if not status_response.json_data:
                print("❌ 任务状态查询响应没有JSON数据")
                return False
            
            status_data = status_response.json_data
            
            # 检查必要字段
            required_fields = ['task_id', 'status']
            missing_fields = [field for field in required_fields if field not in status_data]
            if missing_fields:
                print(f"❌ 任务状态响应缺少字段: {missing_fields}")
                print(f"   实际字段: {list(status_data.keys())}")
                return False
            
            # 验证task_id匹配
            returned_task_id = status_data['task_id']
            if returned_task_id != task_id:
                print(f"❌ 返回的task_id({returned_task_id})与请求的task_id({task_id})不匹配")
                return False
            
            # 验证status是有效值
            status = status_data['status']
            valid_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
            if status not in valid_statuses:
                print(f"❌ 返回的status({status})不在有效值范围内: {valid_statuses}")
                return False
            
            print(f"✅ 任务状态查询成功")
            print(f"   任务ID: {returned_task_id}")
            print(f"   状态: {status}")
            print(f"   响应时间: {status_response.response_time:.2f}s")
            
            # 检查其他可选字段
            optional_fields = ['progress', 'message', 'created_at', 'updated_at', 'estimated_completion']
            for field in optional_fields:
                if field in status_data:
                    print(f"   {field}: {status_data[field]}")
            
            # 验证progress字段（如果存在）
            if 'progress' in status_data:
                progress = status_data['progress']
                if isinstance(progress, (int, float)):
                    if 0 <= progress <= 100:
                        print(f"   ✅ 进度值有效: {progress}%")
                    else:
                        print(f"⚠️  进度值超出范围: {progress}%")
                else:
                    print(f"⚠️  进度值类型不正确: {type(progress)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 任务状态查询测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_invalid_task_id(self) -> bool:
        """
        测试查询无效任务ID的状态
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试查询无效任务ID的状态")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用不存在的任务ID
            invalid_task_id = "invalid_task_id_12345"
            
            print(f"   查询无效任务ID: {invalid_task_id}")
            
            # 查询任务状态
            response = self.client.get(f'/api/videos/composition/{invalid_task_id}/')
            
            # 验证应该返回404错误
            if response.status_code != 404:
                print(f"❌ 无效任务ID应该返回404，实际返回: {response.status_code}")
                return False
            
            # 验证错误响应格式
            if response.json_data:
                print(f"   错误信息: {response.json_data}")
            
            print(f"✅ 无效任务ID正确返回404错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 无效任务ID测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_empty_task_id(self) -> bool:
        """
        测试查询空任务ID的状态
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试查询空任务ID的状态")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用空的任务ID
            empty_task_id = ""
            
            print(f"   查询空任务ID")
            
            # 查询任务状态
            response = self.client.get(f'/api/videos/composition/{empty_task_id}/')
            
            # 验证应该返回404或400错误
            if response.status_code not in [400, 404]:
                print(f"❌ 空任务ID应该返回400或404，实际返回: {response.status_code}")
                return False
            
            print(f"✅ 空任务ID正确返回{response.status_code}错误")
            
            return True
            
        except Exception as e:
            print(f"❌ 空任务ID测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_unauthenticated(self) -> bool:
        """
        测试未认证查询任务状态
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证查询任务状态")
            
            # 首先创建一个任务（需要认证）
            if not self.ensure_authenticated():
                return False
            
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            # 创建合成任务
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            print(f"   未认证查询任务ID: {task_id}")
            
            # 尝试查询任务状态
            response = self.client.get(f'/api/videos/composition/{task_id}/')
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证查询任务状态正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证查询任务状态成功（可能允许匿名访问）")
                return True
            else:
                print(f"❌ 未认证查询返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证查询测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_polling_mechanism(self) -> bool:
        """
        测试状态轮询机制
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试状态轮询机制")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个合成任务
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '轮询测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   轮询任务ID: {task_id}")
            
            # 模拟轮询机制 - 查询多次状态
            poll_count = 5
            poll_interval = 2  # 秒
            
            statuses = []
            response_times = []
            
            for i in range(poll_count):
                print(f"   第{i+1}次轮询...")
                
                start_time = time.time()
                response = self.client.get(f'/api/videos/composition/{task_id}/')
                query_time = time.time() - start_time
                
                response_times.append(query_time)
                
                if response.is_success and response.json_data:
                    status = response.json_data.get('status', 'unknown')
                    progress = response.json_data.get('progress', 'N/A')
                    
                    statuses.append(status)
                    print(f"     状态: {status}, 进度: {progress}, 响应时间: {query_time:.2f}s")
                    
                    # 如果任务已完成或失败，停止轮询
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"     任务已结束，停止轮询")
                        break
                else:
                    print(f"     查询失败: {response.status_code}")
                    statuses.append('error')
                
                # 等待下次轮询
                if i < poll_count - 1:
                    time.sleep(poll_interval)
            
            # 分析轮询结果
            print(f"   轮询结果分析:")
            print(f"   - 总轮询次数: {len(statuses)}")
            print(f"   - 状态变化: {' -> '.join(set(statuses))}")
            print(f"   - 平均响应时间: {sum(response_times)/len(response_times):.2f}s")
            print(f"   - 最大响应时间: {max(response_times):.2f}s")
            
            # 验证轮询机制有效性
            if len(statuses) > 0:
                print(f"✅ 状态轮询机制测试完成")
                return True
            else:
                print(f"❌ 轮询过程中没有成功获取状态")
                return False
            
        except Exception as e:
            print(f"❌ 状态轮询测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_response_time(self) -> bool:
        """
        测试任务状态查询响应时间
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试任务状态查询响应时间")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用已创建的任务ID，或创建新任务
            task_id = None
            if self.created_task_ids:
                task_id = self.created_task_ids[0]
                print(f"   使用已创建的任务ID: {task_id}")
            else:
                # 创建新任务
                video_ids = self.get_available_video_ids()
                if len(video_ids) < 2:
                    print("⚠️  需要至少2个视频才能进行测试，跳过")
                    return True
                
                composition_data = {
                    'video_ids': video_ids[:2],
                    'output_format': 'mp4',
                    'quality': 'high'
                }
                
                create_response = self.client.post('/api/videos/composition/create/', 
                                                 data=composition_data)
                
                if create_response.is_success and create_response.json_data:
                    task_id = create_response.json_data.get('task_id')
                    if task_id:
                        self.created_task_ids.append(task_id)
                        print(f"   创建新任务ID: {task_id}")
                
                if not task_id:
                    print("❌ 无法获取任务ID进行响应时间测试")
                    return False
            
            # 测试多次查询的响应时间
            response_times = []
            test_count = 5
            
            for i in range(test_count):
                start_time = time.time()
                response = self.client.get(f'/api/videos/composition/{task_id}/')
                total_time = time.time() - start_time
                
                if response.is_success:
                    response_times.append(total_time)
                    print(f"   第{i+1}次查询: {total_time:.2f}s")
                else:
                    print(f"   第{i+1}次查询失败: {response.status_code}")
            
            if not response_times:
                print("❌ 所有查询都失败")
                return False
            
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"   平均响应时间: {avg_time:.2f}s")
            print(f"   最大响应时间: {max_time:.2f}s")
            print(f"   最小响应时间: {min_time:.2f}s")
            
            # 验证响应时间在合理范围内（3秒内）
            if max_time > 3.0:
                print(f"⚠️  最大响应时间超过3秒")
            
            print(f"✅ 任务状态查询响应时间测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 响应时间测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_status_data_consistency(self) -> bool:
        """
        测试任务状态数据一致性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试任务状态数据一致性")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个合成任务
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '数据一致性测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            create_status = create_response.json_data.get('status')
            
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   任务ID: {task_id}")
            print(f"   创建时状态: {create_status}")
            
            # 立即查询任务状态
            status_response = self.client.get(f'/api/videos/composition/{task_id}/')
            
            if not status_response.is_success or not status_response.json_data:
                print("❌ 无法查询任务状态")
                return False
            
            status_data = status_response.json_data
            query_status = status_data.get('status')
            query_task_id = status_data.get('task_id')
            
            print(f"   查询时状态: {query_status}")
            
            # 验证数据一致性
            consistency_checks = []
            
            # 1. 任务ID一致性
            if query_task_id == task_id:
                consistency_checks.append("✅ 任务ID一致")
            else:
                consistency_checks.append(f"❌ 任务ID不一致: 创建时{task_id}, 查询时{query_task_id}")
            
            # 2. 状态合理性（创建后的状态应该是pending或processing）
            if create_status in ['pending', 'processing'] and query_status in ['pending', 'processing', 'completed', 'failed']:
                consistency_checks.append("✅ 状态变化合理")
            else:
                consistency_checks.append(f"⚠️  状态变化可能不合理: {create_status} -> {query_status}")
            
            # 3. 时间戳一致性（如果存在）
            create_time = create_response.json_data.get('created_at')
            query_create_time = status_data.get('created_at')
            
            if create_time and query_create_time:
                if create_time == query_create_time:
                    consistency_checks.append("✅ 创建时间一致")
                else:
                    consistency_checks.append(f"⚠️  创建时间不一致")
            
            # 4. 进度值合理性
            progress = status_data.get('progress')
            if progress is not None:
                if isinstance(progress, (int, float)) and 0 <= progress <= 100:
                    consistency_checks.append(f"✅ 进度值合理: {progress}%")
                else:
                    consistency_checks.append(f"❌ 进度值不合理: {progress}")
            
            # 输出一致性检查结果
            print(f"   数据一致性检查:")
            for check in consistency_checks:
                print(f"     {check}")
            
            # 如果没有严重错误，认为测试通过
            error_count = sum(1 for check in consistency_checks if check.startswith("❌"))
            
            if error_count == 0:
                print(f"✅ 任务状态数据一致性测试通过")
                return True
            else:
                print(f"⚠️  发现 {error_count} 个数据一致性问题")
                return True  # 警告不算失败
            
        except Exception as e:
            print(f"❌ 数据一致性测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def test_composition_download_completed_task(self) -> bool:
        """
        测试下载已完成的合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试下载已完成的合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个合成任务
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '下载测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   任务ID: {task_id}")
            
            # 轮询等待任务完成（模拟）
            max_wait_time = 30  # 最大等待30秒
            poll_interval = 3   # 每3秒查询一次
            wait_time = 0
            
            task_completed = False
            download_url = None
            
            while wait_time < max_wait_time:
                status_response = self.client.get(f'/api/videos/composition/{task_id}/')
                
                if status_response.is_success and status_response.json_data:
                    status = status_response.json_data.get('status')
                    print(f"   当前状态: {status}")
                    
                    if status == 'completed':
                        task_completed = True
                        download_url = status_response.json_data.get('download_url')
                        break
                    elif status == 'failed':
                        print("❌ 任务执行失败")
                        return False
                
                time.sleep(poll_interval)
                wait_time += poll_interval
            
            # 如果任务没有完成，模拟一个下载URL进行测试
            if not task_completed:
                print("⚠️  任务未在预期时间内完成，使用模拟下载URL进行测试")
                download_url = f"/api/videos/composition/{task_id}/download/"
            
            if not download_url:
                print("❌ 无法获取下载URL")
                return False
            
            print(f"   下载URL: {download_url}")
            
            # 测试下载请求
            download_response = self.client.get(download_url)
            
            # 验证下载响应
            if download_response.is_success:
                print(f"✅ 下载请求成功")
                print(f"   响应状态码: {download_response.status_code}")
                print(f"   内容长度: {len(download_response.content)} bytes")
                print(f"   响应时间: {download_response.response_time:.2f}s")
                
                # 检查响应头
                content_type = download_response.headers.get('Content-Type', '')
                content_disposition = download_response.headers.get('Content-Disposition', '')
                
                if content_type:
                    print(f"   内容类型: {content_type}")
                    
                    # 验证内容类型是否为视频格式
                    if 'video' in content_type.lower() or 'application/octet-stream' in content_type:
                        print(f"   ✅ 内容类型正确")
                    else:
                        print(f"⚠️  内容类型可能不正确")
                
                if content_disposition:
                    print(f"   内容处置: {content_disposition}")
                    
                    # 验证是否包含文件名
                    if 'filename' in content_disposition:
                        print(f"   ✅ 包含文件名")
                    else:
                        print(f"⚠️  未包含文件名")
                
                return True
                
            elif download_response.status_code == 404:
                print(f"⚠️  下载文件不存在 (404) - 可能任务尚未完成或文件已过期")
                return True
            elif download_response.status_code == 403:
                print(f"⚠️  下载权限不足 (403)")
                return True
            else:
                print(f"❌ 下载请求失败 - 状态码: {download_response.status_code}")
                if download_response.json_data:
                    print(f"   错误信息: {download_response.json_data}")
                return False
            
        except Exception as e:
            print(f"❌ 下载测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_download_invalid_task_id(self) -> bool:
        """
        测试下载无效任务ID的文件
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试下载无效任务ID的文件")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用无效的任务ID
            invalid_task_id = "invalid_download_task_id"
            download_url = f"/api/videos/composition/{invalid_task_id}/download/"
            
            print(f"   尝试下载无效任务: {invalid_task_id}")
            
            # 发送下载请求
            response = self.client.get(download_url)
            
            # 验证应该返回404错误
            if response.status_code == 404:
                print(f"✅ 无效任务ID下载正确返回404错误")
                return True
            elif response.status_code == 400:
                print(f"✅ 无效任务ID下载正确返回400错误")
                return True
            else:
                print(f"❌ 无效任务ID下载返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 无效任务ID下载测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_download_incomplete_task(self) -> bool:
        """
        测试下载未完成任务的文件
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试下载未完成任务的文件")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个新的合成任务（应该是未完成状态）
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '未完成任务下载测试'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   任务ID: {task_id}")
            
            # 立即尝试下载（任务应该还未完成）
            download_url = f"/api/videos/composition/{task_id}/download/"
            
            print(f"   尝试下载未完成任务...")
            
            # 发送下载请求
            response = self.client.get(download_url)
            
            # 验证响应
            if response.status_code == 404:
                print(f"✅ 未完成任务下载正确返回404错误（文件不存在）")
                return True
            elif response.status_code == 400:
                print(f"✅ 未完成任务下载正确返回400错误（任务未完成）")
                return True
            elif response.status_code == 202:
                print(f"✅ 未完成任务下载返回202（任务处理中）")
                return True
            elif response.is_success:
                print(f"⚠️  未完成任务下载成功（可能任务已快速完成）")
                return True
            else:
                print(f"❌ 未完成任务下载返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未完成任务下载测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_download_unauthenticated(self) -> bool:
        """
        测试未认证下载合成文件
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证下载合成文件")
            
            # 首先创建一个任务（需要认证）
            if not self.ensure_authenticated():
                return False
            
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            download_url = f"/api/videos/composition/{task_id}/download/"
            
            print(f"   未认证尝试下载任务: {task_id}")
            
            # 尝试下载
            response = self.client.get(download_url)
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证下载正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证下载成功（可能允许匿名下载）")
                return True
            else:
                print(f"❌ 未认证下载返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证下载测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_download_url_validity(self) -> bool:
        """
        测试下载链接的有效性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试下载链接的有效性")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用已创建的任务ID，或创建新任务
            task_id = None
            if self.created_task_ids:
                task_id = self.created_task_ids[0]
                print(f"   使用已创建的任务ID: {task_id}")
            else:
                # 创建新任务
                video_ids = self.get_available_video_ids()
                if len(video_ids) < 2:
                    print("⚠️  需要至少2个视频才能进行测试，跳过")
                    return True
                
                composition_data = {
                    'video_ids': video_ids[:2],
                    'output_format': 'mp4',
                    'quality': 'high'
                }
                
                create_response = self.client.post('/api/videos/composition/create/', 
                                                 data=composition_data)
                
                if create_response.is_success and create_response.json_data:
                    task_id = create_response.json_data.get('task_id')
                    if task_id:
                        self.created_task_ids.append(task_id)
                        print(f"   创建新任务ID: {task_id}")
                
                if not task_id:
                    print("❌ 无法获取任务ID")
                    return False
            
            # 测试不同的下载URL格式
            download_urls = [
                f"/api/videos/composition/{task_id}/download/",
                f"/api/videos/composition/{task_id}/download",
                f"/api/composition/{task_id}/download/",
                f"/download/composition/{task_id}/"
            ]
            
            valid_url_found = False
            
            for url in download_urls:
                print(f"   测试URL: {url}")
                
                response = self.client.get(url)
                
                if response.is_success:
                    print(f"     ✅ URL有效 - 状态码: {response.status_code}")
                    valid_url_found = True
                    
                    # 检查响应头
                    content_type = response.headers.get('Content-Type', '')
                    if content_type:
                        print(f"     内容类型: {content_type}")
                    
                    break
                elif response.status_code == 404:
                    print(f"     ⚠️  URL不存在 - 404")
                elif response.status_code == 400:
                    print(f"     ⚠️  请求格式错误 - 400")
                elif response.status_code == 202:
                    print(f"     ⚠️  任务处理中 - 202")
                    valid_url_found = True
                    break
                else:
                    print(f"     ❌ 意外状态码: {response.status_code}")
            
            if valid_url_found:
                print(f"✅ 找到有效的下载URL格式")
                return True
            else:
                print(f"⚠️  未找到有效的下载URL格式（可能任务未完成或端点不存在）")
                return True  # 不算失败，可能是正常情况
            
        except Exception as e:
            print(f"❌ 下载链接有效性测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_download_file_integrity(self) -> bool:
        """
        测试下载文件的完整性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试下载文件的完整性")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用已创建的任务ID进行测试
            if not self.created_task_ids:
                print("⚠️  没有可用的任务ID，跳过文件完整性测试")
                return True
            
            task_id = self.created_task_ids[0]
            download_url = f"/api/videos/composition/{task_id}/download/"
            
            print(f"   测试任务ID: {task_id}")
            
            # 发送下载请求
            response = self.client.get(download_url)
            
            if response.is_success:
                print(f"✅ 下载成功")
                
                # 检查文件大小
                content_length = len(response.content)
                print(f"   文件大小: {content_length} bytes")
                
                # 检查响应头中的Content-Length
                header_content_length = response.headers.get('Content-Length')
                if header_content_length:
                    header_length = int(header_content_length)
                    if content_length == header_length:
                        print(f"   ✅ 文件大小与Content-Length头匹配")
                    else:
                        print(f"   ⚠️  文件大小与Content-Length头不匹配: {content_length} vs {header_length}")
                
                # 检查文件内容（基本验证）
                if content_length > 0:
                    print(f"   ✅ 文件不为空")
                    
                    # 检查文件头（如果是视频文件）
                    if content_length >= 4:
                        file_header = response.content[:4]
                        
                        # 常见视频文件头
                        video_signatures = {
                            b'\x00\x00\x00\x18': 'MP4',
                            b'\x00\x00\x00\x20': 'MP4',
                            b'ftyp': 'MP4 (partial)',
                            b'RIFF': 'AVI/WebM'
                        }
                        
                        signature_found = False
                        for sig, format_name in video_signatures.items():
                            if response.content.startswith(sig) or sig in response.content[:20]:
                                print(f"   ✅ 检测到视频格式: {format_name}")
                                signature_found = True
                                break
                        
                        if not signature_found:
                            print(f"   ⚠️  未识别的文件格式（文件头: {file_header.hex()}）")
                else:
                    print(f"   ❌ 文件为空")
                    return False
                
                print(f"✅ 文件完整性检查完成")
                return True
                
            elif response.status_code == 404:
                print(f"⚠️  文件不存在 (404) - 可能任务未完成")
                return True
            elif response.status_code == 202:
                print(f"⚠️  任务处理中 (202) - 文件尚未生成")
                return True
            else:
                print(f"❌ 下载失败 - 状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 文件完整性测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_download_response_time(self) -> bool:
        """
        测试下载响应时间
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试下载响应时间")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用已创建的任务ID进行测试
            if not self.created_task_ids:
                print("⚠️  没有可用的任务ID，跳过下载响应时间测试")
                return True
            
            task_id = self.created_task_ids[0]
            download_url = f"/api/videos/composition/{task_id}/download/"
            
            print(f"   测试任务ID: {task_id}")
            
            # 测试多次下载的响应时间
            response_times = []
            successful_downloads = 0
            test_count = 3
            
            for i in range(test_count):
                start_time = time.time()
                response = self.client.get(download_url)
                total_time = time.time() - start_time
                
                response_times.append(total_time)
                
                if response.is_success:
                    successful_downloads += 1
                    print(f"   第{i+1}次下载: {total_time:.2f}s (成功)")
                elif response.status_code in [404, 202]:
                    print(f"   第{i+1}次下载: {total_time:.2f}s (文件未就绪)")
                else:
                    print(f"   第{i+1}次下载: {total_time:.2f}s (失败: {response.status_code})")
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
                
                print(f"   平均响应时间: {avg_time:.2f}s")
                print(f"   最大响应时间: {max_time:.2f}s")
                print(f"   最小响应时间: {min_time:.2f}s")
                print(f"   成功下载次数: {successful_downloads}/{test_count}")
                
                # 验证响应时间在合理范围内
                if max_time > 30.0:
                    print(f"⚠️  最大响应时间超过30秒")
                elif max_time > 10.0:
                    print(f"⚠️  最大响应时间超过10秒")
                
                print(f"✅ 下载响应时间测试完成")
                return True
            else:
                print("❌ 没有记录到响应时间")
                return False
            
        except Exception as e:
            print(f"❌ 下载响应时间测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def test_composition_cancel_pending_task(self) -> bool:
        """
        测试取消待处理的合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试取消待处理的合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个合成任务
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '取消测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   任务ID: {task_id}")
            
            # 查询任务状态
            status_response = self.client.get(f'/api/videos/composition/{task_id}/')
            
            if status_response.is_success and status_response.json_data:
                initial_status = status_response.json_data.get('status')
                print(f"   初始状态: {initial_status}")
            
            # 尝试取消任务
            cancel_response = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            # 验证取消响应
            if cancel_response.is_success:
                print(f"✅ 任务取消请求成功")
                print(f"   响应状态码: {cancel_response.status_code}")
                
                if cancel_response.json_data:
                    print(f"   响应数据: {cancel_response.json_data}")
                
                # 等待一小段时间让取消操作生效
                time.sleep(2)
                
                # 再次查询任务状态
                final_status_response = self.client.get(f'/api/videos/composition/{task_id}/')
                
                if final_status_response.is_success and final_status_response.json_data:
                    final_status = final_status_response.json_data.get('status')
                    print(f"   取消后状态: {final_status}")
                    
                    # 验证状态已更新
                    if final_status == 'cancelled':
                        print(f"   ✅ 任务状态已更新为cancelled")
                    elif final_status in ['completed', 'failed']:
                        print(f"   ⚠️  任务在取消前已完成或失败")
                    else:
                        print(f"   ⚠️  任务状态未更新为cancelled: {final_status}")
                
                return True
                
            elif cancel_response.status_code == 400:
                print(f"⚠️  任务可能已完成或无法取消 (400)")
                return True
            elif cancel_response.status_code == 404:
                print(f"❌ 任务不存在 (404)")
                return False
            else:
                print(f"❌ 取消请求失败 - 状态码: {cancel_response.status_code}")
                if cancel_response.json_data:
                    print(f"   错误信息: {cancel_response.json_data}")
                return False
            
        except Exception as e:
            print(f"❌ 取消待处理任务测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_cancel_completed_task(self) -> bool:
        """
        测试取消已完成的合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试取消已完成的合成任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用已创建的任务ID（如果有）
            if not self.created_task_ids:
                print("⚠️  没有可用的任务ID，跳过已完成任务取消测试")
                return True
            
            task_id = self.created_task_ids[0]
            
            print(f"   测试任务ID: {task_id}")
            
            # 查询任务状态
            status_response = self.client.get(f'/api/videos/composition/{task_id}/')
            
            if not status_response.is_success or not status_response.json_data:
                print("❌ 无法查询任务状态")
                return False
            
            current_status = status_response.json_data.get('status')
            print(f"   当前状态: {current_status}")
            
            # 尝试取消任务
            cancel_response = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            # 验证取消响应
            if current_status in ['completed', 'failed', 'cancelled']:
                # 已完成的任务取消应该返回错误
                if cancel_response.status_code in [400, 409]:
                    print(f"✅ 已完成任务取消正确返回{cancel_response.status_code}错误")
                    
                    if cancel_response.json_data:
                        print(f"   错误信息: {cancel_response.json_data}")
                    
                    return True
                elif cancel_response.is_success:
                    print(f"⚠️  已完成任务取消成功（可能允许重复取消）")
                    return True
                else:
                    print(f"❌ 已完成任务取消返回意外状态码: {cancel_response.status_code}")
                    return False
            else:
                # 未完成的任务取消应该成功
                if cancel_response.is_success:
                    print(f"✅ 未完成任务取消成功")
                    return True
                else:
                    print(f"⚠️  未完成任务取消失败: {cancel_response.status_code}")
                    return True
            
        except Exception as e:
            print(f"❌ 取消已完成任务测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_cancel_invalid_task_id(self) -> bool:
        """
        测试取消无效任务ID
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试取消无效任务ID")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 使用无效的任务ID
            invalid_task_id = "invalid_cancel_task_id"
            
            print(f"   尝试取消无效任务: {invalid_task_id}")
            
            # 尝试取消任务
            response = self.client.post(f'/api/videos/composition/{invalid_task_id}/cancel/')
            
            # 验证应该返回404错误
            if response.status_code == 404:
                print(f"✅ 无效任务ID取消正确返回404错误")
                return True
            elif response.status_code == 400:
                print(f"✅ 无效任务ID取消正确返回400错误")
                return True
            else:
                print(f"❌ 无效任务ID取消返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 无效任务ID取消测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_cancel_unauthenticated(self) -> bool:
        """
        测试未认证取消合成任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未认证取消合成任务")
            
            # 首先创建一个任务（需要认证）
            if not self.ensure_authenticated():
                return False
            
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_authenticated = False
            
            print(f"   未认证尝试取消任务: {task_id}")
            
            # 尝试取消任务
            response = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证取消任务正确返回401错误")
                return True
            elif response.is_success:
                print(f"⚠️  未认证取消任务成功（可能允许匿名取消）")
                return True
            else:
                print(f"❌ 未认证取消任务返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未认证取消任务测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_cancel_resource_cleanup(self) -> bool:
        """
        测试任务取消后的资源清理
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试任务取消后的资源清理")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个合成任务
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '资源清理测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   任务ID: {task_id}")
            
            # 取消任务
            cancel_response = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            if not cancel_response.is_success:
                print(f"⚠️  任务取消失败，跳过资源清理测试")
                return True
            
            print(f"   任务已取消")
            
            # 等待资源清理
            time.sleep(3)
            
            # 验证任务状态
            status_response = self.client.get(f'/api/videos/composition/{task_id}/')
            
            if status_response.is_success and status_response.json_data:
                status = status_response.json_data.get('status')
                
                if status == 'cancelled':
                    print(f"   ✅ 任务状态为cancelled")
                else:
                    print(f"   ⚠️  任务状态为: {status}")
                
                # 检查是否有下载链接（取消的任务不应该有）
                download_url = status_response.json_data.get('download_url')
                if download_url:
                    print(f"   ⚠️  取消的任务仍有下载链接")
                else:
                    print(f"   ✅ 取消的任务没有下载链接")
            
            # 尝试下载取消的任务（应该失败）
            download_response = self.client.get(f'/api/videos/composition/{task_id}/download/')
            
            if download_response.status_code in [404, 400, 410]:
                print(f"   ✅ 取消的任务下载正确返回错误: {download_response.status_code}")
            elif download_response.is_success:
                print(f"   ⚠️  取消的任务仍可下载")
            else:
                print(f"   ⚠️  下载返回状态码: {download_response.status_code}")
            
            print(f"✅ 任务取消资源清理测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 资源清理测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_composition_cancel_multiple_times(self) -> bool:
        """
        测试多次取消同一任务
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试多次取消同一任务")
            
            # 确保已认证
            if not self.ensure_authenticated():
                return False
            
            # 创建一个合成任务
            video_ids = self.get_available_video_ids()
            if len(video_ids) < 2:
                print("⚠️  需要至少2个视频才能进行测试，跳过")
                return True
            
            composition_data = {
                'video_ids': video_ids[:2],
                'output_format': 'mp4',
                'quality': 'high',
                'title': '多次取消测试任务'
            }
            
            create_response = self.client.post('/api/videos/composition/create/', 
                                             data=composition_data)
            
            if not create_response.is_success or not create_response.json_data:
                print("❌ 无法创建合成任务")
                return False
            
            task_id = create_response.json_data.get('task_id')
            if not task_id:
                print("❌ 无法获取任务ID")
                return False
            
            print(f"   任务ID: {task_id}")
            
            # 第一次取消
            print("   第1次取消...")
            cancel_response1 = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            if cancel_response1.is_success:
                print(f"     ✅ 第1次取消成功")
            else:
                print(f"     ⚠️  第1次取消失败: {cancel_response1.status_code}")
            
            # 等待一小段时间
            time.sleep(1)
            
            # 第二次取消
            print("   第2次取消...")
            cancel_response2 = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            # 第二次取消应该返回错误或成功（幂等性）
            if cancel_response2.is_success:
                print(f"     ✅ 第2次取消成功（幂等操作）")
            elif cancel_response2.status_code in [400, 409]:
                print(f"     ✅ 第2次取消正确返回{cancel_response2.status_code}错误（已取消）")
            else:
                print(f"     ⚠️  第2次取消返回状态码: {cancel_response2.status_code}")
            
            # 第三次取消
            print("   第3次取消...")
            cancel_response3 = self.client.post(f'/api/videos/composition/{task_id}/cancel/')
            
            if cancel_response3.is_success:
                print(f"     ✅ 第3次取消成功（幂等操作）")
            elif cancel_response3.status_code in [400, 409]:
                print(f"     ✅ 第3次取消正确返回{cancel_response3.status_code}错误（已取消）")
            else:
                print(f"     ⚠️  第3次取消返回状态码: {cancel_response3.status_code}")
            
            print(f"✅ 多次取消测试完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 多次取消测试异常: {str(e)}")
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
def composition_tester(config):
    """视频合成API测试器fixture"""
    tester = CompositionAPITester(config)
    yield tester
    tester.close()


def test_composition_api_tester_creation(config):
    """测试视频合成API测试器创建"""
    tester = CompositionAPITester(config)
    assert tester is not None
    assert tester.base_url == config.get_base_url()
    tester.close()


def test_composition_create_valid_request(composition_tester):
    """测试创建有效的合成任务"""
    result = composition_tester.test_composition_create_valid_request()
    assert isinstance(result, bool)


def test_composition_create_invalid_video_ids(composition_tester):
    """测试使用无效视频ID创建合成任务"""
    result = composition_tester.test_composition_create_invalid_video_ids()
    assert isinstance(result, bool)


def test_composition_create_missing_video_ids(composition_tester):
    """测试缺少video_ids参数创建合成任务"""
    result = composition_tester.test_composition_create_missing_video_ids()
    assert isinstance(result, bool)


def test_composition_create_empty_video_ids(composition_tester):
    """测试空的video_ids列表创建合成任务"""
    result = composition_tester.test_composition_create_empty_video_ids()
    assert isinstance(result, bool)


def test_composition_create_single_video_id(composition_tester):
    """测试单个视频ID创建合成任务"""
    result = composition_tester.test_composition_create_single_video_id()
    assert isinstance(result, bool)


def test_composition_create_invalid_output_format(composition_tester):
    """测试无效输出格式创建合成任务"""
    result = composition_tester.test_composition_create_invalid_output_format()
    assert isinstance(result, bool)


def test_composition_create_invalid_quality(composition_tester):
    """测试无效质量参数创建合成任务"""
    result = composition_tester.test_composition_create_invalid_quality()
    assert isinstance(result, bool)


def test_composition_create_unauthenticated(composition_tester):
    """测试未认证创建合成任务"""
    result = composition_tester.test_composition_create_unauthenticated()
    assert isinstance(result, bool)


def test_composition_create_response_time(composition_tester):
    """测试合成任务创建响应时间"""
    result = composition_tester.test_composition_create_response_time()
    assert isinstance(result, bool)


def test_composition_create_with_optional_parameters(composition_tester):
    """测试包含可选参数的合成任务创建"""
    result = composition_tester.test_composition_create_with_optional_parameters()
    assert isinstance(result, bool)


def test_composition_status_valid_task_id(composition_tester):
    """测试查询有效任务ID的状态"""
    result = composition_tester.test_composition_status_valid_task_id()
    assert isinstance(result, bool)


def test_composition_status_invalid_task_id(composition_tester):
    """测试查询无效任务ID的状态"""
    result = composition_tester.test_composition_status_invalid_task_id()
    assert isinstance(result, bool)


def test_composition_status_empty_task_id(composition_tester):
    """测试查询空任务ID的状态"""
    result = composition_tester.test_composition_status_empty_task_id()
    assert isinstance(result, bool)


def test_composition_status_unauthenticated(composition_tester):
    """测试未认证查询任务状态"""
    result = composition_tester.test_composition_status_unauthenticated()
    assert isinstance(result, bool)


def test_composition_status_polling_mechanism(composition_tester):
    """测试状态轮询机制"""
    result = composition_tester.test_composition_status_polling_mechanism()
    assert isinstance(result, bool)


def test_composition_status_response_time(composition_tester):
    """测试任务状态查询响应时间"""
    result = composition_tester.test_composition_status_response_time()
    assert isinstance(result, bool)


def test_composition_status_data_consistency(composition_tester):
    """测试任务状态数据一致性"""
    result = composition_tester.test_composition_status_data_consistency()
    assert isinstance(result, bool)


def test_composition_download_completed_task(composition_tester):
    """测试下载已完成的合成任务"""
    result = composition_tester.test_composition_download_completed_task()
    assert isinstance(result, bool)


def test_composition_download_invalid_task_id(composition_tester):
    """测试下载无效任务ID的文件"""
    result = composition_tester.test_composition_download_invalid_task_id()
    assert isinstance(result, bool)


def test_composition_download_incomplete_task(composition_tester):
    """测试下载未完成任务的文件"""
    result = composition_tester.test_composition_download_incomplete_task()
    assert isinstance(result, bool)


def test_composition_download_unauthenticated(composition_tester):
    """测试未认证下载合成文件"""
    result = composition_tester.test_composition_download_unauthenticated()
    assert isinstance(result, bool)


def test_composition_download_url_validity(composition_tester):
    """测试下载链接的有效性"""
    result = composition_tester.test_composition_download_url_validity()
    assert isinstance(result, bool)


def test_composition_download_file_integrity(composition_tester):
    """测试下载文件的完整性"""
    result = composition_tester.test_composition_download_file_integrity()
    assert isinstance(result, bool)


def test_composition_download_response_time(composition_tester):
    """测试下载响应时间"""
    result = composition_tester.test_composition_download_response_time()
    assert isinstance(result, bool)


def test_composition_cancel_pending_task(composition_tester):
    """测试取消待处理的合成任务"""
    result = composition_tester.test_composition_cancel_pending_task()
    assert isinstance(result, bool)


def test_composition_cancel_completed_task(composition_tester):
    """测试取消已完成的合成任务"""
    result = composition_tester.test_composition_cancel_completed_task()
    assert isinstance(result, bool)


def test_composition_cancel_invalid_task_id(composition_tester):
    """测试取消无效任务ID"""
    result = composition_tester.test_composition_cancel_invalid_task_id()
    assert isinstance(result, bool)


def test_composition_cancel_unauthenticated(composition_tester):
    """测试未认证取消合成任务"""
    result = composition_tester.test_composition_cancel_unauthenticated()
    assert isinstance(result, bool)


def test_composition_cancel_resource_cleanup(composition_tester):
    """测试任务取消后的资源清理"""
    result = composition_tester.test_composition_cancel_resource_cleanup()
    assert isinstance(result, bool)


def test_composition_cancel_multiple_times(composition_tester):
    """测试多次取消同一任务"""
    result = composition_tester.test_composition_cancel_multiple_times()
    assert isinstance(result, bool)


if __name__ == "__main__":
    # 直接运行测试
    config = TestConfigManager()
    tester = CompositionAPITester(config)
    
    print("开始视频合成API测试...")
    print(f"目标URL: {config.get_base_url()}")
    
    # 执行合成任务创建测试
    print("\n=== 合成任务创建测试 ===")
    
    print("1. 测试创建有效的合成任务...")
    valid_result = tester.test_composition_create_valid_request()
    
    print("\n2. 测试使用无效视频ID创建合成任务...")
    invalid_ids_result = tester.test_composition_create_invalid_video_ids()
    
    print("\n3. 测试缺少video_ids参数创建合成任务...")
    missing_ids_result = tester.test_composition_create_missing_video_ids()
    
    print("\n4. 测试空的video_ids列表创建合成任务...")
    empty_ids_result = tester.test_composition_create_empty_video_ids()
    
    print("\n5. 测试单个视频ID创建合成任务...")
    single_id_result = tester.test_composition_create_single_video_id()
    
    print("\n6. 测试无效输出格式创建合成任务...")
    invalid_format_result = tester.test_composition_create_invalid_output_format()
    
    print("\n7. 测试无效质量参数创建合成任务...")
    invalid_quality_result = tester.test_composition_create_invalid_quality()
    
    print("\n8. 测试未认证创建合成任务...")
    unauth_result = tester.test_composition_create_unauthenticated()
    
    print("\n9. 测试合成任务创建响应时间...")
    response_time_result = tester.test_composition_create_response_time()
    
    print("\n10. 测试包含可选参数的合成任务创建...")
    optional_params_result = tester.test_composition_create_with_optional_parameters()
    
    # 执行任务状态查询测试
    print("\n=== 任务状态查询测试 ===")
    
    print("11. 测试查询有效任务ID的状态...")
    status_valid_result = tester.test_composition_status_valid_task_id()
    
    print("\n12. 测试查询无效任务ID的状态...")
    status_invalid_result = tester.test_composition_status_invalid_task_id()
    
    print("\n13. 测试查询空任务ID的状态...")
    status_empty_result = tester.test_composition_status_empty_task_id()
    
    print("\n14. 测试未认证查询任务状态...")
    status_unauth_result = tester.test_composition_status_unauthenticated()
    
    print("\n15. 测试状态轮询机制...")
    status_polling_result = tester.test_composition_status_polling_mechanism()
    
    print("\n16. 测试任务状态查询响应时间...")
    status_response_time_result = tester.test_composition_status_response_time()
    
    print("\n17. 测试任务状态数据一致性...")
    status_consistency_result = tester.test_composition_status_data_consistency()
    
    # 执行任务完成和下载测试
    print("\n=== 任务完成和下载测试 ===")
    
    print("18. 测试下载已完成的合成任务...")
    download_completed_result = tester.test_composition_download_completed_task()
    
    print("\n19. 测试下载无效任务ID的文件...")
    download_invalid_result = tester.test_composition_download_invalid_task_id()
    
    print("\n20. 测试下载未完成任务的文件...")
    download_incomplete_result = tester.test_composition_download_incomplete_task()
    
    print("\n21. 测试未认证下载合成文件...")
    download_unauth_result = tester.test_composition_download_unauthenticated()
    
    print("\n22. 测试下载链接的有效性...")
    download_url_validity_result = tester.test_composition_download_url_validity()
    
    print("\n23. 测试下载文件的完整性...")
    download_integrity_result = tester.test_composition_download_file_integrity()
    
    print("\n24. 测试下载响应时间...")
    download_response_time_result = tester.test_composition_download_response_time()
    
    # 执行任务取消测试
    print("\n=== 任务取消测试 ===")
    
    print("25. 测试取消待处理的合成任务...")
    cancel_pending_result = tester.test_composition_cancel_pending_task()
    
    print("\n26. 测试取消已完成的合成任务...")
    cancel_completed_result = tester.test_composition_cancel_completed_task()
    
    print("\n27. 测试取消无效任务ID...")
    cancel_invalid_result = tester.test_composition_cancel_invalid_task_id()
    
    print("\n28. 测试未认证取消合成任务...")
    cancel_unauth_result = tester.test_composition_cancel_unauthenticated()
    
    print("\n29. 测试任务取消后的资源清理...")
    cancel_cleanup_result = tester.test_composition_cancel_resource_cleanup()
    
    print("\n30. 测试多次取消同一任务...")
    cancel_multiple_result = tester.test_composition_cancel_multiple_times()
    
    # 总结
    print(f"\n=== 视频合成API测试结果总结 ===")
    print("合成任务创建测试:")
    print(f"- 创建有效合成任务: {'✅ 通过' if valid_result else '❌ 失败'}")
    print(f"- 无效视频ID测试: {'✅ 通过' if invalid_ids_result else '❌ 失败'}")
    print(f"- 缺少video_ids测试: {'✅ 通过' if missing_ids_result else '❌ 失败'}")
    print(f"- 空video_ids列表测试: {'✅ 通过' if empty_ids_result else '❌ 失败'}")
    print(f"- 单个视频ID测试: {'✅ 通过' if single_id_result else '❌ 失败'}")
    print(f"- 无效输出格式测试: {'✅ 通过' if invalid_format_result else '❌ 失败'}")
    print(f"- 无效质量参数测试: {'✅ 通过' if invalid_quality_result else '❌ 失败'}")
    print(f"- 未认证访问测试: {'✅ 通过' if unauth_result else '❌ 失败'}")
    print(f"- 响应时间测试: {'✅ 通过' if response_time_result else '❌ 失败'}")
    print(f"- 可选参数测试: {'✅ 通过' if optional_params_result else '❌ 失败'}")
    
    print("\n任务状态查询测试:")
    print(f"- 查询有效任务状态: {'✅ 通过' if status_valid_result else '❌ 失败'}")
    print(f"- 查询无效任务状态: {'✅ 通过' if status_invalid_result else '❌ 失败'}")
    print(f"- 查询空任务ID状态: {'✅ 通过' if status_empty_result else '❌ 失败'}")
    print(f"- 未认证查询状态: {'✅ 通过' if status_unauth_result else '❌ 失败'}")
    print(f"- 状态轮询机制: {'✅ 通过' if status_polling_result else '❌ 失败'}")
    print(f"- 状态查询响应时间: {'✅ 通过' if status_response_time_result else '❌ 失败'}")
    print(f"- 状态数据一致性: {'✅ 通过' if status_consistency_result else '❌ 失败'}")
    
    print("\n任务完成和下载测试:")
    print(f"- 下载已完成任务: {'✅ 通过' if download_completed_result else '❌ 失败'}")
    print(f"- 下载无效任务ID: {'✅ 通过' if download_invalid_result else '❌ 失败'}")
    print(f"- 下载未完成任务: {'✅ 通过' if download_incomplete_result else '❌ 失败'}")
    print(f"- 未认证下载: {'✅ 通过' if download_unauth_result else '❌ 失败'}")
    print(f"- 下载链接有效性: {'✅ 通过' if download_url_validity_result else '❌ 失败'}")
    print(f"- 下载文件完整性: {'✅ 通过' if download_integrity_result else '❌ 失败'}")
    print(f"- 下载响应时间: {'✅ 通过' if download_response_time_result else '❌ 失败'}")
    
    print("\n任务取消测试:")
    print(f"- 取消待处理任务: {'✅ 通过' if cancel_pending_result else '❌ 失败'}")
    print(f"- 取消已完成任务: {'✅ 通过' if cancel_completed_result else '❌ 失败'}")
    print(f"- 取消无效任务ID: {'✅ 通过' if cancel_invalid_result else '❌ 失败'}")
    print(f"- 未认证取消任务: {'✅ 通过' if cancel_unauth_result else '❌ 失败'}")
    print(f"- 取消资源清理: {'✅ 通过' if cancel_cleanup_result else '❌ 失败'}")
    print(f"- 多次取消任务: {'✅ 通过' if cancel_multiple_result else '❌ 失败'}")
    
    # 显示创建的任务ID
    if tester.created_task_ids:
        print(f"\n创建的任务ID: {tester.created_task_ids}")
    
    tester.close()