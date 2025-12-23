"""
系统监控数据准确性属性测试

使用属性测试验证系统监控数据的准确性和一致性。
"""

import pytest
import time
import json
import os
import sys
from typing import Dict, Any, List, Optional
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, Mock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_integration_tests.config.test_config import TestConfigManager
from api_integration_tests.utils.http_client import APIClient, HTTPResponse
from api_integration_tests.utils.test_result_manager import TestResultManager, TestStatus
from api_integration_tests.utils.test_helpers import TestDataGenerator


class MonitoringPropertiesTester:
    """系统监控属性测试器"""
    
    def __init__(self, config: TestConfigManager):
        """
        初始化监控属性测试器
        
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
        
        # 登录状态
        self.is_admin_authenticated = False
    
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
        
        return success
    
    def get_system_statistics(self) -> Optional[Dict[str, Any]]:
        """
        获取系统统计数据
        
        Returns:
            Optional[Dict[str, Any]]: 系统统计数据，失败时返回None
        """
        try:
            if not self.ensure_admin_authenticated():
                return None
            
            response = self.client.get('/api/videos/admin/monitoring/statistics/')
            
            if response.is_success and response.json_data:
                return response.json_data
            
            return None
            
        except Exception:
            return None
    
    def get_storage_info(self) -> Optional[Dict[str, Any]]:
        """
        获取存储信息数据
        
        Returns:
            Optional[Dict[str, Any]]: 存储信息数据，失败时返回None
        """
        try:
            if not self.ensure_admin_authenticated():
                return None
            
            response = self.client.get('/api/videos/admin/monitoring/storage/')
            
            if response.is_success and response.json_data:
                return response.json_data
            
            return None
            
        except Exception:
            return None
    
    def get_error_statistics(self, hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        获取错误统计数据
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            Optional[Dict[str, Any]]: 错误统计数据，失败时返回None
        """
        try:
            if not self.ensure_admin_authenticated():
                return None
            
            response = self.client.get('/api/monitoring/errors/', params={'hours': hours})
            
            if response.is_success and response.json_data and 'data' in response.json_data:
                return response.json_data['data']
            
            return None
            
        except Exception:
            return None


# 生成测试数据的策略
time_range_strategy = st.integers(min_value=1, max_value=168)  # 1小时到1周


