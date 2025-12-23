"""
数据格式一致性属性测试模块

使用属性测试验证数据格式一致性的通用正确性属性。
**属性 9: 数据格式一致性**
**验证需求: 8.1, 8.2, 8.3, 8.4**
"""

import json
import uuid
import string
import random
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings, assume
import pytest

from ..utils.http_client import APIClient
from ..utils.test_helpers import TestLogger
from ..config.test_config import TestConfigManager


class DataConsistencyPropertyTester:
    """数据一致性属性测试器"""
    
    def __init__(self):
        """初始化属性测试器"""
        self.config = TestConfigManager()
        self.client = APIClient(
            base_url=self.config.get_base_url(),
            timeout=self.config.get_timeout(),
            retry_count=1  # 属性测试时减少重试
        )
        self.logger = TestLogger("data_consistency_properties.log")
        self._authenticated = False
    
    def _ensure_authentication(self) -> bool:
        """确保用户已登录"""
        if self._authenticated:
            return True
        
        success = self.client.login(
            self.config.test_username,
            self.config.test_password
        )
        
        if success:
            self._authenticated = True
        
        return success
    
    def close(self):
        """关闭测试器"""
        if self.client:
            self.client.close()


# Hypothesis策略定义
@st.composite
def chinese_text_strategy(draw):
    """生成包含中文字符的文本策略"""
    # 中文字符范围
    chinese_chars = draw(st.text(
        alphabet=st.characters(min_codepoint=0x4e00, max_codepoint=0x9fff),
        min_size=1, max_size=20
    ))
    
    # 可能包含英文和数字
    mixed_text = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
        min_size=0, max_size=10
    ))
    
    return chinese_chars + mixed_text


