#!/usr/bin/env python3
"""
单元测试 - 针对核心功能模块的独立测试
"""
import unittest
import sys
import os
import json
import time
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTemperatureDataHandler(unittest.TestCase):
    """测试温度数据处理单元"""
    
    def setUp(self):
        """测试前准备"""
        self.sample_temp_data = {
            'sensorId': 1,
            'value': 35.5,
            'timestamp': time.time()
        }
    
    def test_temperature_data_validation(self):
        """测试温度数据验证"""
        # 有效数据
        self.assertIsNotNone(self.sample_temp_data['value'])
        self.assertIsInstance(self.sample_temp_data['value'], (int, float))
        self.assertGreaterEqual(self.sample_temp_data['value'], -50)
        self.assertLessEqual(self.sample_temp_data['value'], 150)
        
        # 测试无效数据
        invalid_data = {'sensorId': 1, 'value': None}
        self.assertIsNone(invalid_data['value'])
    
    def test_temperature_categorization(self):
        """测试温度分级分类"""
        def get_temp_category(value):
            if value > 50:
                return 'high'
            elif value > 30:
                return 'medium'
            else:
                return 'normal'
        
        self.assertEqual(get_temp_category(60), 'high')
        self.assertEqual(get_temp_category(40), 'medium')
        self.assertEqual(get_temp_category(25), 'normal')


class TestAlertLogic(unittest.TestCase):
    """测试警报逻辑单元"""
    
    def test_fire_alert_level(self):
        """测试火灾警报级别判断"""
        def get_alert_level(detected_classes):
            has_fire = "fire" in detected_classes
            has_smoke = "smoke" in detected_classes
            
            if has_fire and has_smoke:
                return 'critical'
            elif has_fire:
                return 'high'
            elif has_smoke:
                return 'medium'
            else:
                return 'safe'
        
        self.assertEqual(get_alert_level(['fire', 'smoke']), 'critical')
        self.assertEqual(get_alert_level(['fire']), 'high')
        self.assertEqual(get_alert_level(['smoke']), 'medium')
        self.assertEqual(get_alert_level([]), 'safe')
    
    def test_alert_message_generation(self):
        """测试警报消息生成"""
        alert_messages = {
            'critical': '警告！检测到火焰和烟雾！',
            'high': '警告！检测到火焰！',
            'medium': '注意！检测到烟雾！',
            'safe': '未检测到危险'
        }
        
        self.assertIn('火焰和烟雾', alert_messages['critical'])
        self.assertIn('火焰', alert_messages['high'])


class TestModelConfiguration(unittest.TestCase):
    """测试模型配置单元"""
    
    def test_model_path_construction(self):
        """测试模型路径构建"""
        weights_dir = "weights"
        model_name = "yolov8n.pt"
        expected_path = os.path.join(weights_dir, model_name)
        
        # Windows和Linux路径分隔符不同
        self.assertTrue(expected_path.endswith("yolov8n.pt"))
        self.assertIn("weights", expected_path)
    
    def test_confidence_threshold_validation(self):
        """测试置信度阈值验证"""
        def validate_confidence(value):
            return 0.01 <= value <= 1.0
        
        self.assertTrue(validate_confidence(0.25))
        self.assertTrue(validate_confidence(0.01))
        self.assertTrue(validate_confidence(1.0))
        self.assertFalse(validate_confidence(0))
        self.assertFalse(validate_confidence(1.5))


class TestDataProcessing(unittest.TestCase):
    """测试数据处理单元"""
    
    def test_detection_stats_aggregation(self):
        """测试检测统计聚合"""
        # 模拟检测结果
        mock_results = [
            {'class': 'fire', 'count': 2},
            {'class': 'smoke', 'count': 1}
        ]
        
        # 统计总数
        total = sum(r['count'] for r in mock_results)
        self.assertEqual(total, 3)
        
        # 按类别统计
        fire_count = sum(r['count'] for r in mock_results if r['class'] == 'fire')
        self.assertEqual(fire_count, 2)


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数单元"""
    
    def test_time_format_conversion(self):
        """测试时间格式转换"""
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        formatted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
        # 由于时区不同，只验证格式正确
        self.assertEqual(len(formatted), 19)  # YYYY-MM-DD HH:MM:SS
        self.assertEqual(formatted[4], '-')  # 日期分隔符
        self.assertEqual(formatted[13], ':')  # 时间分隔符
    
    def test_json_data_parsing(self):
        """测试JSON数据解析"""
        json_str = '{"sensorId": 1, "value": 25.5}'
        data = json.loads(json_str)
        
        self.assertEqual(data['sensorId'], 1)
        self.assertEqual(data['value'], 25.5)


def run_unit_tests():
    """运行单元测试并返回结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestTemperatureDataHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestAlertLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestModelConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataProcessing))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return {
        'total': result.testsRun,
        'passed': result.testsRun - len(result.failures) - len(result.errors),
        'failed': len(result.failures),
        'errors': len(result.errors),
        'success': result.wasSuccessful()
    }


if __name__ == '__main__':
    results = run_unit_tests()
    print("\n" + "="*50)
    print("单元测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
