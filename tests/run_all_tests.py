#!/usr/bin/env python3
"""
测试运行主程序 - 运行所有测试并生成报告
"""
import sys
import os
import time
import json
from datetime import datetime

# 导入各个测试模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_unit import run_unit_tests
from test_functional import run_functional_tests
from test_integration import run_integration_tests
from test_performance import run_performance_tests
from test_exception import run_exception_tests


def generate_charts_data(results):
    """生成图表数据"""
    # 测试类型分布数据（柱状图）
    chart1_data = {
        'categories': ['单元测试', '功能测试', '集成测试', '性能测试', '异常测试'],
        'values': [
            results['unit']['total'],
            results['functional']['total'],
            results['integration']['total'],
            results['performance']['total'],
            results['exception']['total']
        ],
        'passed': [
            results['unit']['passed'],
            results['functional']['passed'],
            results['integration']['passed'],
            results['performance']['passed'],
            results['exception']['passed']
        ]
    }
    
    # 测试通过率趋势（折线图）
    chart2_data = {
        'categories': ['单元测试', '功能测试', '集成测试', '性能测试', '异常测试'],
        'pass_rates': [
            results['unit']['passed'] / results['unit']['total'] * 100 if results['unit']['total'] > 0 else 0,
            results['functional']['passed'] / results['functional']['total'] * 100 if results['functional']['total'] > 0 else 0,
            results['integration']['passed'] / results['integration']['total'] * 100 if results['integration']['total'] > 0 else 0,
            results['performance']['passed'] / results['performance']['total'] * 100 if results['performance']['total'] > 0 else 0,
            results['exception']['passed'] / results['exception']['total'] * 100 if results['exception']['total'] > 0 else 0
        ]
    }
    
    # 测试结果分布（饼图）
    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_errors = sum(r['errors'] for r in results.values())
    
    chart3_data = {
        'labels': ['通过', '失败', '错误'],
        'values': [total_passed, total_failed, total_errors]
    }
    
    return chart1_data, chart2_data, chart3_data