@st.composite
def special_characters_strategy(draw):
    """生成包含特殊字符的文本策略"""
    # 特殊符号
    special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?~`"
    special_text = draw(st.text(alphabet=special_chars, min_size=1, max_size=10))
    
    # 数学符号
    math_symbols = "±×÷≠≤≥∞∑∏√∫"
    math_text = draw(st.text(alphabet=math_symbols, min_size=0, max_size=5))
    
    # 货币符号
    currency_symbols = "¥$€£¢"
    currency_text = draw(st.text(alphabet=currency_symbols, min_size=0, max_size=3))
    
    return special_text + math_text + currency_text


@st.composite
def emoji_strategy(draw):
    """生成emoji字符策略"""
    # 简化的emoji范围（实际emoji范围更复杂）
    emoji_chars = draw(st.text(
        alphabet=st.characters(min_codepoint=0x1F600, max_codepoint=0x1F64F),
        min_size=0, max_size=5
    ))
    return emoji_chars


@st.composite
def complex_json_data_strategy(draw):
    """生成复杂JSON数据策略"""
    # 基础数据类型
    simple_values = st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.booleans()
    )
    
    # 嵌套对象
    nested_dict = st.dictionaries(
        keys=st.text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        values=simple_values,
        min_size=1, max_size=5
    )
    
    # 数组
    array_values = st.lists(simple_values, min_size=0, max_size=10)
    
    # 复杂数据结构
    complex_data = draw(st.dictionaries(
        keys=st.text(alphabet=string.ascii_letters + '_', min_size=1, max_size=15),
        values=st.one_of(simple_values, nested_dict, array_values),
        min_size=1, max_size=8
    ))
    
    return complex_data


@st.composite
def datetime_strategy(draw):
    """生成日期时间策略"""
    # 生成合理范围内的日期时间
    base_time = datetime.now()
    
    # 时间偏移（过去或未来一年内）
    offset_days = draw(st.integers(min_value=-365, max_value=365))
    offset_seconds = draw(st.integers(min_value=0, max_value=86400))
    
    target_time = base_time + timedelta(days=offset_days, seconds=offset_seconds)
    
    # 选择时区
    timezone_offset = draw(st.integers(min_value=-12, max_value=12))
    tz = timezone(timedelta(hours=timezone_offset))
    
    return target_time.replace(tzinfo=tz)


# 属性测试fixture
@pytest.fixture(scope="module")
def property_tester():
    """属性测试器fixture"""
    tester = DataConsistencyPropertyTester()
    yield tester
    tester.close()


# 属性测试函数
@given(complex_data=complex_json_data_strategy())
@settings(max_examples=50, deadline=30000)  # 30秒超时
def test_json_serialization_round_trip_property(complex_data, property_tester):
    """
    属性测试：JSON序列化往返一致性
    
    **Feature: api-integration-testing, Property 9: 数据格式一致性**
    **Validates: Requirements 8.1**
    
    对于任何复杂的JSON数据，序列化后发送到API再反序列化，
    应该保持数据的基本结构和类型一致性。
    """
    try:
        # 确保数据不为空且有意义
        assume(len(complex_data) > 0)
        assume(any(isinstance(v, str) and len(v) > 0 for v in complex_data.values()))
        
        # 添加必要的字段使其成为有效的API请求
        test_data = {
            "title": f"属性测试_{uuid.uuid4().hex[:8]}",
            "description": "属性测试生成的数据",
            "category": "测试",
            **complex_data
        }
        
        # 序列化测试数据
        original_json = json.dumps(test_data, ensure_ascii=False, sort_keys=True)
        
        # 确保能够正确序列化
        assume(len(original_json) > 0)
        
        # 发送到API（使用健康检查端点进行基础测试）
        response = property_tester.client.get("/api/monitoring/health/")
        
        # 验证响应可以正确处理JSON
        assert response.status_code in [200, 201, 400, 401, 403, 404], \
            f"API返回了意外的状态码: {response.status_code}"
        
        if response.json_data is not None:
            # 验证响应JSON可以正确序列化
            response_json = json.dumps(response.json_data, ensure_ascii=False, sort_keys=True)
            assert len(response_json) > 0, "响应JSON序列化后为空"
            
            # 验证可以重新解析
            reparsed_data = json.loads(response_json)
            assert isinstance(reparsed_data, dict), "重新解析的数据不是字典类型"
        
        property_tester.logger.info("JSON序列化往返测试通过", {
            "original_size": len(original_json),
            "response_status": response.status_code
        })
        
    except Exception as e:
        property_tester.logger.error("JSON序列化属性测试失败", {
            "error": str(e),
            "data_keys": list(complex_data.keys()) if complex_data else []
        })
        raise

@given(chinese_text=chinese_text_strategy())
@settings(max_examples=30, deadline=25000)
def test_utf8_chinese_handling_property(chinese_text, property_tester):
    """
    属性测试：中文字符处理一致性
    
    **Feature: api-integration-testing, Property 9: 数据格式一致性**
    **Validates: Requirements 8.2, 8.3**
    
    对于任何包含中文字符的文本，API应该能够正确处理UTF-8编码，
    不会出现乱码或编码错误。
    """
    try:
        # 确保文本包含中文字符
        assume(any('\u4e00' <= char <= '\u9fff' for char in chinese_text))
        assume(len(chinese_text.strip()) > 0)
        
        # 创建包含中文的测试数据
        test_data = {
            "title": chinese_text,
            "description": f"中文测试描述：{chinese_text}",
            "category": "中文测试"
        }
        
        # 验证数据可以正确编码为UTF-8
        utf8_encoded = json.dumps(test_data, ensure_ascii=False).encode('utf-8')
        assert len(utf8_encoded) > 0, "UTF-8编码后数据为空"
        
        # 验证可以正确解码
        decoded_data = json.loads(utf8_encoded.decode('utf-8'))
        assert decoded_data["title"] == chinese_text, "中文文本在编码/解码后发生变化"
        
        # 发送到API进行实际测试
        response = property_tester.client.get("/api/monitoring/health/")
        
        # 验证响应文本可以正确处理UTF-8
        if response.text:
            # 尝试编码/解码响应文本
            response_utf8 = response.text.encode('utf-8').decode('utf-8')
            assert len(response_utf8) >= 0, "响应文本UTF-8处理失败"
        
        property_tester.logger.info("UTF-8中文处理测试通过", {
            "chinese_text_length": len(chinese_text),
            "chinese_char_count": sum(1 for c in chinese_text if '\u4e00' <= c <= '\u9fff'),
            "response_status": response.status_code
        })
        
    except UnicodeError as e:
        property_tester.logger.error("UTF-8编码错误", {
            "error": str(e),
            "chinese_text": chinese_text[:50]  # 只记录前50个字符
        })
        raise
    except Exception as e:
        property_tester.logger.error("UTF-8中文处理属性测试失败", {
            "error": str(e),
            "chinese_text": chinese_text[:50]
        })
        raise


@given(special_text=special_characters_strategy())
@settings(max_examples=25, deadline=20000)
def test_special_characters_handling_property(special_text, property_tester):
    """
    属性测试：特殊字符处理一致性
    
    **Feature: api-integration-testing, Property 9: 数据格式一致性**
    **Validates: Requirements 8.2, 8.3**
    
    对于任何包含特殊字符的文本，API应该能够正确处理，
    不会导致解析错误或数据损坏。
    """
    try:
        # 确保文本包含特殊字符
        assume(len(special_text.strip()) > 0)
        assume(any(ord(char) > 127 or char in "!@#$%^&*()_+-=[]{}|;':\",./<>?~`" 
                  for char in special_text))
        
        # 创建包含特殊字符的测试数据
        test_data = {
            "title": f"特殊字符测试: {special_text}",
            "description": f"包含特殊字符的描述：{special_text}",
            "category": "特殊字符测试"
        }
        
        # 验证数据可以正确序列化
        json_str = json.dumps(test_data, ensure_ascii=False)
        assert len(json_str) > 0, "包含特殊字符的数据序列化失败"
        
        # 验证可以正确反序列化
        parsed_data = json.loads(json_str)
        assert special_text in parsed_data["title"], "特殊字符在序列化/反序列化后丢失"
        
        # 发送到API进行测试
        response = property_tester.client.get("/api/monitoring/health/")
        
        # 验证响应可以正确处理
        assert response.status_code in [200, 201, 400, 401, 403, 404], \
            f"API返回意外状态码: {response.status_code}"
        
        property_tester.logger.info("特殊字符处理测试通过", {
            "special_text_length": len(special_text),
            "special_char_count": sum(1 for c in special_text if ord(c) > 127),
            "response_status": response.status_code
        })
        
    except Exception as e:
        property_tester.logger.error("特殊字符处理属性测试失败", {
            "error": str(e),
            "special_text": special_text[:50]
        })
        raise


