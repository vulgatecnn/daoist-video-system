"""
测试结果管理模块

提供测试结果的收集、存储、分析和报告生成功能。
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

from .test_helpers import TestLogger


class TestStatus(Enum):
    """测试状态枚举"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    status: TestStatus
    duration: float
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result['status'] = self.status.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestResult':
        """从字典创建测试结果"""
        data = data.copy()
        data['status'] = TestStatus(data['status'])
        return cls(**data)


@dataclass
class TestSuite:
    """测试套件数据类"""
    name: str
    tests: List[TestResult]
    start_time: str
    end_time: str = None
    
    def __post_init__(self):
        if self.end_time is None:
            self.end_time = datetime.now().isoformat()
    
    @property
    def total_tests(self) -> int:
        """总测试数"""
        return len(self.tests)
    
    @property
    def passed_tests(self) -> int:
        """通过的测试数"""
        return len([t for t in self.tests if t.status == TestStatus.PASS])
    
    @property
    def failed_tests(self) -> int:
        """失败的测试数"""
        return len([t for t in self.tests if t.status == TestStatus.FAIL])
    
    @property
    def skipped_tests(self) -> int:
        """跳过的测试数"""
        return len([t for t in self.tests if t.status == TestStatus.SKIP])
    
    @property
    def error_tests(self) -> int:
        """错误的测试数"""
        return len([t for t in self.tests if t.status == TestStatus.ERROR])
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def total_duration(self) -> float:
        """总耗时"""
        return sum(test.duration for test in self.tests)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "skipped": self.skipped_tests,
            "errors": self.error_tests,
            "success_rate": round(self.success_rate, 2),
            "total_duration": round(self.total_duration, 3)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "summary": self.get_summary(),
            "tests": [test.to_dict() for test in self.tests]
        }


