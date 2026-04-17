#!/usr/bin/env python3
"""
完整项目测试运行器 - 运行所有测试并生成综合报告
包括：单元测试、功能测试、集成测试、性能测试、异常测试、真实代码测试、YOLO内部测试
"""
import unittest
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有测试模块
from test_unit import run_unit_tests
from test_functional import run_functional_tests
from test_integration import run_integration_tests
from test_performance import run_performance_tests
from test_exception import run_exception_tests
from test_real_code import run_real_code_tests
from test_yolo_internal import run_yolo_internal_tests


def run_all_test_suites():
    """运行所有测试套件"""
    results = {}
    
    print("="*70)
    print("工厂火灾检测系统 - 完整项目测试")
    print("="*70)
    print()
    
    test_suites = [
        ("单元测试", run_unit_tests),
        ("功能测试", run_functional_tests),
        ("集成测试", run_integration_tests),
        ("性能测试", run_performance_tests),
        ("异常测试", run_exception_tests),
        ("真实代码测试", run_real_code_tests),
        ("YOLO内部测试", run_yolo_internal_tests),
    ]
    
    for name, test_func in test_suites:
        print(f"\n{'='*70}")
        print(f"运行: {name}")
        print('='*70)
        
        try:
            result = test_func()
            results[name] = result
        except Exception as e:
            print(f"错误: {e}")
            results[name] = {
                'total': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'success': False
            }
    
    return results