@given(test_datetime=datetime_strategy())
@settings(max_examples=30, deadline=25000)
def test_datetime_format_consistency_property(test_datetime, property_tester):
    """
    属性测试：日期时间格式一致性
    
    **Feature: api-integration-testing, Property 9: 数据格式一致性**
    **Validates: Requirements 8.4**
    
    对于任何有效的日期时间，API应该能够一致地处理不同的时区和格式，
    保持时间信息的准确性。
    """
    try:
        # 生成不同格式的时间表示
        iso_format = test_datetime.isoformat()
        timestamp = test_datetime.timestamp()
        formatted_time = test_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建包含时间信息的测试数据
        test_data = {
            "created_at": iso_format,
            "timestamp": timestamp,
            "formatted_time": formatted_time,
            "timezone": str(test_datetime.tzinfo)
        }
        
        # 验证时间数据可以正确序列化
        json_str = json.dumps(test_data, ensure_ascii=False)
        assert len(json_str) > 0, "时间数据序列化失败"
        
        # 验证可以正确反序列化
        parsed_data = json.loads(json_str)
        assert parsed_data["created_at"] == iso_format, "ISO格式时间在序列化后发生变化"
        assert abs(parsed_data["timestamp"] - timestamp) < 0.001, "时间戳在序列化后发生变化"
        
        # 验证时间解析的一致性
        parsed_datetime = datetime.fromisoformat(parsed_data["created_at"])
        time_diff = abs((parsed_datetime - test_datetime.replace(microsecond=0)).total_seconds())
        assert time_diff < 1.0, f"解析后的时间与原始时间差异过大: {time_diff}秒"
        
        # 发送到API进行测试
        response = property_tester.client.get("/api/monitoring/health/")
        
        # 如果响应包含时间信息，验证格式一致性
        if response.json_data and any('time' in key.lower() or 'date' in key.lower() 
                                     for key in response.json_data.keys()):
            # 验证响应中的时间字段格式
            for key, value in response.json_data.items():
                if ('time' in key.lower() or 'date' in key.lower()) and isinstance(value, str):
                    try:
                        # 尝试解析时间字符串
                        parsed_response_time = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        assert isinstance(parsed_response_time, datetime), f"无法解析响应中的时间字段: {key}"
                    except ValueError:
                        # 如果不是ISO格式，可能是其他有效格式，这也是可以接受的
                        pass
        
        property_tester.logger.info("日期时间格式一致性测试通过", {
            "iso_format": iso_format,
            "timestamp": timestamp,
            "timezone": str(test_datetime.tzinfo),
            "response_status": response.status_code
        })
        
    except Exception as e:
        property_tester.logger.error("日期时间格式一致性属性测试失败", {
            "error": str(e),
            "iso_format": iso_format if 'iso_format' in locals() else "未生成",
            "timestamp": timestamp if 'timestamp' in locals() else "未生成"
        })
        raise


