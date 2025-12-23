"""
验证错误处理功能的简单脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api_integration_tests'))

from api_integration_tests.tests.test_error_handling import ErrorHandlingTester
from api_integration_tests.tests.test_network_errors import NetworkErrorTester
from api_integration_tests.tests.test_auth_error_handling import AuthErrorHandlingTester
from api_integration_tests.config.test_config import TestConfigManager

def main():
    print("开始验证错误处理功能...")
    config = TestConfigManager()
    
    # 测试HTTP错误处理
    print("\n1. 测试HTTP错误处理...")
    http_tester = ErrorHandlingTester(config)
    try:
        result = http_tester.test_4xx_errors()
        print(f"   4xx错误测试: {result['status']} ({result['passed']}/{result['total']})")
        
        result = http_tester.test_5xx_errors()
        print(f"   5xx错误测试: {result['status']} ({result['passed']}/{result['total']})")
        
        result = http_tester.test_error_message_user_friendliness()
        print(f"   用户友好性测试: {result['status']} ({result['passed']}/{result['total']})")
        
    finally:
        http_tester.cleanup()
    
    # 测试网络错误处理
    print("\n2. 测试网络错误处理...")
    network_tester = NetworkErrorTester(config)
    try:
        result = network_tester.test_connection_errors()
        print(f"   连接错误测试: {result['status']} ({result['passed']}/{result['total']})")
        
        result = network_tester.test_retry_mechanism()
        print(f"   重试机制测试: {result['status']} ({result['passed']}/{result['total']})")
        
    finally:
        network_tester.cleanup()
    
    # 测试认证错误处理
    print("\n3. 测试认证错误处理...")
    auth_tester = AuthErrorHandlingTester(config)
    try:
        result = auth_tester.test_authentication_failure_handling()
        print(f"   认证失败测试: {result['status']} ({result['passed']}/{result['total']})")
        
        result = auth_tester.test_authentication_state_cleanup()
        print(f"   状态清理测试: {result['status']} ({result['passed']}/{result['total']})")
        
        result = auth_tester.test_error_logging()
        print(f"   错误日志测试: {result['status']} ({result['passed']}/{result['total']})")
        
    finally:
        auth_tester.cleanup()
    
    print("\n✅ 错误处理功能验证完成")

if __name__ == "__main__":
    main()