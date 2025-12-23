"""
系统监控API测试模块

测试系统统计、存储信息、错误报告等监控功能。
"""

import pytest
import time
import json
import os
import sys
from typing import Dict, Any, List
from unittest.mock import patch, Mock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
from api_integration_tests.utils.test_helpers import TestDataGenerator


class MonitoringAPITester:
    """系统监控API测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化监控API测试器
        
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
        self.admin_user = self.test_data["admin_user"]
        self.valid_user = self.test_data["valid_user"]
        
        # 登录状态
        self.is_admin_authenticated = False
        self.is_user_authenticated = False
    
    def ensure_admin_authenticated(self) -> bool:
        """
        确保管理员已认证
        
        Returns:
            bool: 是否成功认证
        """
        if self.is_admin_authenticated and self.client.access_token:
            return True
        
        # 尝试管理员登录
        success = self.client.login(
            self.admin_user['username'],
            self.admin_user['password']
        )
        
        if success:
            self.is_admin_authenticated = True
            self.is_user_authenticated = False
            print(f"✅ 已登录管理员: {self.admin_user['username']}")
        else:
            print(f"❌ 管理员登录失败: {self.admin_user['username']}")
        
        return success
    
    def ensure_user_authenticated(self) -> bool:
        """
        确保普通用户已认证
        
        Returns:
            bool: 是否成功认证
        """
        if self.is_user_authenticated and self.client.access_token:
            return True
        
        # 尝试普通用户登录
        success = self.client.login(
            self.valid_user['username'],
            self.valid_user['password']
        )
        
        if success:
            self.is_user_authenticated = True
            self.is_admin_authenticated = False
            print(f"✅ 已登录普通用户: {self.valid_user['username']}")
        else:
            print(f"❌ 普通用户登录失败: {self.valid_user['username']}")
        
        return success
    
    def test_system_statistics_basic(self) -> bool:
        """
        测试基础系统统计信息获取
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试基础系统统计信息获取")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                print("❌ 需要管理员权限才能访问系统统计")
                return False
            
            # 发送系统统计请求
            response = self.client.get('/api/videos/admin/monitoring/statistics/')
            
            # 验证响应状态码
            if not response.is_success:
                print(f"❌ 获取系统统计失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 系统统计响应没有JSON数据")
                return False
            
            data = response.json_data
            
            # 检查必要的统计字段
            expected_sections = ['users', 'videos', 'compositions', 'playbacks', 'storage']
            missing_sections = [section for section in expected_sections if section not in data]
            
            if missing_sections:
                print(f"❌ 系统统计响应缺少部分: {missing_sections}")
                print(f"   实际部分: {list(data.keys())}")
                return False
            
            # 验证用户统计
            users_stats = data['users']
            user_fields = ['total', 'admins', 'active_30d']
            missing_user_fields = [field for field in user_fields if field not in users_stats]
            if missing_user_fields:
                print(f"❌ 用户统计缺少字段: {missing_user_fields}")
                return False
            
            # 验证视频统计
            videos_stats = data['videos']
            video_fields = ['total', 'uploaded_30d', 'total_views', 'avg_views_per_video']
            missing_video_fields = [field for field in video_fields if field not in videos_stats]
            if missing_video_fields:
                print(f"❌ 视频统计缺少字段: {missing_video_fields}")
                return False
            
            # 验证合成任务统计
            compositions_stats = data['compositions']
            composition_fields = ['total', 'successful', 'failed', 'success_rate', 'recent_7d']
            missing_composition_fields = [field for field in composition_fields if field not in compositions_stats]
            if missing_composition_fields:
                print(f"❌ 合成任务统计缺少字段: {missing_composition_fields}")
                return False
            
            # 验证播放统计
            playbacks_stats = data['playbacks']
            playback_fields = ['total', 'completed', 'completion_rate', 'avg_completion_percentage']
            missing_playback_fields = [field for field in playback_fields if field not in playbacks_stats]
            if missing_playback_fields:
                print(f"❌ 播放统计缺少字段: {missing_playback_fields}")
                return False
            
            # 验证存储统计
            storage_stats = data['storage']
            if storage_stats:  # 存储统计可能为None
                storage_fields = ['disk_total', 'disk_used', 'disk_free', 'disk_usage_percent']
                missing_storage_fields = [field for field in storage_fields if field not in storage_stats]
                if missing_storage_fields:
                    print(f"⚠️  存储统计缺少字段: {missing_storage_fields}")
            
            print(f"✅ 系统统计信息获取成功")
            print(f"   用户总数: {users_stats['total']}")
            print(f"   管理员数: {users_stats['admins']}")
            print(f"   视频总数: {videos_stats['total']}")
            print(f"   合成任务总数: {compositions_stats['total']}")
            print(f"   播放记录总数: {playbacks_stats['total']}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ 系统统计测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_system_statistics_data_accuracy(self) -> bool:
        """
        测试系统统计数据的准确性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试系统统计数据的准确性")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                return False
            
            # 获取系统统计
            response = self.client.get('/api/videos/admin/monitoring/statistics/')
            
            if not response.is_success or not response.json_data:
                print("❌ 无法获取系统统计数据")
                return False
            
            data = response.json_data
            
            # 验证数据类型和合理性
            users_stats = data['users']
            
            # 验证用户数据类型
            if not isinstance(users_stats['total'], int) or users_stats['total'] < 0:
                print(f"❌ 用户总数数据类型或值不正确: {users_stats['total']}")
                return False
            
            if not isinstance(users_stats['admins'], int) or users_stats['admins'] < 0:
                print(f"❌ 管理员数数据类型或值不正确: {users_stats['admins']}")
                return False
            
            # 管理员数不应该超过总用户数
            if users_stats['admins'] > users_stats['total']:
                print(f"❌ 管理员数({users_stats['admins']})超过总用户数({users_stats['total']})")
                return False
            
            # 验证视频数据
            videos_stats = data['videos']
            
            if not isinstance(videos_stats['total'], int) or videos_stats['total'] < 0:
                print(f"❌ 视频总数数据类型或值不正确: {videos_stats['total']}")
                return False
            
            if not isinstance(videos_stats['total_views'], int) or videos_stats['total_views'] < 0:
                print(f"❌ 总观看数数据类型或值不正确: {videos_stats['total_views']}")
                return False
            
            # 验证平均观看数的计算
            expected_avg = videos_stats['total_views'] / videos_stats['total'] if videos_stats['total'] > 0 else 0
            actual_avg = videos_stats['avg_views_per_video']
            
            if abs(actual_avg - expected_avg) > 0.01:  # 允许小数点误差
                print(f"❌ 平均观看数计算错误: 期望{expected_avg:.2f}, 实际{actual_avg:.2f}")
                return False
            
            # 验证合成任务数据
            compositions_stats = data['compositions']
            
            total_compositions = compositions_stats['total']
            successful = compositions_stats['successful']
            failed = compositions_stats['failed']
            
            # 成功和失败的任务数不应该超过总数
            if successful + failed > total_compositions:
                print(f"❌ 成功({successful})和失败({failed})任务数之和超过总数({total_compositions})")
                return False
            
            # 验证成功率计算
            expected_success_rate = (successful / total_compositions * 100) if total_compositions > 0 else 0
            actual_success_rate = compositions_stats['success_rate']
            
            if abs(actual_success_rate - expected_success_rate) > 0.01:
                print(f"❌ 成功率计算错误: 期望{expected_success_rate:.2f}%, 实际{actual_success_rate:.2f}%")
                return False
            
            # 验证播放数据
            playbacks_stats = data['playbacks']
            
            total_playbacks = playbacks_stats['total']
            completed_playbacks = playbacks_stats['completed']
            
            # 完成的播放数不应该超过总数
            if completed_playbacks > total_playbacks:
                print(f"❌ 完成播放数({completed_playbacks})超过总播放数({total_playbacks})")
                return False
            
            # 验证完成率计算
            expected_completion_rate = (completed_playbacks / total_playbacks * 100) if total_playbacks > 0 else 0
            actual_completion_rate = playbacks_stats['completion_rate']
            
            if abs(actual_completion_rate - expected_completion_rate) > 0.01:
                print(f"❌ 完成率计算错误: 期望{expected_completion_rate:.2f}%, 实际{actual_completion_rate:.2f}%")
                return False
            
            print(f"✅ 系统统计数据准确性验证通过")
            
            return True
            
        except Exception as e:
            print(f"❌ 数据准确性测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_system_statistics_unauthorized(self) -> bool:
        """
        测试未授权访问系统统计
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试未授权访问系统统计")
            
            # 清除认证状态
            self.client.clear_auth()
            self.is_admin_authenticated = False
            self.is_user_authenticated = False
            
            # 尝试访问系统统计
            response = self.client.get('/api/videos/admin/monitoring/statistics/')
            
            # 应该返回401错误
            if response.status_code == 401:
                print(f"✅ 未认证访问正确返回401错误")
                return True
            else:
                print(f"❌ 未认证访问返回意外状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 未授权访问测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_system_statistics_non_admin(self) -> bool:
        """
        测试非管理员用户访问系统统计
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试非管理员用户访问系统统计")
            
            # 确保普通用户已认证
            if not self.ensure_user_authenticated():
                return False
            
            # 尝试访问系统统计
            response = self.client.get('/api/videos/admin/monitoring/statistics/')
            
            # 应该返回403错误（权限不足）
            if response.status_code == 403:
                print(f"✅ 非管理员访问正确返回403错误")
                return True
            elif response.status_code == 401:
                print(f"✅ 非管理员访问返回401错误（也是合理的）")
                return True
            else:
                print(f"❌ 非管理员访问返回意外状态码: {response.status_code}")
                if response.json_data:
                    print(f"   响应内容: {response.json_data}")
                return False
            
        except Exception as e:
            print(f"❌ 非管理员访问测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_storage_info_basic(self) -> bool:
        """
        测试基础存储信息获取
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试基础存储信息获取")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                print("❌ 需要管理员权限才能访问存储信息")
                return False
            
            # 发送存储信息请求
            response = self.client.get('/api/videos/admin/monitoring/storage/')
            
            # 验证响应状态码
            if not response.is_success:
                print(f"❌ 获取存储信息失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 存储信息响应没有JSON数据")
                return False
            
            data = response.json_data
            
            # 检查必要的存储字段
            expected_fields = [
                'disk_total', 'disk_used', 'disk_free', 'disk_usage_percent',
                'video_files_size', 'composed_files_size', 'total_media_size',
                'warning_threshold', 'critical_threshold'
            ]
            
            missing_fields = [field for field in expected_fields if field not in data]
            if missing_fields:
                print(f"❌ 存储信息响应缺少字段: {missing_fields}")
                print(f"   实际字段: {list(data.keys())}")
                return False
            
            # 验证数据类型和合理性
            if not isinstance(data['disk_total'], int) or data['disk_total'] <= 0:
                print(f"❌ 磁盘总容量数据不正确: {data['disk_total']}")
                return False
            
            if not isinstance(data['disk_used'], int) or data['disk_used'] < 0:
                print(f"❌ 磁盘已用容量数据不正确: {data['disk_used']}")
                return False
            
            if not isinstance(data['disk_free'], int) or data['disk_free'] < 0:
                print(f"❌ 磁盘可用容量数据不正确: {data['disk_free']}")
                return False
            
            # 验证磁盘容量计算
            if abs(data['disk_total'] - (data['disk_used'] + data['disk_free'])) > 1024:  # 允许1KB误差
                print(f"❌ 磁盘容量计算不一致")
                print(f"   总容量: {data['disk_total']}")
                print(f"   已用: {data['disk_used']}")
                print(f"   可用: {data['disk_free']}")
                print(f"   已用+可用: {data['disk_used'] + data['disk_free']}")
                return False
            
            # 验证使用率计算
            expected_usage_percent = (data['disk_used'] / data['disk_total']) * 100
            actual_usage_percent = data['disk_usage_percent']
            
            if abs(actual_usage_percent - expected_usage_percent) > 0.1:
                print(f"❌ 磁盘使用率计算错误: 期望{expected_usage_percent:.2f}%, 实际{actual_usage_percent:.2f}%")
                return False
            
            print(f"✅ 存储信息获取成功")
            print(f"   磁盘总容量: {data['disk_total'] / (1024**3):.2f} GB")
            print(f"   磁盘已用: {data['disk_used'] / (1024**3):.2f} GB")
            print(f"   磁盘可用: {data['disk_free'] / (1024**3):.2f} GB")
            print(f"   使用率: {data['disk_usage_percent']:.2f}%")
            print(f"   视频文件大小: {data['video_files_size'] / (1024**2):.2f} MB")
            print(f"   合成文件大小: {data['composed_files_size'] / (1024**2):.2f} MB")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            # 检查警告信息
            if 'warnings' in data and data['warnings']:
                print(f"   ⚠️  存储警告: {len(data['warnings'])} 个")
                for warning in data['warnings']:
                    print(f"      - {warning.get('level', 'unknown')}: {warning.get('message', '')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 存储信息测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_storage_info_calculation_accuracy(self) -> bool:
        """
        测试存储信息计算的准确性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试存储信息计算的准确性")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                return False
            
            # 获取存储信息
            response = self.client.get('/api/videos/admin/monitoring/storage/')
            
            if not response.is_success or not response.json_data:
                print("❌ 无法获取存储信息")
                return False
            
            data = response.json_data
            
            # 验证总媒体大小计算
            expected_total_media = data['video_files_size'] + data['composed_files_size']
            actual_total_media = data['total_media_size']
            
            if actual_total_media != expected_total_media:
                print(f"❌ 总媒体大小计算错误")
                print(f"   视频文件: {data['video_files_size']}")
                print(f"   合成文件: {data['composed_files_size']}")
                print(f"   期望总计: {expected_total_media}")
                print(f"   实际总计: {actual_total_media}")
                return False
            
            # 验证阈值设置合理性
            warning_threshold = data['warning_threshold']
            critical_threshold = data['critical_threshold']
            
            if warning_threshold >= critical_threshold:
                print(f"❌ 警告阈值({warning_threshold})应该小于严重阈值({critical_threshold})")
                return False
            
            if warning_threshold <= 0 or warning_threshold > 100:
                print(f"❌ 警告阈值({warning_threshold})应该在0-100之间")
                return False
            
            if critical_threshold <= 0 or critical_threshold > 100:
                print(f"❌ 严重阈值({critical_threshold})应该在0-100之间")
                return False
            
            # 验证警告逻辑
            usage_percent = data['disk_usage_percent']
            warnings = data.get('warnings', [])
            
            if usage_percent >= critical_threshold:
                # 应该有严重警告
                has_critical = any(w.get('level') == 'critical' for w in warnings)
                if not has_critical:
                    print(f"❌ 使用率{usage_percent:.1f}%超过严重阈值{critical_threshold}%，但没有严重警告")
                    return False
            elif usage_percent >= warning_threshold:
                # 应该有警告
                has_warning = any(w.get('level') in ['warning', 'critical'] for w in warnings)
                if not has_warning:
                    print(f"❌ 使用率{usage_percent:.1f}%超过警告阈值{warning_threshold}%，但没有警告")
                    return False
            
            print(f"✅ 存储信息计算准确性验证通过")
            
            return True
            
        except Exception as e:
            print(f"❌ 存储计算准确性测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_error_statistics_basic(self) -> bool:
        """
        测试基础错误统计信息获取
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试基础错误统计信息获取")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                print("❌ 需要管理员权限才能访问错误统计")
                return False
            
            # 发送错误统计请求
            response = self.client.get('/api/monitoring/errors/')
            
            # 验证响应状态码
            if not response.is_success:
                print(f"❌ 获取错误统计失败 - 状态码: {response.status_code}")
                if response.json_data:
                    print(f"   错误信息: {response.json_data}")
                return False
            
            # 验证响应数据结构
            if not response.json_data:
                print("❌ 错误统计响应没有JSON数据")
                return False
            
            data = response.json_data
            
            # 检查响应格式
            if 'message' not in data or 'data' not in data:
                print(f"❌ 错误统计响应格式不正确")
                print(f"   实际字段: {list(data.keys())}")
                return False
            
            error_stats = data['data']
            
            # 检查错误统计的基本字段
            expected_fields = ['total_errors', 'error_types', 'recent_errors', 'error_rate']
            
            for field in expected_fields:
                if field not in error_stats:
                    print(f"⚠️  错误统计可能缺少字段: {field}")
            
            # 验证数据类型
            if 'total_errors' in error_stats:
                if not isinstance(error_stats['total_errors'], int) or error_stats['total_errors'] < 0:
                    print(f"❌ 总错误数数据类型或值不正确: {error_stats['total_errors']}")
                    return False
            
            if 'error_types' in error_stats:
                if not isinstance(error_stats['error_types'], (list, dict)):
                    print(f"❌ 错误类型数据类型不正确: {type(error_stats['error_types'])}")
                    return False
            
            print(f"✅ 错误统计信息获取成功")
            print(f"   总错误数: {error_stats.get('total_errors', 'N/A')}")
            print(f"   错误类型数: {len(error_stats.get('error_types', []))}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ 错误统计测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_error_statistics_time_range(self) -> bool:
        """
        测试错误统计的时间范围参数
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试错误统计的时间范围参数")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                return False
            
            # 测试不同的时间范围
            time_ranges = [1, 6, 24, 72]  # 1小时、6小时、24小时、72小时
            
            for hours in time_ranges:
                print(f"   测试 {hours} 小时范围...")
                
                response = self.client.get('/api/monitoring/errors/', params={'hours': hours})
                
                if not response.is_success:
                    print(f"❌ {hours}小时范围请求失败 - 状态码: {response.status_code}")
                    return False
                
                if not response.json_data or 'data' not in response.json_data:
                    print(f"❌ {hours}小时范围响应格式错误")
                    return False
                
                print(f"   ✅ {hours}小时范围: 响应时间 {response.response_time:.2f}s")
            
            print(f"✅ 错误统计时间范围参数测试通过")
            
            return True
            
        except Exception as e:
            print(f"❌ 时间范围参数测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_error_statistics_data_format(self) -> bool:
        """
        测试错误统计数据格式的完整性
        
        Returns:
            bool: 测试是否通过
        """
        try:
            print("测试错误统计数据格式的完整性")
            
            # 确保管理员已认证
            if not self.ensure_admin_authenticated():
                return False
            
            # 获取错误统计
            response = self.client.get('/api/monitoring/errors/')
            
            if not response.is_success or not response.json_data:
                print("❌ 无法获取错误统计数据")
                return False
            
            data = response.json_data['data']
            
            # 验证错误类型数据格式
            if 'error_types' in data and data['error_types']:
                error_types = data['error_types']
                
                if isinstance(error_types, list):
                    # 如果是列表，检查每个元素
                    for error_type in error_types:
                        if isinstance(error_type, dict):
                            # 检查错误类型对象的字段
                            if 'type' not in error_type and 'name' not in error_type:
                                print(f"⚠️  错误类型对象缺少类型名称字段")
                            if 'count' not in error_type:
                                print(f"⚠️  错误类型对象缺少计数字段")
                
                elif isinstance(error_types, dict):
                    # 如果是字典，检查值的类型
                    for error_name, error_count in error_types.items():
                        if not isinstance(error_count, int) or error_count < 0:
                            print(f"⚠️  错误类型 {error_name} 的计数值不正确: {error_count}")
            
            # 验证最近错误数据格式
            if 'recent_errors' in data and data['recent_errors']:
                recent_errors = data['recent_errors']
                
                if isinstance(recent_errors, list):
                    for error in recent_errors[:3]:  # 只检查前3个
                        if isinstance(error, dict):
                            # 检查错误对象的基本字段
                            expected_error_fields = ['timestamp', 'type', 'message']
                            for field in expected_error_fields:
                                if field not in error:
                                    print(f"⚠️  最近错误对象缺少字段: {field}")
            
            print(f"✅ 错误统计数据格式验证完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 数据格式测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


# 测试函数
def test_system_statistics_api():
    """测试系统统计API"""
    config = TestConfigManager()
    tester = MonitoringAPITester(config)
    
    print("=" * 60)
    print("系统统计API测试")
    print("=" * 60)
    
    results = []
    
    # 基础功能测试
    results.append(tester.test_system_statistics_basic())
    results.append(tester.test_system_statistics_data_accuracy())
    
    # 权限测试
    results.append(tester.test_system_statistics_unauthorized())
    results.append(tester.test_system_statistics_non_admin())
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n系统统计API测试完成: {success_count}/{total_count} 通过")
    
    return success_count == total_count


def test_storage_info_api():
    """测试存储信息API"""
    config = TestConfigManager()
    tester = MonitoringAPITester(config)
    
    print("=" * 60)
    print("存储信息API测试")
    print("=" * 60)
    
    results = []
    
    # 基础功能测试
    results.append(tester.test_storage_info_basic())
    results.append(tester.test_storage_info_calculation_accuracy())
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n存储信息API测试完成: {success_count}/{total_count} 通过")
    
    return success_count == total_count


def test_error_statistics_api():
    """测试错误统计API"""
    config = TestConfigManager()
    tester = MonitoringAPITester(config)
    
    print("=" * 60)
    print("错误统计API测试")
    print("=" * 60)
    
    results = []
    
    # 基础功能测试
    results.append(tester.test_error_statistics_basic())
    results.append(tester.test_error_statistics_time_range())
    results.append(tester.test_error_statistics_data_format())
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n错误统计API测试完成: {success_count}/{total_count} 通过")
    
    return success_count == total_count


if __name__ == "__main__":
    # 运行所有监控API测试
    all_results = []
    
    all_results.append(test_system_statistics_api())
    all_results.append(test_storage_info_api())
    all_results.append(test_error_statistics_api())
    
    total_success = sum(all_results)
    total_tests = len(all_results)
    
    print("=" * 60)
    print(f"监控API测试总结: {total_success}/{total_tests} 个测试套件通过")
    print("=" * 60)
    
    if total_success == total_tests:
        print("✅ 所有监控API测试通过")
        exit(0)
    else:
        print("❌ 部分监控API测试失败")
        exit(1)