def generate_html_report(results, charts_data, duration):
    """生成HTML测试报告"""
    chart1, chart2, chart3 = charts_data
    
    total_tests = sum(r['total'] for r in results.values())
    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_errors = sum(r['errors'] for r in results.values())
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工厂火灾检测系统 - 测试报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        .summary-card .number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card.passed {{ border-top: 4px solid #28a745; }}
        .summary-card.passed .number {{ color: #28a745; }}
        .summary-card.failed {{ border-top: 4px solid #dc3545; }}
        .summary-card.failed .number {{ color: #dc3545; }}
        .summary-card.errors {{ border-top: 4px solid #ffc107; }}
        .summary-card.errors .number {{ color: #ffc107; }}
        .summary-card.total {{ border-top: 4px solid #17a2b8; }}
        .summary-card.total .number {{ color: #17a2b8; }}
        .summary-card.rate {{ border-top: 4px solid #6f42c1; }}
        .summary-card.rate .number {{ color: #6f42c1; }}
        .charts-section {{
            padding: 40px;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }}
        .chart-container {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .chart-container h3 {{
            margin-bottom: 20px;
            color: #333;
            text-align: center;
        }}
        .chart-wrapper {{
            position: relative;
            height: 300px;
        }}
        .details-section {{
            padding: 40px;
            background: #f8f9fa;
        }}
        .details-section h2 {{
            margin-bottom: 20px;
            color: #333;
        }}
        .test-type-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .test-type-table th,
        .test-type-table td {{
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
        }}
        .test-type-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .test-type-table tr:hover {{
            background: #f5f5f5;
        }}
        .status-badge {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .status-success {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            background: #333;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 工厂火灾检测系统测试报告</h1>
            <p class="subtitle">Factory Fire Detection System Test Report</p>
            <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>测试耗时: {duration:.2f} 秒</p>
        </div>
        
        <div class="summary">
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
        
        <div class="charts-section">
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>📊 各类测试用例数量分布</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart1"></canvas>
                    </div>
                </div>
                <div class="chart-container">
                    <h3>📈 测试通过率趋势</h3>
                    <div class="chart-wrapper">
                        <canvas id="chart2"></canvas>
                    </div>
                </div>
            </div>
            <div class="chart-container" style="max-width: 600px; margin: 0 auto;">
                <h3>🥧 测试结果分布</h3>
                <div class="chart-wrapper">
                    <canvas id="chart3"></canvas>
                </div>
            </div>
        </div>
        
        <div class="details-section">
            <h2>📋 测试详情</h2>
            <table class="test-type-table">
                <thead>
                    <tr>
                        <th>测试类型</th>
                        <th>总用例</th>
                        <th>通过</th>
                        <th>失败</th>
                        <th>错误</th>
                        <th>通过率</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>单元测试</td>
                        <td>{results['unit']['total']}</td>
                        <td>{results['unit']['passed']}</td>
                        <td>{results['unit']['failed']}</td>
                        <td>{results['unit']['errors']}</td>
                        <td>{results['unit']['passed']/results['unit']['total']*100:.1f}%</td>
                        <td><span class="status-badge {'status-success' if results['unit']['success'] else 'status-failed'}">{'通过' if results['unit']['success'] else '未通过'}</span></td>
                    </tr>
                    <tr>
                        <td>功能测试</td>
                        <td>{results['functional']['total']}</td>
                        <td>{results['functional']['passed']}</td>
                        <td>{results['functional']['failed']}</td>
                        <td>{results['functional']['errors']}</td>
                        <td>{results['functional']['passed']/results['functional']['total']*100:.1f}%</td>
                        <td><span class="status-badge {'status-success' if results['functional']['success'] else 'status-failed'}">{'通过' if results['functional']['success'] else '未通过'}</span></td>
                    </tr>
                    <tr>
                        <td>集成测试</td>
                        <td>{results['integration']['total']}</td>
                        <td>{results['integration']['passed']}</td>
                        <td>{results['integration']['failed']}</td>
                        <td>{results['integration']['errors']}</td>
                        <td>{results['integration']['passed']/results['integration']['total']*100:.1f}%</td>
                        <td><span class="status-badge {'status-success' if results['integration']['success'] else 'status-failed'}">{'通过' if results['integration']['success'] else '未通过'}</span></td>
                    </tr>
                    <tr>
                        <td>性能测试</td>
                        <td>{results['performance']['total']}</td>
                        <td>{results['performance']['passed']}</td>
                        <td>{results['performance']['failed']}</td>
                        <td>{results['performance']['errors']}</td>
                        <td>{results['performance']['passed']/results['performance']['total']*100:.1f}%</td>
                        <td><span class="status-badge {'status-success' if results['performance']['success'] else 'status-failed'}">{'通过' if results['performance']['success'] else '未通过'}</span></td>
                    </tr>
                    <tr>
                        <td>异常测试</td>
                        <td>{results['exception']['total']}</td>
                        <td>{results['exception']['passed']}</td>
                        <td>{results['exception']['failed']}</td>
                        <td>{results['exception']['errors']}</td>
                        <td>{results['exception']['passed']/results['exception']['total']*100:.1f}%</td>
                        <td><span class="status-badge {'status-success' if results['exception']['success'] else 'status-failed'}">{'通过' if results['exception']['success'] else '未通过'}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>工厂火灾检测系统 - 自动化测试报告</p>
            <p>Generated by Python Test Framework</p>
        </div>
    </div>
    
    <script>
        // 图表1: 测试用例数量分布（柱状图）
        const ctx1 = document.getElementById('chart1').getContext('2d');
        new Chart(ctx1, {{
            type: 'bar',
            data: {{
                labels: {chart1['categories']},
                datasets: [{{
                    label: '总用例数',
                    data: {chart1['values']},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2
                }}, {{
                    label: '通过数',
                    data: {chart1['passed']},
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        
        // 图表2: 测试通过率趋势（折线图）
        const ctx2 = document.getElementById('chart2').getContext('2d');
        new Chart(ctx2, {{
            type: 'line',
            data: {{
                labels: {chart2['categories']},
                datasets: [{{
                    label: '通过率 (%)',
                    data: {chart2['pass_rates']},
                    borderColor: 'rgba(111, 66, 193, 1)',
                    backgroundColor: 'rgba(111, 66, 193, 0.2)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
        
        // 图表3: 测试结果分布（饼图）
        const ctx3 = document.getElementById('chart3').getContext('2d');
        new Chart(ctx3, {{
            type: 'pie',
            data: {{
                labels: {chart3['labels']},
                datasets: [{{
                    data: {chart3['values']},
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.8)',
                        'rgba(220, 53, 69, 0.8)',
                        'rgba(255, 193, 7, 0.8)'
                    ],
                    borderColor: [
                        'rgba(40, 167, 69, 1)',
                        'rgba(220, 53, 69, 1)',
                        'rgba(255, 193, 7, 1)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html


def main():
    """主函数"""
    print("="*60)
    print("工厂火灾检测系统 - 全面测试")
    print("="*60)
    print()
    
    start_time = time.time()
    
    # 运行所有测试
    print("【1/5】正在运行单元测试...")
    unit_results = run_unit_tests()
    print()
    
    print("【2/5】正在运行功能测试...")
    functional_results = run_functional_tests()
    print()
    
    print("【3/5】正在运行集成测试...")
    integration_results = run_integration_tests()
    print()
    
    print("【4/5】正在运行性能测试...")
    performance_results = run_performance_tests()
    print()
    
    print("【5/5】正在运行异常测试...")
    exception_results = run_exception_tests()
    print()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 汇总结果
    all_results = {
        'unit': unit_results,
        'functional': functional_results,
        'integration': integration_results,
        'performance': performance_results,
        'exception': exception_results
    }
    
    # 生成图表数据
    charts_data = generate_charts_data(all_results)
    
    # 生成HTML报告
    html_report = generate_html_report(all_results, charts_data, duration)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'test_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # 控制台输出汇总
    print("="*60)
    print("测试完成！汇总结果")
    print("="*60)
    
    total_tests = sum(r['total'] for r in all_results.values())
    total_passed = sum(r['passed'] for r in all_results.values())
    total_failed = sum(r['failed'] for r in all_results.values())
    total_errors = sum(r['errors'] for r in all_results.values())
    
    print(f"总测试数: {total_tests}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"错误: {total_errors}")
    print(f"通过率: {total_passed/total_tests*100:.1f}%")
    print(f"总耗时: {duration:.2f} 秒")
    print()
    print(f"详细报告已保存至: {report_path}")
    print("="*60)


if __name__ == '__main__':
    main()
