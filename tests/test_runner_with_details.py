#!/usr/bin/env python3
"""
详细测试运行器 - 生成包含每个测试用例详细结果的报告
"""
import unittest
import sys
import os
import time
import json
import traceback
from datetime import datetime
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入测试模块
from test_unit import (
    TestTemperatureDataHandler, TestAlertLogic, TestModelConfiguration,
    TestDataProcessing, TestUtilityFunctions
)
from test_functional import (
    TestTemperatureReception, TestFireDetection, TestModelLoading,
    TestGUIComponents, TestHTTPCommunication, TestDataPersistence
)
from test_integration import (
    TestTemperatureIntegration, TestDetectionAlertIntegration,
    TestModelDetectionIntegration, TestGUIFunctionIntegration, TestDataFlowIntegration
)
from test_performance import (
    TestResponseTime, TestThroughput, TestMemoryUsage,
    TestConcurrency, TestScalability
)
from test_exception import (
    TestInvalidInput, TestNetworkErrors, TestResourceErrors,
    TestDataCorruption, TestBoundaryConditions, TestRecoveryMechanisms, TestConcurrentErrors
)


class DetailedTestResult(unittest.TestResult):
    """详细的测试结果收集器"""
    
    def __init__(self):
        super().__init__()
        self.test_details = []
        self.current_test_start_time = None
        
    def startTest(self, test):
        super().startTest(test)
        self.current_test_start_time = time.time()
        
    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.time() - self.current_test_start_time
        self.test_details.append({
            'name': str(test),
            'status': 'PASSED',
            'duration': duration,
            'message': '',
            'doc': test._testMethodDoc or '无描述'
        })
        
    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.time() - self.current_test_start_time
        error_msg = self._exc_info_to_string(err, test)
        self.test_details.append({
            'name': str(test),
            'status': 'FAILED',
            'duration': duration,
            'message': error_msg,
            'doc': test._testMethodDoc or '无描述'
        })
        
    def addError(self, test, err):
        super().addError(test, err)
        duration = time.time() - self.current_test_start_time
        error_msg = self._exc_info_to_string(err, test)
        self.test_details.append({
            'name': str(test),
            'status': 'ERROR',
            'duration': duration,
            'message': error_msg,
            'doc': test._testMethodDoc or '无描述'
        })