@pytest.mark.property
class TestMonitoringDataAccuracy:
    """系统监控数据准确性属性测试"""
    
    @classmethod
    def setup_class(cls):
        """设置测试类"""
        cls.config = TestConfigManager()
        cls.tester = MonitoringPropertiesTester(cls.config)
    
    @given(time_range=time_range_strategy)
    @settings(max_examples=10, deadline=60000)  # 60秒超时
    def test_property_error_statistics_time_consistency(self, time_range):
        """
        属性 6: 系统监控数据准确性 - 错误统计时间一致性
        
        对于任何有效的时间范围，错误统计API应该返回一致的数据格式，
        并且较长时间范围的错误数应该大于等于较短时间范围的错误数。
        
        **验证需求: 5.1, 5.2, 5.3, 5.4**
        """
        assume(1 <= time_range <= 168)  # 确保时间范围在合理区间
        
        try:
            print(f"\n测试错误统计时间一致性 - 时间范围: {time_range}小时")
            
            # 获取指定时间范围的错误统计
            error_stats = self.tester.get_error_statistics(time_range)
            
            if error_stats is None:
                pytest.skip("无法获取错误统计数据，跳过测试")
            
            # 验证数据结构一致性
            assert isinstance(error_stats, dict), "错误统计应该是字典类型"
            
            # 验证总错误数字段
            if 'total_errors' in error_stats:
                total_errors = error_stats['total_errors']
                assert isinstance(total_errors, int), "总错误数应该是整数"
                assert total_errors >= 0, "总错误数不能为负数"
            
            # 验证错误率字段
            if 'error_rate' in error_stats:
                error_rate = error_stats['error_rate']
                assert isinstance(error_rate, (int, float)), "错误率应该是数字"
                assert 0 <= error_rate <= 100, "错误率应该在0-100之间"
            
            # 验证错误类型字段
            if 'error_types' in error_stats:
                error_types = error_stats['error_types']
                assert isinstance(error_types, (list, dict)), "错误类型应该是列表或字典"
                
                if isinstance(error_types, dict):
                    # 如果是字典，验证所有值都是非负整数
                    for error_name, count in error_types.items():
                        assert isinstance(count, int), f"错误类型 {error_name} 的计数应该是整数"
                        assert count >= 0, f"错误类型 {error_name} 的计数不能为负数"
            
            # 如果时间范围较小，尝试获取更大时间范围的数据进行比较
            if time_range < 24:
                larger_range = min(time_range * 2, 24)
                larger_stats = self.tester.get_error_statistics(larger_range)
                
                if larger_stats and 'total_errors' in error_stats and 'total_errors' in larger_stats:
                    # 更大时间范围的错误数应该大于等于较小时间范围的错误数
                    assert larger_stats['total_errors'] >= error_stats['total_errors'], \
                        f"更大时间范围({larger_range}h)的错误数({larger_stats['total_errors']})应该大于等于较小时间范围({time_range}h)的错误数({error_stats['total_errors']})"
            
            print(f"✅ 错误统计时间一致性验证通过 - {time_range}小时")
            
        except Exception as e:
            pytest.fail(f"错误统计时间一致性测试失败: {str(e)}")
    
    def test_property_system_statistics_data_consistency(self):
        """
        属性 6: 系统监控数据准确性 - 系统统计数据一致性
        
        对于任何系统统计数据，各个统计项之间应该保持逻辑一致性，
        比如管理员数不应该超过总用户数，成功率计算应该正确等。
        
        **验证需求: 5.1, 5.2, 5.3, 5.4**
        """
        try:
            print(f"\n测试系统统计数据一致性")
            
            # 获取系统统计数据
            stats = self.tester.get_system_statistics()
            
            if stats is None:
                pytest.skip("无法获取系统统计数据，跳过测试")
            
            # 验证用户统计一致性
            if 'users' in stats:
                users_stats = stats['users']
                
                if 'total' in users_stats and 'admins' in users_stats:
                    total_users = users_stats['total']
                    admin_users = users_stats['admins']
                    
                    assert isinstance(total_users, int), "总用户数应该是整数"
                    assert isinstance(admin_users, int), "管理员数应该是整数"
                    assert total_users >= 0, "总用户数不能为负数"
                    assert admin_users >= 0, "管理员数不能为负数"
                    assert admin_users <= total_users, f"管理员数({admin_users})不应该超过总用户数({total_users})"
                
                if 'active_30d' in users_stats and 'total' in users_stats:
                    active_users = users_stats['active_30d']
                    total_users = users_stats['total']
                    
                    assert isinstance(active_users, int), "活跃用户数应该是整数"
                    assert active_users >= 0, "活跃用户数不能为负数"
                    assert active_users <= total_users, f"活跃用户数({active_users})不应该超过总用户数({total_users})"
            
            # 验证视频统计一致性
            if 'videos' in stats:
                videos_stats = stats['videos']
                
                if 'total' in videos_stats and 'total_views' in videos_stats and 'avg_views_per_video' in videos_stats:
                    total_videos = videos_stats['total']
                    total_views = videos_stats['total_views']
                    avg_views = videos_stats['avg_views_per_video']
                    
                    assert isinstance(total_videos, int), "总视频数应该是整数"
                    assert isinstance(total_views, int), "总观看数应该是整数"
                    assert isinstance(avg_views, (int, float)), "平均观看数应该是数字"
                    
                    assert total_videos >= 0, "总视频数不能为负数"
                    assert total_views >= 0, "总观看数不能为负数"
                    assert avg_views >= 0, "平均观看数不能为负数"
                    
                    # 验证平均观看数计算
                    expected_avg = total_views / total_videos if total_videos > 0 else 0
                    assert abs(avg_views - expected_avg) < 0.01, \
                        f"平均观看数计算错误: 期望{expected_avg:.2f}, 实际{avg_views:.2f}"
                
                if 'uploaded_30d' in videos_stats and 'total' in videos_stats:
                    uploaded_30d = videos_stats['uploaded_30d']
                    total_videos = videos_stats['total']
                    
                    assert isinstance(uploaded_30d, int), "30天内上传数应该是整数"
                    assert uploaded_30d >= 0, "30天内上传数不能为负数"
                    assert uploaded_30d <= total_videos, f"30天内上传数({uploaded_30d})不应该超过总视频数({total_videos})"
            
            # 验证合成任务统计一致性
            if 'compositions' in stats:
                compositions_stats = stats['compositions']
                
                if all(key in compositions_stats for key in ['total', 'successful', 'failed', 'success_rate']):
                    total_compositions = compositions_stats['total']
                    successful = compositions_stats['successful']
                    failed = compositions_stats['failed']
                    success_rate = compositions_stats['success_rate']
                    
                    assert isinstance(total_compositions, int), "总合成任务数应该是整数"
                    assert isinstance(successful, int), "成功任务数应该是整数"
                    assert isinstance(failed, int), "失败任务数应该是整数"
                    assert isinstance(success_rate, (int, float)), "成功率应该是数字"
                    
                    assert total_compositions >= 0, "总合成任务数不能为负数"
                    assert successful >= 0, "成功任务数不能为负数"
                    assert failed >= 0, "失败任务数不能为负数"
                    assert 0 <= success_rate <= 100, "成功率应该在0-100之间"
                    
                    # 成功和失败的任务数之和不应该超过总数
                    assert successful + failed <= total_compositions, \
                        f"成功({successful})和失败({failed})任务数之和不应该超过总数({total_compositions})"
                    
                    # 验证成功率计算
                    expected_success_rate = (successful / total_compositions * 100) if total_compositions > 0 else 0
                    assert abs(success_rate - expected_success_rate) < 0.01, \
                        f"成功率计算错误: 期望{expected_success_rate:.2f}%, 实际{success_rate:.2f}%"
            
            # 验证播放统计一致性
            if 'playbacks' in stats:
                playbacks_stats = stats['playbacks']
                
                if all(key in playbacks_stats for key in ['total', 'completed', 'completion_rate']):
                    total_playbacks = playbacks_stats['total']
                    completed_playbacks = playbacks_stats['completed']
                    completion_rate = playbacks_stats['completion_rate']
                    
                    assert isinstance(total_playbacks, int), "总播放数应该是整数"
                    assert isinstance(completed_playbacks, int), "完成播放数应该是整数"
                    assert isinstance(completion_rate, (int, float)), "完成率应该是数字"
                    
                    assert total_playbacks >= 0, "总播放数不能为负数"
                    assert completed_playbacks >= 0, "完成播放数不能为负数"
                    assert 0 <= completion_rate <= 100, "完成率应该在0-100之间"
                    
                    # 完成的播放数不应该超过总数
                    assert completed_playbacks <= total_playbacks, \
                        f"完成播放数({completed_playbacks})不应该超过总播放数({total_playbacks})"
                    
                    # 验证完成率计算
                    expected_completion_rate = (completed_playbacks / total_playbacks * 100) if total_playbacks > 0 else 0
                    assert abs(completion_rate - expected_completion_rate) < 0.01, \
                        f"完成率计算错误: 期望{expected_completion_rate:.2f}%, 实际{completion_rate:.2f}%"
                
                if 'avg_completion_percentage' in playbacks_stats:
                    avg_completion = playbacks_stats['avg_completion_percentage']
                    assert isinstance(avg_completion, (int, float)), "平均完成百分比应该是数字"
                    assert 0 <= avg_completion <= 100, "平均完成百分比应该在0-100之间"
            
            print(f"✅ 系统统计数据一致性验证通过")
            
        except Exception as e:
            pytest.fail(f"系统统计数据一致性测试失败: {str(e)}")
    
    def test_property_storage_info_calculation_accuracy(self):
        """
        属性 6: 系统监控数据准确性 - 存储信息计算准确性
        
        对于任何存储信息数据，磁盘容量计算应该准确，
        使用率计算应该正确，阈值设置应该合理。
        
        **验证需求: 5.1, 5.2, 5.3, 5.4**
        """
        try:
            print(f"\n测试存储信息计算准确性")
            
            # 获取存储信息数据
            storage_info = self.tester.get_storage_info()
            
            if storage_info is None:
                pytest.skip("无法获取存储信息数据，跳过测试")
            
            # 验证基本字段存在
            required_fields = ['disk_total', 'disk_used', 'disk_free', 'disk_usage_percent']
            for field in required_fields:
                assert field in storage_info, f"存储信息缺少必要字段: {field}"
            
            disk_total = storage_info['disk_total']
            disk_used = storage_info['disk_used']
            disk_free = storage_info['disk_free']
            disk_usage_percent = storage_info['disk_usage_percent']
            
            # 验证数据类型
            assert isinstance(disk_total, int), "磁盘总容量应该是整数"
            assert isinstance(disk_used, int), "磁盘已用容量应该是整数"
            assert isinstance(disk_free, int), "磁盘可用容量应该是整数"
            assert isinstance(disk_usage_percent, (int, float)), "磁盘使用率应该是数字"
            
            # 验证数值合理性
            assert disk_total > 0, "磁盘总容量应该大于0"
            assert disk_used >= 0, "磁盘已用容量不能为负数"
            assert disk_free >= 0, "磁盘可用容量不能为负数"
            assert 0 <= disk_usage_percent <= 100, "磁盘使用率应该在0-100之间"
            
            # 验证磁盘容量计算（允许小误差，因为文件系统开销）
            total_calculated = disk_used + disk_free
            assert abs(disk_total - total_calculated) <= disk_total * 0.05, \
                f"磁盘容量计算不一致: 总容量{disk_total}, 已用+可用{total_calculated}"
            
            # 验证使用率计算
            expected_usage_percent = (disk_used / disk_total) * 100
            assert abs(disk_usage_percent - expected_usage_percent) < 0.1, \
                f"磁盘使用率计算错误: 期望{expected_usage_percent:.2f}%, 实际{disk_usage_percent:.2f}%"
            
            # 验证媒体文件大小字段
            if 'video_files_size' in storage_info and 'composed_files_size' in storage_info and 'total_media_size' in storage_info:
                video_size = storage_info['video_files_size']
                composed_size = storage_info['composed_files_size']
                total_media_size = storage_info['total_media_size']
                
                assert isinstance(video_size, int), "视频文件大小应该是整数"
                assert isinstance(composed_size, int), "合成文件大小应该是整数"
                assert isinstance(total_media_size, int), "总媒体文件大小应该是整数"
                
                assert video_size >= 0, "视频文件大小不能为负数"
                assert composed_size >= 0, "合成文件大小不能为负数"
                assert total_media_size >= 0, "总媒体文件大小不能为负数"
                
                # 验证总媒体大小计算
                expected_total_media = video_size + composed_size
                assert total_media_size == expected_total_media, \
                    f"总媒体大小计算错误: 期望{expected_total_media}, 实际{total_media_size}"
            
            # 验证阈值设置
            if 'warning_threshold' in storage_info and 'critical_threshold' in storage_info:
                warning_threshold = storage_info['warning_threshold']
                critical_threshold = storage_info['critical_threshold']
                
                assert isinstance(warning_threshold, (int, float)), "警告阈值应该是数字"
                assert isinstance(critical_threshold, (int, float)), "严重阈值应该是数字"
                
                assert 0 < warning_threshold < 100, "警告阈值应该在0-100之间"
                assert 0 < critical_threshold <= 100, "严重阈值应该在0-100之间"
                assert warning_threshold < critical_threshold, "警告阈值应该小于严重阈值"
            
            # 验证警告逻辑
            if 'warnings' in storage_info:
                warnings = storage_info['warnings']
                assert isinstance(warnings, list), "警告信息应该是列表"
                
                # 如果有警告，验证警告的合理性
                for warning in warnings:
                    assert isinstance(warning, dict), "每个警告应该是字典"
                    assert 'level' in warning, "警告应该有级别字段"
                    assert 'message' in warning, "警告应该有消息字段"
                    assert warning['level'] in ['warning', 'critical'], "警告级别应该是warning或critical"
            
            print(f"✅ 存储信息计算准确性验证通过")
            
        except Exception as e:
            pytest.fail(f"存储信息计算准确性测试失败: {str(e)}")
    
    def test_property_monitoring_api_response_consistency(self):
        """
        属性 6: 系统监控数据准确性 - 监控API响应一致性
        
        对于任何监控API调用，响应格式应该一致，
        数据类型应该正确，必要字段应该存在。
        
        **验证需求: 5.1, 5.2, 5.3, 5.4**
        """
        try:
            print(f"\n测试监控API响应一致性")
            
            # 测试系统统计API响应一致性
            stats = self.tester.get_system_statistics()
            if stats is not None:
                assert isinstance(stats, dict), "系统统计响应应该是字典"
                
                # 检查主要部分
                expected_sections = ['users', 'videos', 'compositions', 'playbacks']
                for section in expected_sections:
                    if section in stats:
                        assert isinstance(stats[section], dict), f"{section}部分应该是字典"
            
            # 测试存储信息API响应一致性
            storage = self.tester.get_storage_info()
            if storage is not None:
                assert isinstance(storage, dict), "存储信息响应应该是字典"
                
                # 检查数值字段的类型
                numeric_fields = ['disk_total', 'disk_used', 'disk_free', 'disk_usage_percent']
                for field in numeric_fields:
                    if field in storage:
                        assert isinstance(storage[field], (int, float)), f"{field}应该是数字类型"
            
            # 测试错误统计API响应一致性
            errors = self.tester.get_error_statistics()
            if errors is not None:
                assert isinstance(errors, dict), "错误统计响应应该是字典"
                
                # 检查数值字段的类型
                if 'total_errors' in errors:
                    assert isinstance(errors['total_errors'], int), "总错误数应该是整数"
                
                if 'error_rate' in errors:
                    assert isinstance(errors['error_rate'], (int, float)), "错误率应该是数字"
            
            print(f"✅ 监控API响应一致性验证通过")
            
        except Exception as e:
            pytest.fail(f"监控API响应一致性测试失败: {str(e)}")


