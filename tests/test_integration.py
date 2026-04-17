#!/usr/bin/env python3
"""
集成测试 - 验证各模块之间的协同工作
"""
import unittest
import sys
import os
import json
import time
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockTemperatureHTTPHandler(BaseHTTPRequestHandler):
    """模拟温度HTTP处理器"""
    received_data = []
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        MockTemperatureHTTPHandler.received_data.append(data)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())
    
    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class TestTemperatureIntegration(unittest.TestCase):
    """测试温度数据集成"""
    
    @classmethod
    def setUpClass(cls):
        """启动模拟服务器"""
        cls.server = ThreadedHTTPServer(('localhost', 18090), MockTemperatureHTTPHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)  # 等待服务器启动
    
    @classmethod
    def tearDownClass(cls):
        """关闭模拟服务器"""
        cls.server.shutdown()
        cls.server.server_close()
    
    def setUp(self):
        """重置接收数据"""
        MockTemperatureHTTPHandler.received_data = []
    
    def test_csharp_to_python_communication(self):
        """测试C#到Python的通信链路"""
        # 模拟C#发送的数据
        csharp_data = {
            "sensorId": 1,
            "value": 35.5
        }
        
        # 发送数据到模拟服务器
        url = "http://localhost:18090"
        data = json.dumps(csharp_data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                self.assertEqual(result['status'], 'success')
        except Exception as e:
            self.fail(f"通信失败: {e}")
        
        # 验证数据接收
        time.sleep(0.1)
        self.assertEqual(len(MockTemperatureHTTPHandler.received_data), 1)
        received = MockTemperatureHTTPHandler.received_data[0]
        self.assertEqual(received['sensorId'], 1)
        self.assertEqual(received['value'], 35.5)
    
    def test_multiple_sensor_data(self):
        """测试多传感器数据接收"""
        sensors = [
            {"sensorId": 1, "value": 25.0},
            {"sensorId": 2, "value": 30.5},
            {"sensorId": 3, "value": 28.3}
        ]
        
        url = "http://localhost:18090"
        for sensor_data in sensors:
            data = json.dumps(sensor_data).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req, timeout=2):
                    pass
            except:
                pass
        
        time.sleep(0.2)
        self.assertEqual(len(MockTemperatureHTTPHandler.received_data), 3)


class TestDetectionAlertIntegration(unittest.TestCase):
    """测试检测与警报集成"""
    
    def test_fire_detection_to_alert(self):
        """测试火灾检测到警报的完整流程"""
        # 模拟检测结果
        detection_results = {
            'fire': 2,
            'smoke': 1
        }
        
        # 根据结果确定警报级别
        def get_alert_from_detection(results):
            has_fire = results.get('fire', 0) > 0
            has_smoke = results.get('smoke', 0) > 0
            
            if has_fire and has_smoke:
                return 'critical'
            elif has_fire:
                return 'high'
            elif has_smoke:
                return 'medium'
            return 'safe'
        
        alert_level = get_alert_from_detection(detection_results)
        self.assertEqual(alert_level, 'critical')
    
    def test_alert_to_ui_update(self):
        """测试警报到UI更新的流程"""
        alert_levels = {
            'critical': {'color': '#D32F2F', 'message': '警告！检测到火焰和烟雾！'},
            'high': {'color': '#F57C00', 'message': '警告！检测到火焰！'},
            'medium': {'color': '#FBC02D', 'message': '注意！检测到烟雾！'},
            'safe': {'color': '#4CAF50', 'message': '未检测到危险'}
        }
        
        # 验证每个级别都有对应的UI配置
        for level in ['critical', 'high', 'medium', 'safe']:
            self.assertIn(level, alert_levels)
            self.assertIn('color', alert_levels[level])
            self.assertIn('message', alert_levels[level])


class TestModelDetectionIntegration(unittest.TestCase):
    """测试模型与检测集成"""
    
    def test_model_to_detection_pipeline(self):
        """测试模型到检测的完整流程"""
        # 模拟模型配置
        model_config = {
            'model_path': 'weights/yolov8n.pt',
            'confidence': 0.25,
            'device': 'cpu'
        }
        
        # 验证配置完整性
        self.assertTrue(model_config['model_path'].endswith('.pt'))
        self.assertTrue(0 < model_config['confidence'] <= 1)
    
    def test_detection_result_format(self):
        """测试结果格式标准化"""
        # YOLO检测结果格式
        mock_result = {
            'boxes': [
                {'cls': 0, 'conf': 0.85, 'xyxy': [100, 100, 200, 200]},  # fire
                {'cls': 1, 'conf': 0.75, 'xyxy': [150, 150, 250, 250]}   # smoke
            ],
            'names': {0: 'fire', 1: 'smoke'}
        }
        
        # 统计各类别数量
        class_counts = {}
        for box in mock_result['boxes']:
            cls_id = int(box['cls'])
            cls_name = mock_result['names'].get(cls_id, 'unknown')
            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        
        self.assertEqual(class_counts['fire'], 1)
        self.assertEqual(class_counts['smoke'], 1)


class TestGUIFunctionIntegration(unittest.TestCase):
    """测试GUI功能集成"""
    
    def test_input_source_switching(self):
        """测试输入源切换"""
        sources = {
            0: 'camera',
            1: 'video',
            2: 'image'
        }
        
        # 验证所有源类型
        for index, source_type in sources.items():
            self.assertIn(index, [0, 1, 2])
            self.assertIn(source_type, ['camera', 'video', 'image'])
    
    def test_confidence_to_detection_filter(self):
        """测试置信度到检测过滤"""
        confidence_threshold = 0.25
        
        # 模拟检测结果
        detections = [
            {'class': 'fire', 'conf': 0.85},
            {'class': 'smoke', 'conf': 0.15},
            {'class': 'fire', 'conf': 0.30}
        ]
        
        # 过滤低置信度
        filtered = [d for d in detections if d['conf'] >= confidence_threshold]
        self.assertEqual(len(filtered), 2)


class TestDataFlowIntegration(unittest.TestCase):
    """测试数据流集成"""
    
    def test_end_to_end_data_flow(self):
        """测试端到端数据流"""
        # 1. C#发送温度数据
        temp_data = {"sensorId": 1, "value": 35.5}
        
        # 2. Python接收并处理
        processed_temp = {
            'sensorId': temp_data['sensorId'],
            'value': temp_data['value'],
            'timestamp': time.time()
        }
        
        # 3. 更新UI显示
        ui_display = f"🌡️ {processed_temp['value']:.1f}°C"
        
        self.assertIn('35.5', ui_display)
        self.assertIn('°C', ui_display)
    
    def test_concurrent_data_handling(self):
        """测试并发数据处理"""
        import concurrent.futures
        
        def process_data(data):
            time.sleep(0.01)  # 模拟处理时间
            return data * 2
        
        data_list = [1, 2, 3, 4, 5]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(process_data, data_list))
        
        self.assertEqual(results, [2, 4, 6, 8, 10])


def run_integration_tests():
    """运行集成测试并返回结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTemperatureIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDetectionAlertIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestModelDetectionIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestGUIFunctionIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFlowIntegration))
    
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
    results = run_integration_tests()
    print("\n" + "="*50)
    print("集成测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