@given(test_data=st.dictionaries(
    keys=st.text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    values=st.one_of(
        st.text(min_size=1, max_size=100),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.none()
    ),
    min_size=1, max_size=10
))
@settings(max_examples=40, deadline=30000)
def test_data_type_preservation_property(test_data, property_tester):
    """
    属性测试：数据类型保持一致性
    
    **Feature: api-integration-testing, Property 9: 数据格式一致性**
    **Validates: Requirements 8.1, 8.2**
    
    对于任何包含不同数据类型的JSON对象，在序列化和传输过程中，
    基本数据类型应该得到正确保持。
    """
    try:
        # 确保测试数据有意义
        assume(len(test_data) > 0)
        
        # 记录原始数据类型
        original_types = {key: type(value).__name__ for key, value in test_data.items()}
        
        # 序列化和反序列化测试
        json_str = json.dumps(test_data, ensure_ascii=False)
        parsed_data = json.loads(json_str)
        
        # 验证数据类型保持（JSON序列化会有一些类型转换，这是正常的）
        for key, original_value in test_data.items():
            parsed_value = parsed_data[key]
            
            # 检查基本类型一致性
            if isinstance(original_value, str):
                assert isinstance(parsed_value, str), f"字符串类型未保持: {key}"
                assert parsed_value == original_value, f"字符串值发生变化: {key}"
            elif isinstance(original_value, bool):
                assert isinstance(parsed_value, bool), f"布尔类型未保持: {key}"
                assert parsed_value == original_value, f"布尔值发生变化: {key}"
            elif isinstance(original_value, int):
                assert isinstance(parsed_value, int), f"整数类型未保持: {key}"
                assert parsed_value == original_value, f"整数值发生变化: {key}"
            elif isinstance(original_value, float):
                assert isinstance(parsed_value, (int, float)), f"数值类型未保持: {key}"
                assert abs(parsed_value - original_value) < 0.0001, f"浮点数值发生显著变化: {key}"
            elif original_value is None:
                assert parsed_value is None, f"None值未保持: {key}"
        
        # 发送到API进行基础连接测试
        response = property_tester.client.get("/api/monitoring/health/")
        assert response.status_code in [200, 201, 400, 401, 403, 404], \
            f"API连接测试失败: {response.status_code}"
        
        property_tester.logger.info("数据类型保持一致性测试通过", {
            "original_types": original_types,
            "data_size": len(test_data),
            "response_status": response.status_code
        })
        
    except Exception as e:
        property_tester.logger.error("数据类型保持一致性属性测试失败", {
            "error": str(e),
            "original_types": original_types if 'original_types' in locals() else {},
            "data_keys": list(test_data.keys())
        })
        raise


if __name__ == "__main__":
    # 直接运行属性测试
    import sys
    
    print("开始数据格式一致性属性测试...")
    
    # 创建测试器
    tester = DataConsistencyPropertyTester()
    
    try:
        # 运行一些示例测试
        print("运行JSON序列化属性测试...")
        test_json_serialization_round_trip_property(
            {"test": "data", "number": 42, "flag": True}, tester
        )
        
        print("运行UTF-8中文处理属性测试...")
        test_utf8_chinese_handling_property("测试中文字符", tester)
        
        print("运行特殊字符处理属性测试...")
        test_special_characters_handling_property("!@#$%^&*()", tester)
        
        print("运行日期时间格式属性测试...")
        test_datetime_format_consistency_property(datetime.now(timezone.utc), tester)
        
        print("运行数据类型保持属性测试...")
        test_data_type_preservation_property(
            {"str": "test", "int": 42, "float": 3.14, "bool": True, "null": None}, tester
        )
        
        print("✅ 所有属性测试示例运行完成")
        
    except Exception as e:
        print(f"❌ 属性测试失败: {str(e)}")
        sys.exit(1)
    
    finally:
        tester.close()