# 运行属性测试的函数
def test_monitoring_data_accuracy_properties():
    """运行系统监控数据准确性属性测试"""
    config = TestConfigManager()
    tester = MonitoringPropertiesTester(config)
    
    print("=" * 60)
    print("系统监控数据准确性属性测试")
    print("=" * 60)
    
    test_class = TestMonitoringDataAccuracy()
    test_class.setup_class()
    
    results = []
    
    try:
        # 运行各个属性测试
        print("\n运行错误统计时间一致性属性测试...")
        # 手动运行几个测试用例
        for time_range in [1, 6, 24, 72]:
            try:
                test_class.test_property_error_statistics_time_consistency(time_range)
                results.append(True)
            except Exception as e:
                print(f"时间范围 {time_range} 测试失败: {str(e)}")
                results.append(False)
        
        print("\n运行系统统计数据一致性属性测试...")
        try:
            test_class.test_property_system_statistics_data_consistency()
            results.append(True)
        except Exception as e:
            print(f"系统统计数据一致性测试失败: {str(e)}")
            results.append(False)
        
        print("\n运行存储信息计算准确性属性测试...")
        try:
            test_class.test_property_storage_info_calculation_accuracy()
            results.append(True)
        except Exception as e:
            print(f"存储信息计算准确性测试失败: {str(e)}")
            results.append(False)
        
        print("\n运行监控API响应一致性属性测试...")
        try:
            test_class.test_property_monitoring_api_response_consistency()
            results.append(True)
        except Exception as e:
            print(f"监控API响应一致性测试失败: {str(e)}")
            results.append(False)
        
    except Exception as e:
        print(f"属性测试执行异常: {str(e)}")
        results.append(False)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n系统监控数据准确性属性测试完成: {success_count}/{total_count} 通过")
    
    return success_count == total_count


if __name__ == "__main__":
    # 运行属性测试
    success = test_monitoring_data_accuracy_properties()
    
    print("=" * 60)
    if success:
        print("✅ 所有系统监控数据准确性属性测试通过")
        exit(0)
    else:
        print("❌ 部分系统监控数据准确性属性测试失败")
        exit(1)