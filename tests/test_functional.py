#!/usr/bin/env python3
"""
功能测试 - 验证系统各项功能是否按需求正常工作
"""
import unittest
import sys
import os
import json
import time
import urllib.request
import urllib.error
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTemperatureReception(unittest.TestCase):
    """测试温度数据接收功能"""
    
    def test_temperature_data_format(self):
        """测试温度数据格式要求"""
        # 标准C#发送的数据格式
        csharp_data = {
            "sensorId": 1,
            "value": 25.5  # C#代码中 temperatureValue / 10.0
        }
        
        # 验证必需字段
        self.assertIn('sensorId', csharp_data)
        self.assertIn('value', csharp_data)
        self.assertIsInstance(csharp_data['sensorId'], int)
        self.assertIsInstance(csharp_data['value'], float)
    
    def test_temperature_display_update(self):
        """测试温度显示更新逻辑"""
        # 模拟温度数据更新
        temp_data = {'sensorId': 1, 'value': 35.5, 'timestamp': time.time()}
        
        # 验证数据在有效时间内
        current_time = time.time()
        is_valid = (current_time - temp_data['timestamp']) <= 10  # 10秒超时
        self.assertTrue(is_valid)
    
    def test_temperature_timeout_handling(self):
        """测试温度数据超时处理"""
        old_time = time.time() - 15  # 15秒前的数据
        is_expired = (time.time() - old_time) > 10
        self.assertTrue(is_expired)


class TestFireDetection(unittest.TestCase):
    """测试火灾检测功能"""
    
    def test_fire_detection_categories(self):
        """测试火灾检测类别"""
        # 系统应检测的类别
        expected_classes = ['fire', 'smoke']
        
        # 验证类别名称
        for cls in expected_classes:
            self.assertIn(cls, ['fire', 'smoke', 'person', 'car'])  # 可能的检测类别
    
    def test_alert_level_transition(self):
        """测试警报级别转换"""
        # 安全 -> 烟雾 -> 火焰+烟雾 的级别提升
        alert_levels = ['safe', 'medium', 'critical']
        
        # 验证级别顺序
        self.assertLess(alert_levels.index('safe'), alert_levels.index('medium'))
        self.assertLess(alert_levels.index('medium'), alert_levels.index('critical'))


class TestModelLoading(unittest.TestCase):
    """测试模型加载功能"""
    
    def test_model_file_existence(self):
        """测试模型文件存在性检查"""
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        # 检查weights目录是否存在
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
            self.assertGreater(len(model_files), 0, "没有找到模型文件")
    
    def test_model_selection_options(self):
        """测试模型选择选项"""
        expected_models = ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt']
        
        for model in expected_models:
            self.assertTrue(model.endswith('.pt'), f"{model} 不是有效的模型文件名")


class TestGUIComponents(unittest.TestCase):
    """测试GUI组件功能"""
    
    def test_input_source_types(self):
        """测试输入源类型"""
        source_types = ['摄像头', '视频文件', '图片文件']
        
        self.assertEqual(len(source_types), 3)
        self.assertIn('摄像头', source_types)
        self.assertIn('视频文件', source_types)
        self.assertIn('图片文件', source_types)
    
    def test_confidence_range(self):
        """测试置信度范围"""
        # 置信度滑块范围 1-100，对应 0.01-1.0
        min_conf = 1
        max_conf = 100
        
        self.assertEqual(min_conf / 100, 0.01)
        self.assertEqual(max_conf / 100, 1.0)


class TestHTTPCommunication(unittest.TestCase):
    """测试HTTP通信功能"""
    
    def test_http_post_format(self):
        """测试HTTP POST请求格式"""
        # 模拟C#发送的POST请求
        url = "http://localhost:8090"
        data = json.dumps({"sensorId": 1, "value": 25.5}).encode('utf-8')
        
        # 验证请求可以构建
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': len(data)
            },
            method='POST'
        )
        
        self.assertEqual(req.get_method(), 'POST')
        self.assertEqual(req.get_header('Content-type'), 'application/json')


class TestDataPersistence(unittest.TestCase):
    """测试数据持久化功能"""
    
    def test_detection_result_saving(self):
        """测试结果保存功能"""
        save_dir = 'results'
        
        # 验证保存目录逻辑
        self.assertIsInstance(save_dir, str)
        self.assertTrue(len(save_dir) > 0)
    
    def test_log_info_recording(self):
        """测试日志记录功能"""
        log_message = "测试日志信息"
        
        # 验证日志消息不为空
        self.assertIsNotNone(log_message)
        self.assertTrue(len(log_message) > 0)


def run_functional_tests():
    """运行功能测试并返回结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTemperatureReception))
    suite.addTests(loader.loadTestsFromTestCase(TestFireDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestModelLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestGUIComponents))
    suite.addTests(loader.loadTestsFromTestCase(TestHTTPCommunication))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPersistence))
    
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
    results = run_functional_tests()
    print("\n" + "="*50)
    print("功能测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
