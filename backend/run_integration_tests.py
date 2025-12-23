#!/usr/bin/env python
"""
道士经文视频管理系统 - 集成测试运行器
统一运行所有集成测试，包括用户流程、API端点验证和负载测试
"""
import os
import sys
import django
import subprocess
import time
from pathlib import Path

# 设置Django环境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daoist_video_system.settings')
django.setup()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self):
        self.test_results = {}
        self.server_process = None
        
    def check_server_status(self):
        """检查服务器状态"""
        logger.info("检查Django服务器状态...")
        
        try:
            import requests
            response = requests.get('http://127.0.0.1:8000/api/monitoring/health/', timeout=5)
            logger.info("✅ Django服务器正在运行")
            return True
        except:
            logger.warning("⚠️  Django服务器未运行")
            return False
    
    def start_test_server(self):
        """启动测试服务器"""
        if self.check_server_status():
            logger.info("使用现有的Django服务器")
            return True
        
        logger.info("启动Django测试服务器...")
        
        try:
            # 启动Django开发服务器
            self.server_process = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待服务器启动
            for i in range(30):  # 最多等待30秒
                time.sleep(1)
                if self.check_server_status():
                    logger.info("✅ Django测试服务器启动成功")
                    return True
            
            logger.error("❌ Django测试服务器启动超时")
            return False
            
        except Exception as e:
            logger.error(f"❌ 启动Django测试服务器失败: {e}")
            return False
    
    def stop_test_server(self):
        """停止测试服务器"""
        if self.server_process:
            logger.info("停止Django测试服务器...")
            self.server_process.terminate()
            self.server_process.wait()
            logger.info("✅ Django测试服务器已停止")
    
    def run_test_script(self, script_name, description):
        """运行测试脚本"""
        logger.info(f"\n🚀 运行{description}...")
        logger.info("=" * 50)
        
        script_path = BASE_DIR / script_name
        
        if not script_path.exists():
            logger.error(f"❌ 测试脚本不存在: {script_path}")
            return False
        
        try:
            # 运行测试脚本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 输出结果
            if result.stdout:
                print(result.stdout)
            
            if result.stderr:
                print(result.stderr)
            
            success = result.returncode == 0
            
            if success:
                logger.info(f"✅ {description}完成")
            else:
                logger.error(f"❌ {description}失败 (退出码: {result.returncode})")
            
            return success
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description}超时")
            return False
        except Exception as e:
            logger.error(f"❌ 运行{description}时发生错误: {e}")
            return False
    
    def run_basic_system_tests(self):
        """运行基础系统测试"""
        logger.info("\n🔧 运行基础系统测试...")
        
        tests = [
            ('test_video_system.py', '基础功能测试'),
            ('test_video_composition.py', '视频合成环境测试'),
        ]
        
        results = {}
        for script, description in tests:
            results[description] = self.run_test_script(script, description)
        
        return results
    
    def run_integration_tests(self):
        """运行集成测试"""
        logger.info("\n🔄 运行集成测试...")
        
        # 确保服务器运行
        if not self.check_server_status():
            logger.error("❌ 服务器未运行，无法进行集成测试")
            return {}
        
        tests = [
            ('test_integration.py', '完整用户流程集成测试'),
            ('test_api_endpoints.py', 'API端点验证测试'),
        ]
        
        results = {}
        for script, description in tests:
            results[description] = self.run_test_script(script, description)
        
        return results
    
    def run_performance_tests(self):
        """运行性能测试"""
        logger.info("\n⚡ 运行性能测试...")
        
        # 确保服务器运行
        if not self.check_server_status():
            logger.error("❌ 服务器未运行，无法进行性能测试")
            return {}
        
        tests = [
            ('test_load_performance.py', '负载和性能测试'),
        ]
        
        results = {}
        for script, description in tests:
            results[description] = self.run_test_script(script, description)
        
        return results
    
    def run_property_tests(self):
        """运行属性测试"""
        logger.info("\n🧪 运行属性测试...")
        
        # 查找所有属性测试文件
        property_test_files = [
            'test_properties.py',
            'test_auth_api.py',
            'test_composition_api.py',
            'test_composition_properties.py',
            'test_file_processing_properties.py',
            'test_monitoring_properties.py',
            'test_admin_management_properties.py',
        ]
        
        results = {}
        for test_file in property_test_files:
            test_path = BASE_DIR / test_file
            if test_path.exists():
                description = f'属性测试 - {test_file}'
                results[description] = self.run_test_script(test_file, description)
        
        return results
    
    def generate_final_report(self):
        """生成最终测试报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 集成测试最终报告")
        logger.info("=" * 80)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.test_results.items():
            logger.info(f"\n📋 {category}:")
            logger.info("-" * 40)
            
            category_total = len(tests)
            category_passed = sum(1 for result in tests.values() if result)
            
            total_tests += category_total
            passed_tests += category_passed
            
            for test_name, result in tests.items():
                status = "✅ 通过" if result else "❌ 失败"
                logger.info(f"  {status} {test_name}")
            
            success_rate = category_passed / category_total if category_total > 0 else 0
            logger.info(f"\n  分类汇总: {category_passed}/{category_total} ({success_rate:.1%})")
        
        # 总体统计
        logger.info("\n" + "=" * 80)
        logger.info("🎯 总体统计")
        logger.info("=" * 80)
        
        overall_success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过测试: {passed_tests}")
        logger.info(f"失败测试: {total_tests - passed_tests}")
        logger.info(f"成功率: {overall_success_rate:.1%}")
        
        # 评估结果
        if overall_success_rate >= 0.95:
            logger.info("\n🎉 优秀！系统质量很高，几乎所有测试都通过了。")
        elif overall_success_rate >= 0.85:
            logger.info("\n✅ 良好！系统基本功能正常，少数测试失败。")
        elif overall_success_rate >= 0.70:
            logger.info("\n⚠️  一般！系统有一些问题需要修复。")
        else:
            logger.info("\n❌ 较差！系统存在较多问题，需要重点关注。")
        
        return overall_success_rate >= 0.85
    
    def run_all_tests(self, include_performance=True, include_properties=True):
        """运行所有测试"""
        logger.info("🚀 开始运行完整集成测试套件")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        try:
            # 1. 运行基础系统测试
            self.test_results['基础系统测试'] = self.run_basic_system_tests()
            
            # 2. 启动测试服务器（如果需要）
            server_started = self.start_test_server()
            
            if server_started:
                # 3. 运行集成测试
                self.test_results['集成测试'] = self.run_integration_tests()
                
                # 4. 运行性能测试（可选）
                if include_performance:
                    self.test_results['性能测试'] = self.run_performance_tests()
                
                # 5. 运行属性测试（可选）
                if include_properties:
                    self.test_results['属性测试'] = self.run_property_tests()
            else:
                logger.error("❌ 无法启动测试服务器，跳过需要服务器的测试")
            
            # 6. 生成最终报告
            success = self.generate_final_report()
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"\n⏱️  总测试时间: {duration:.1f} 秒")
            
            return success
            
        finally:
            # 清理
            self.stop_test_server()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='道士经文视频管理系统集成测试')
    parser.add_argument('--no-performance', action='store_true', help='跳过性能测试')
    parser.add_argument('--no-properties', action='store_true', help='跳过属性测试')
    parser.add_argument('--basic-only', action='store_true', help='只运行基础测试')
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner()
    
    if args.basic_only:
        # 只运行基础测试
        logger.info("🔧 运行基础测试模式")
        results = runner.run_basic_system_tests()
        success = all(results.values())
        
        logger.info(f"\n📊 基础测试结果: {sum(results.values())}/{len(results)} 通过")
        
        if success:
            logger.info("✅ 所有基础测试通过")
        else:
            logger.info("❌ 部分基础测试失败")
    else:
        # 运行完整测试套件
        include_performance = not args.no_performance
        include_properties = not args.no_properties
        
        success = runner.run_all_tests(
            include_performance=include_performance,
            include_properties=include_properties
        )
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)