class TestResultManager:
    """测试结果管理器"""
    
    def __init__(self, output_dir: str = "test_results"):
        """
        初始化测试结果管理器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.test_suites: List[TestSuite] = []
        self.current_suite: Optional[TestSuite] = None
        
        self.logger = TestLogger("test_result_manager.log")
    
    def start_suite(self, suite_name: str) -> TestSuite:
        """
        开始新的测试套件
        
        Args:
            suite_name: 套件名称
            
        Returns:
            TestSuite: 测试套件对象
        """
        self.current_suite = TestSuite(
            name=suite_name,
            tests=[],
            start_time=datetime.now().isoformat()
        )
        
        self.logger.info(f"开始测试套件: {suite_name}")
        return self.current_suite
    
    def end_suite(self) -> Optional[TestSuite]:
        """
        结束当前测试套件
        
        Returns:
            TestSuite: 完成的测试套件
        """
        if self.current_suite:
            self.current_suite.end_time = datetime.now().isoformat()
            self.test_suites.append(self.current_suite)
            
            self.logger.info(f"结束测试套件: {self.current_suite.name}", {
                "summary": self.current_suite.get_summary()
            })
            
            completed_suite = self.current_suite
            self.current_suite = None
            return completed_suite
        
        return None
    
    def add_test_result(self, test_name: str, status: TestStatus, 
                       duration: float, message: str = "", 
                       details: Dict[str, Any] = None) -> TestResult:
        """
        添加测试结果
        
        Args:
            test_name: 测试名称
            status: 测试状态
            duration: 测试耗时
            message: 测试消息
            details: 测试详情
            
        Returns:
            TestResult: 测试结果对象
        """
        test_result = TestResult(
            test_name=test_name,
            status=status,
            duration=duration,
            message=message,
            details=details or {}
        )
        
        if self.current_suite:
            self.current_suite.tests.append(test_result)
        
        self.logger.info(f"添加测试结果: {test_name}", {
            "status": status.value,
            "duration": duration,
            "message": message
        })
        
        return test_result
    
    def add_passed_test(self, test_name: str, duration: float, 
                       message: str = "", details: Dict[str, Any] = None) -> TestResult:
        """添加通过的测试"""
        return self.add_test_result(test_name, TestStatus.PASS, duration, message, details)
    
    def add_failed_test(self, test_name: str, duration: float, 
                       message: str = "", details: Dict[str, Any] = None) -> TestResult:
        """添加失败的测试"""
        return self.add_test_result(test_name, TestStatus.FAIL, duration, message, details)
    
    def add_skipped_test(self, test_name: str, message: str = "", 
                        details: Dict[str, Any] = None) -> TestResult:
        """添加跳过的测试"""
        return self.add_test_result(test_name, TestStatus.SKIP, 0.0, message, details)
    
    def add_error_test(self, test_name: str, duration: float, 
                      message: str = "", details: Dict[str, Any] = None) -> TestResult:
        """添加错误的测试"""
        return self.add_test_result(test_name, TestStatus.ERROR, duration, message, details)
    
    def get_overall_summary(self) -> Dict[str, Any]:
        """获取总体摘要"""
        total_tests = sum(suite.total_tests for suite in self.test_suites)
        total_passed = sum(suite.passed_tests for suite in self.test_suites)
        total_failed = sum(suite.failed_tests for suite in self.test_suites)
        total_skipped = sum(suite.skipped_tests for suite in self.test_suites)
        total_errors = sum(suite.error_tests for suite in self.test_suites)
        total_duration = sum(suite.total_duration for suite in self.test_suites)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        
        return {
            "total_suites": len(self.test_suites),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "errors": total_errors,
            "success_rate": round(success_rate, 2),
            "total_duration": round(total_duration, 3),
            "timestamp": datetime.now().isoformat()
        }
    
    def save_json_report(self, filename: str = None) -> Path:
        """
        保存JSON格式报告
        
        Args:
            filename: 文件名
            
        Returns:
            Path: 报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        report_path = self.output_dir / filename
        
        report_data = {
            "summary": self.get_overall_summary(),
            "suites": [suite.to_dict() for suite in self.test_suites]
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON报告已保存: {report_path}")
        return report_path
    
    def save_html_report(self, filename: str = None) -> Path:
        """
        保存HTML格式报告
        
        Args:
            filename: 文件名
            
        Returns:
            Path: 报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.html"
        
        report_path = self.output_dir / filename
        
        # 生成HTML报告
        html_content = self._generate_html_report()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML报告已保存: {report_path}")
        return report_path
    
    def _generate_html_report(self) -> str:
        """生成HTML报告内容"""
        summary = self.get_overall_summary()
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API集成测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric.passed {{ background-color: #d4edda; }}
        .metric.failed {{ background-color: #f8d7da; }}
        .metric.skipped {{ background-color: #fff3cd; }}
        .metric.error {{ background-color: #f5c6cb; }}
        .suite {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .suite-header {{ background-color: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; }}
        .test-list {{ padding: 0; margin: 0; list-style: none; }}
        .test-item {{ padding: 10px 15px; border-bottom: 1px solid #eee; }}
        .test-item:last-child {{ border-bottom: none; }}
        .test-item.passed {{ background-color: #d4edda; }}
        .test-item.failed {{ background-color: #f8d7da; }}
        .test-item.skipped {{ background-color: #fff3cd; }}
        .test-item.error {{ background-color: #f5c6cb; }}
        .test-details {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>API集成测试报告</h1>
        <p>生成时间: {summary['timestamp']}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>总测试数</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['total_tests']}</div>
        </div>
        <div class="metric passed">
            <h3>通过</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['passed']}</div>
        </div>
        <div class="metric failed">
            <h3>失败</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['failed']}</div>
        </div>
        <div class="metric skipped">
            <h3>跳过</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['skipped']}</div>
        </div>
        <div class="metric error">
            <h3>错误</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['errors']}</div>
        </div>
        <div class="metric">
            <h3>成功率</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['success_rate']}%</div>
        </div>
        <div class="metric">
            <h3>总耗时</h3>
            <div style="font-size: 2em; font-weight: bold;">{summary['total_duration']}s</div>
        </div>
    </div>
"""
        
        # 添加测试套件详情
        for suite in self.test_suites:
            suite_summary = suite.get_summary()
            html += f"""
    <div class="suite">
        <div class="suite-header">
            <h2>{suite.name}</h2>
            <p>测试数: {suite_summary['total_tests']} | 
               通过: {suite_summary['passed']} | 
               失败: {suite_summary['failed']} | 
               跳过: {suite_summary['skipped']} | 
               错误: {suite_summary['errors']} | 
               成功率: {suite_summary['success_rate']}% | 
               耗时: {suite_summary['total_duration']}s</p>
        </div>
        <ul class="test-list">
"""
            
            for test in suite.tests:
                status_class = test.status.value.lower()
                html += f"""
            <li class="test-item {status_class}">
                <strong>{test.test_name}</strong> - {test.status.value} ({test.duration}s)
                {f'<div class="test-details">{test.message}</div>' if test.message else ''}
            </li>
"""
            
            html += """
        </ul>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html
    
    def print_summary(self):
        """打印测试摘要"""
        summary = self.get_overall_summary()
        
        print("\n" + "="*60)
        print("API集成测试报告摘要")
        print("="*60)
        print(f"总测试套件数: {summary['total_suites']}")
        print(f"总测试数: {summary['total_tests']}")
        print(f"通过: {summary['passed']}")
        print(f"失败: {summary['failed']}")
        print(f"跳过: {summary['skipped']}")
        print(f"错误: {summary['errors']}")
        print(f"成功率: {summary['success_rate']}%")
        print(f"总耗时: {summary['total_duration']}s")
        print("="*60)
        
        # 打印各套件摘要
        for suite in self.test_suites:
            suite_summary = suite.get_summary()
            print(f"\n{suite.name}:")
            print(f"  测试数: {suite_summary['total_tests']} | "
                  f"通过: {suite_summary['passed']} | "
                  f"失败: {suite_summary['failed']} | "
                  f"成功率: {suite_summary['success_rate']}%")
    
    def clear_results(self):
        """清除所有测试结果"""
        self.test_suites.clear()
        self.current_suite = None
        self.logger.info("测试结果已清除")