def run_test_class(test_class, category_name):
    """运行单个测试类并收集详细结果"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_class)
    
    result = DetailedTestResult()
    start_time = time.time()
    suite.run(result)
    end_time = time.time()
    
    return {
        'category': category_name,
        'class_name': test_class.__name__,
        'total': result.testsRun,
        'passed': len([t for t in result.test_details if t['status'] == 'PASSED']),
        'failed': len([t for t in result.test_details if t['status'] == 'FAILED']),
        'errors': len([t for t in result.test_details if t['status'] == 'ERROR']),
        'duration': end_time - start_time,
        'details': result.test_details,
        'success': result.wasSuccessful()
    }


def run_all_tests_detailed():
    """运行所有测试并收集详细结果"""
    all_results = []
    
    # 单元测试
    print("运行单元测试...")
    all_results.append(run_test_class(TestTemperatureDataHandler, '单元测试'))
    all_results.append(run_test_class(TestAlertLogic, '单元测试'))
    all_results.append(run_test_class(TestModelConfiguration, '单元测试'))
    all_results.append(run_test_class(TestDataProcessing, '单元测试'))
    all_results.append(run_test_class(TestUtilityFunctions, '单元测试'))
    
    # 功能测试
    print("运行功能测试...")
    all_results.append(run_test_class(TestTemperatureReception, '功能测试'))
    all_results.append(run_test_class(TestFireDetection, '功能测试'))
    all_results.append(run_test_class(TestModelLoading, '功能测试'))
    all_results.append(run_test_class(TestGUIComponents, '功能测试'))
    all_results.append(run_test_class(TestHTTPCommunication, '功能测试'))
    all_results.append(run_test_class(TestDataPersistence, '功能测试'))
    
    # 集成测试
    print("运行集成测试...")
    all_results.append(run_test_class(TestTemperatureIntegration, '集成测试'))
    all_results.append(run_test_class(TestDetectionAlertIntegration, '集成测试'))
    all_results.append(run_test_class(TestModelDetectionIntegration, '集成测试'))
    all_results.append(run_test_class(TestGUIFunctionIntegration, '集成测试'))
    all_results.append(run_test_class(TestDataFlowIntegration, '集成测试'))
    
    # 性能测试
    print("运行性能测试...")
    all_results.append(run_test_class(TestResponseTime, '性能测试'))
    all_results.append(run_test_class(TestThroughput, '性能测试'))
    all_results.append(run_test_class(TestMemoryUsage, '性能测试'))
    all_results.append(run_test_class(TestConcurrency, '性能测试'))
    all_results.append(run_test_class(TestScalability, '性能测试'))
    
    # 异常测试
    print("运行异常测试...")
    all_results.append(run_test_class(TestInvalidInput, '异常测试'))
    all_results.append(run_test_class(TestNetworkErrors, '异常测试'))
    all_results.append(run_test_class(TestResourceErrors, '异常测试'))
    all_results.append(run_test_class(TestDataCorruption, '异常测试'))
    all_results.append(run_test_class(TestBoundaryConditions, '异常测试'))
    all_results.append(run_test_class(TestRecoveryMechanisms, '异常测试'))
    all_results.append(run_test_class(TestConcurrentErrors, '异常测试'))
    
    return all_results


def generate_detailed_html_report(all_results, total_duration):
    """生成详细的HTML测试报告"""
    
    # 计算汇总数据
    total_tests = sum(r['total'] for r in all_results)
    total_passed = sum(r['passed'] for r in all_results)
    total_failed = sum(r['failed'] for r in all_results)
    total_errors = sum(r['errors'] for r in all_results)
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    # 按类别分组
    categories = {}
    for result in all_results:
        cat = result['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)
    
    # 生成详细测试用例表格
    def generate_test_cases_table(details, category_name):
        rows = ""
        for i, test in enumerate(details, 1):
            status_class = {
                'PASSED': 'status-passed',
                'FAILED': 'status-failed',
                'ERROR': 'status-error'
            }.get(test['status'], '')
            
            status_icon = {
                'PASSED': '✓',
                'FAILED': '✗',
                'ERROR': '⚠'
            }.get(test['status'], '?')
            
            # 截断错误信息，只显示前200字符
            message = test['message']
            if len(message) > 200:
                message = message[:200] + "..."
            message = message.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            
            rows += f"""
                <tr class="{status_class}">
                    <td>{i}</td>
                    <td class="test-name">{test['name'].split('.')[-1]}</td>
                    <td class="test-doc">{test['doc']}</td>
                    <td class="test-status {status_class}">{status_icon} {test['status']}</td>
                    <td class="test-duration">{test['duration']*1000:.1f}ms</td>
                    <td class="test-message">{message if message else '-'}</td>
                </tr>
            """
        return rows
    
    # 生成分类汇总卡片
    category_cards = ""
    for cat_name, cat_results in categories.items():
        cat_total = sum(r['total'] for r in cat_results)
        cat_passed = sum(r['passed'] for r in cat_results)
        cat_failed = sum(r['failed'] for r in cat_results)
        cat_errors = sum(r['errors'] for r in cat_results)
        cat_rate = (cat_passed / cat_total * 100) if cat_total > 0 else 0
        
        category_cards += f"""
            <div class="category-card">
                <h3>{cat_name}</h3>
                <div class="category-stats">
                    <div class="stat">
                        <span class="stat-value">{cat_total}</span>
                        <span class="stat-label">总用例</span>
                    </div>
                    <div class="stat passed">
                        <span class="stat-value">{cat_passed}</span>
                        <span class="stat-label">通过</span>
                    </div>
                    <div class="stat failed">
                        <span class="stat-value">{cat_failed}</span>
                        <span class="stat-label">失败</span>
                    </div>
                    <div class="stat error">
                        <span class="stat-value">{cat_errors}</span>
                        <span class="stat-label">错误</span>
                    </div>
                    <div class="stat rate">
                        <span class="stat-value">{cat_rate:.1f}%</span>
                        <span class="stat-label">通过率</span>
                    </div>
                </div>
            </div>
        """
    
    # 生成详细测试列表
    test_details_sections = ""
    for cat_name, cat_results in categories.items():
        for result in cat_results:
            if result['details']:
                test_cases_rows = generate_test_cases_table(result['details'], cat_name)
                test_details_sections += f"""
                    <div class="test-class-section">
                        <h4 class="class-name">{result['class_name']}</h4>
                        <div class="class-summary">
                            <span>总: {result['total']}</span>
                            <span class="passed">通过: {result['passed']}</span>
                            <span class="failed">失败: {result['failed']}</span>
                            <span class="error">错误: {result['errors']}</span>
                            <span>耗时: {result['duration']:.2f}s</span>
                        </div>
                        <table class="test-cases-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>测试名称</th>
                                    <th>测试描述</th>
                                    <th>状态</th>
                                    <th>耗时</th>
                                    <th>详细信息</th>
                                </tr>
                            </thead>
                            <tbody>
                                {test_cases_rows}
                            </tbody>
                        </table>
                    </div>
                """
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工厂火灾检测系统 - 详细测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; margin-top: 10px; }}
        
        .summary-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .summary-card {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .summary-card .number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card.total {{ border-top: 4px solid #17a2b8; }}
        .summary-card.total .number {{ color: #17a2b8; }}
        .summary-card.passed {{ border-top: 4px solid #28a745; }}
        .summary-card.passed .number {{ color: #28a745; }}
        .summary-card.failed {{ border-top: 4px solid #dc3545; }}
        .summary-card.failed .number {{ color: #dc3545; }}
        .summary-card.errors {{ border-top: 4px solid #ffc107; }}
        .summary-card.errors .number {{ color: #ffc107; }}
        .summary-card.rate {{ border-top: 4px solid #6f42c1; }}
        .summary-card.rate .number {{ color: #6f42c1; }}
        
        .categories-section {{
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .category-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .category-card h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .category-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 15px;
        }}
        
        .stat {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .stat-value {{
            display: block;
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .stat.passed .stat-value {{ color: #28a745; }}
        .stat.failed .stat-value {{ color: #dc3545; }}
        .stat.error .stat-value {{ color: #ffc107; }}
        .stat.rate .stat-value {{ color: #6f42c1; }}
        
        .details-section {{
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .details-section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        
        .test-class-section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .class-name {{
            color: #667eea;
            font-size: 1.2em;
            margin-bottom: 10px;
        }}
        
        .class-summary {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-size: 0.9em;
        }}
        .class-summary .passed {{ color: #28a745; font-weight: bold; }}
        .class-summary .failed {{ color: #dc3545; font-weight: bold; }}
        .class-summary .error {{ color: #ffc107; font-weight: bold; }}
        
        .test-cases-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        
        .test-cases-table th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        
        .test-cases-table td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .test-cases-table tr:hover {{
            background: #f5f5f5;
        }}
        
        .test-name {{ font-weight: bold; color: #333; }}
        .test-doc {{ color: #666; font-size: 0.9em; }}
        .test-status {{ font-weight: bold; }}
        .status-passed {{ color: #28a745; background: #d4edda; }}
        .status-failed {{ color: #dc3545; background: #f8d7da; }}
        .status-error {{ color: #856404; background: #fff3cd; }}
        .test-duration {{ color: #666; font-family: monospace; }}
        .test-message {{
            color: #dc3545;
            font-size: 0.85em;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            background: #333;
            color: white;
            margin-top: 50px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 工厂火灾检测系统详细测试报告</h1>
        <div class="meta">
            <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>总耗时: {total_duration:.2f} 秒</p>
        </div>
    </div>
    
    <div class="summary-section">
        <div class="summary-card total">
            <div class="label">总测试数</div>
            <div class="number">{total_tests}</div>
        </div>
        <div class="summary-card passed">
            <div class="label">通过</div>
            <div class="number">{total_passed}</div>
        </div>
        <div class="summary-card failed">
            <div class="label">失败</div>
            <div class="number">{total_failed}</div>
        </div>
        <div class="summary-card errors">
            <div class="label">错误</div>
            <div class="number">{total_errors}</div>
        </div>
        <div class="summary-card rate">
            <div class="label">通过率</div>
            <div class="number">{pass_rate:.1f}%</div>
        </div>
    </div>
    
    <div class="categories-section">
        <h2 style="margin-bottom: 20px; color: #333;">📊 分类统计</h2>
        {category_cards}
    </div>
    
    <div class="details-section">
        <h2>📋 详细测试结果</h2>
        {test_details_sections}
    </div>
    
    <div class="footer">
        <p>工厂火灾检测系统 - 自动化测试报告</p>
        <p>Generated by Python Test Framework</p>
    </div>
</body>
</html>
"""
    
    return html


def main():
    """主函数"""
    print("="*60)
    print("工厂火灾检测系统 - 详细测试")
    print("="*60)
    print()
    
    start_time = time.time()
    all_results = run_all_tests_detailed()
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 生成详细报告
    html_report = generate_detailed_html_report(all_results, total_duration)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'detailed_test_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # 控制台输出汇总
    total_tests = sum(r['total'] for r in all_results)
    total_passed = sum(r['passed'] for r in all_results)
    total_failed = sum(r['failed'] for r in all_results)
    total_errors = sum(r['errors'] for r in all_results)
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print(f"总测试数: {total_tests}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"错误: {total_errors}")
    print(f"通过率: {total_passed/total_tests*100:.1f}%")
    print(f"总耗时: {total_duration:.2f} 秒")
    print(f"\n详细报告已保存至: {report_path}")
    print("="*60)


if __name__ == '__main__':
    main()