def generate_complete_report(all_results, duration):
    """生成完整测试报告"""
    
    # 计算总体统计
    total_tests = sum(r['total'] for r in all_results.values())
    total_passed = sum(r['passed'] for r in all_results.values())
    total_failed = sum(r['failed'] for r in all_results.values())
    total_errors = sum(r['errors'] for r in all_results.values())
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    # 生成HTML报告
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工厂火灾检测系统 - 完整测试报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; }}
        
        .summary-grid {{
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
        }}
        
        .summary-card .number {{
            font-size: 2.5em;
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
        
        .charts-section {{
            padding: 40px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
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
        
        .test-suite-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .test-suite-table th,
        .test-suite-table td {{
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .test-suite-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .test-suite-table tr:hover {{
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
        
        .test-categories {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        
        .category-box {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        
        .category-box h4 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .category-box ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .category-box li {{
            padding: 5px 0;
            color: #666;
        }}
        
        .category-box li::before {{
            content: "✓ ";
            color: #28a745;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 工厂火灾检测系统</h1>
            <h2>完整项目测试报告</h2>
            <div class="meta">
                <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>总耗时: {duration:.2f} 秒</p>
            </div>
        </div>
        
        <div class="summary-grid">
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
            <h2 style="text-align: center; margin-bottom: 30px; color: #333;">📊 测试统计图表</h2>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>各测试套件用例数量</h3>
                    <div class="chart-wrapper">
                        <canvas id="barChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>测试通过率对比</h3>
                    <div class="chart-wrapper">
                        <canvas id="lineChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="chart-container" style="max-width: 600px; margin: 0 auto;">
                <h3>测试结果分布</h3>
                <div class="chart-wrapper">
                    <canvas id="pieChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="details-section">
            <h2 style="margin-bottom: 20px; color: #333;">📋 测试套件详情</h2>
            
            <table class="test-suite-table">
                <thead>
                    <tr>
                        <th>测试套件</th>
                        <th>总用例</th>
                        <th>通过</th>
                        <th>失败</th>
                        <th>错误</th>
                        <th>通过率</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # 添加每个测试套件的结果
    for suite_name, result in all_results.items():
        pass_rate_suite = (result['passed'] / result['total'] * 100) if result['total'] > 0 else 0
        status_class = 'status-success' if result['success'] else 'status-failed'
        status_text = '通过' if result['success'] else '未通过'
        
        html += f"""
                    <tr>
                        <td><strong>{suite_name}</strong></td>
                        <td>{result['total']}</td>
                        <td>{result['passed']}</td>
                        <td>{result['failed']}</td>
                        <td>{result['errors']}</td>
                        <td>{pass_rate_suite:.1f}%</td>
                        <td><span class="status-badge {status_class}">{status_text}</span></td>
                    </tr>
"""
    
    # 准备图表数据
    suite_names = list(all_results.keys())
    suite_totals = [r['total'] for r in all_results.values()]
    suite_passed = [r['passed'] for r in all_results.values()]
    suite_rates = [(r['passed']/r['total']*100) if r['total'] > 0 else 0 for r in all_results.values()]
    
    html += f"""
                </tbody>
            </table>
            
            <h2 style="margin-bottom: 20px; color: #333;">📁 测试内容说明</h2>
            
            <div class="test-categories">
                <div class="category-box">
                    <h4>单元测试</h4>
                    <ul>
                        <li>温度数据处理</li>
                        <li>警报逻辑判断</li>
                        <li>模型配置验证</li>
                        <li>工具函数测试</li>
                    </ul>
                </div>
                
                <div class="category-box">
                    <h4>功能测试</h4>
                    <ul>
                        <li>温度数据接收</li>
                        <li>火灾检测功能</li>
                        <li>模型加载功能</li>
                        <li>GUI组件功能</li>
                    </ul>
                </div>
                
                <div class="category-box">
                    <h4>集成测试</h4>
                    <ul>
                        <li>C#到Python通信</li>
                        <li>检测与警报集成</li>
                        <li>模型与检测集成</li>
                        <li>端到端数据流</li>
                    </ul>
                </div>
                
                <div class="category-box">
                    <h4>性能测试</h4>
                    <ul>
                        <li>响应时间测试</li>
                        <li>吞吐量测试</li>
                        <li>内存使用测试</li>
                        <li>并发性能测试</li>
                    </ul>
                </div>
                
                <div class="category-box">
                    <h4>异常测试</h4>
                    <ul>
                        <li>无效输入处理</li>
                        <li>网络错误处理</li>
                        <li>资源错误处理</li>
                        <li>边界条件测试</li>
                    </ul>
                </div>
                
                <div class="category-box">
                    <h4>YOLO内部测试</h4>
                    <ul>
                        <li>模型加载与信息</li>
                        <li>推理功能测试</li>
                        <li>训练配置验证</li>
                        <li>数据集配置检查</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>工厂火灾检测系统 - 完整项目测试报告</p>
            <p>包含YOLO模型内部细节测试</p>
        </div>
    </div>
    
    <script>
        // 柱状图：各测试套件用例数量
        const ctx1 = document.getElementById('barChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'bar',
            data: {{
                labels: {suite_names},
                datasets: [{{
                    label: '总用例数',
                    data: {suite_totals},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2
                }}, {{
                    label: '通过数',
                    data: {suite_passed},
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        
        // 折线图：测试通过率
        const ctx2 = document.getElementById('lineChart').getContext('2d');
        new Chart(ctx2, {{
            type: 'line',
            data: {{
                labels: {suite_names},
                datasets: [{{
                    label: '通过率 (%)',
                    data: {suite_rates},
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
                    y: {{ beginAtZero: true, max: 100 }}
                }}
            }}
        }});
        
        // 饼图：测试结果分布
        const ctx3 = document.getElementById('pieChart').getContext('2d');
        new Chart(ctx3, {{
            type: 'pie',
            data: {{
                labels: ['通过', '失败', '错误'],
                datasets: [{{
                    data: [{total_passed}, {total_failed}, {total_errors}],
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
    start_time = time.time()
    
    # 运行所有测试
    all_results = run_all_test_suites()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 生成报告
    html_report = generate_complete_report(all_results, duration)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), 'complete_test_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # 控制台输出汇总
    total_tests = sum(r['total'] for r in all_results.values())
    total_passed = sum(r['passed'] for r in all_results.values())
    total_failed = sum(r['failed'] for r in all_results.values())
    total_errors = sum(r['errors'] for r in all_results.values())
    
    print("\n" + "="*70)
    print("完整项目测试完成！")
    print("="*70)
    print(f"总测试数: {total_tests}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"错误: {total_errors}")
    print(f"通过率: {total_passed/total_tests*100:.1f}%" if total_tests > 0 else "N/A")
    print(f"总耗时: {duration:.2f} 秒")
    print(f"\n完整报告已保存至: {report_path}")
    print("="*70)


if __name__ == '__main__':
    main()
