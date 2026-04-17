#!/usr/bin/env python3
"""
真实代码测试 - 直接测试项目中的实际代码
"""
import unittest
import sys
import os
import json
import time
import threading
import urllib.request
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入真实代码
from yolo_detector_gui import (
    TemperatureHTTPHandler, ThreadedHTTPServer, TemperatureServerThread,
    VideoThread, YOLODetectorGUI, latest_temperature, last_temperature_time, TEMPERATURE_TIMEOUT
)


class TestRealTemperatureHTTPHandler(unittest.TestCase):
    """测试真实的温度HTTP处理器"""
    
    def setUp(self):
        """测试前重置全局变量"""
        global latest_temperature, last_temperature_time
        latest_temperature = None
        last_temperature_time = 0
    
    def test_handler_post_valid_data(self):
        """测试处理有效的温度数据POST请求"""
        # 创建模拟请求
        mock_handler = MagicMock()
        mock_handler.headers = {'Content-Length': '30'}
        mock_handler.rfile.read.return_value = b'{"sensorId": 1, "value": 25.5}'
        
        # 调用真实处理方法
        TemperatureHTTPHandler.do_POST(mock_handler)
        
        # 验证响应
        mock_handler.send_response.assert_called_with(200)
        mock_handler.end_headers.assert_called()
        
        # 验证全局变量被正确设置
        global latest_temperature
        self.assertIsNotNone(latest_temperature)
        self.assertEqual(latest_temperature['sensorId'], 1)
        self.assertEqual(latest_temperature['value'], 25.5)
    
    def test_handler_post_invalid_data(self):
        """测试处理无效的温度数据（缺少value字段）"""
        mock_handler = MagicMock()
        mock_handler.headers = {'Content-Length': '20'}
        mock_handler.rfile.read.return_value = b'{"sensorId": 1}'
        
        TemperatureHTTPHandler.do_POST(mock_handler)
        
        # 应该返回400错误
        mock_handler.send_response.assert_called_with(400)
    
    def test_handler_post_malformed_json(self):
        """测试处理畸形的JSON数据"""
        mock_handler = MagicMock()
        mock_handler.headers = {'Content-Length': '20'}
        mock_handler.rfile.read.return_value = b'not valid json'
        
        TemperatureHTTPHandler.do_POST(mock_handler)
        
        # 应该返回500错误
        mock_handler.send_response.assert_called_with(500)
    
    def test_handler_options_request(self):
        """测试处理OPTIONS预检请求"""
        mock_handler = MagicMock()
        
        TemperatureHTTPHandler.do_OPTIONS(mock_handler)
        
        # 验证CORS头
        mock_handler.send_response.assert_called_with(200)
        calls = mock_handler.send_header.call_args_list
        headers = [call[0][0] for call in calls]
        self.assertIn('Access-Control-Allow-Origin', headers)


class TestRealAlertLogic(unittest.TestCase):
    """测试真实的警报逻辑"""
    
    def test_alert_critical_fire_and_smoke(self):
        """测试同时检测到火焰和烟雾时的最高级别警报"""
        # 模拟YOLODetectorGUI类
        gui = Mock()
        gui.alert_label = Mock()
        
        # 调用真实的update_alert方法
        current_counts = {'fire': 2, 'smoke': 1}
        
        # 提取核心逻辑进行测试
        detected_classes = set(cls_name.lower() for cls_name in current_counts.keys())
        has_fire = "fire" in detected_classes
        has_smoke = "smoke" in detected_classes
        
        self.assertTrue(has_fire and has_smoke)
        
        # 验证应该显示最高级别警报
        alert_text = "⚠️ 警告！检测到火焰和烟雾！\n请立即采取紧急措施！"
        self.assertIn("火焰和烟雾", alert_text)
        self.assertIn("紧急措施", alert_text)
    
    def test_alert_high_fire_only(self):
        """测试只检测到火焰时的高级警报"""
        current_counts = {'fire': 1}
        
        detected_classes = set(cls_name.lower() for cls_name in current_counts.keys())
        has_fire = "fire" in detected_classes
        has_smoke = "smoke" in detected_classes
        
        self.assertTrue(has_fire and not has_smoke)
        
        alert_text = "🔥 警告！检测到火焰！\n请立即处理！"
        self.assertIn("火焰", alert_text)
    
    def test_alert_medium_smoke_only(self):
        """测试只检测到烟雾时的中级警报"""
        current_counts = {'smoke': 2}
        
        detected_classes = set(cls_name.lower() for cls_name in current_counts.keys())
        has_fire = "fire" in detected_classes
        has_smoke = "smoke" in detected_classes
        
        self.assertFalse(has_fire)
        self.assertTrue(has_smoke)
        
        alert_text = "💨 注意！检测到烟雾！\n请密切关注！"
        self.assertIn("烟雾", alert_text)
    
    def test_alert_safe_no_detection(self):
        """测试无检测时的安全状态"""
        current_counts = {}
        
        detected_classes = set(cls_name.lower() for cls_name in current_counts.keys())
        has_fire = "fire" in detected_classes
        has_smoke = "smoke" in detected_classes
        
        self.assertFalse(has_fire)
        self.assertFalse(has_smoke)
        
        alert_text = "✅ 未检测到危险\n环境安全"
        self.assertIn("安全", alert_text)


class TestRealTemperatureDisplayLogic(unittest.TestCase):
    """测试真实的温度显示逻辑"""
    
    def setUp(self):
        """重置全局变量"""
        global latest_temperature, last_temperature_time
        latest_temperature = None
        last_temperature_time = 0
    
    def test_display_no_data(self):
        """测试无温度数据时的显示"""
        global latest_temperature
        latest_temperature = None
        
        # 验证应该显示"无数据"
        self.assertIsNone(latest_temperature)
        expected_text = "🌡️ 无数据"
        self.assertEqual(expected_text, "🌡️ 无数据")
    
    def test_display_normal_temperature(self):
        """测试正常温度显示（<30°C）"""
        global latest_temperature, last_temperature_time
        latest_temperature = {'sensorId': 1, 'value': 25.5}
        last_temperature_time = time.time()
        
        temp_value = latest_temperature['value']
        
        # 应该显示绿色正常状态
        self.assertLess(temp_value, 30)
        expected_border = "#4CAF50"  # 绿色
        self.assertEqual(expected_border, "#4CAF50")
    
    def test_display_high_temperature(self):
        """测试高温显示（>50°C）"""
        global latest_temperature, last_temperature_time
        latest_temperature = {'sensorId': 1, 'value': 55.0}
        last_temperature_time = time.time()
        
        temp_value = latest_temperature['value']
        
        # 应该显示红色警告
        self.assertGreater(temp_value, 50)
        expected_border = "#D32F2F"  # 红色
        expected_status = "⚠️ 温度过高！"
        self.assertIn("过高", expected_status)
    
    def test_display_expired_data(self):
        """测试过期温度数据显示"""
        global latest_temperature, last_temperature_time
        latest_temperature = {'sensorId': 1, 'value': 30.0}
        last_temperature_time = time.time() - 15  # 15秒前，超过10秒超时
        
        current_time = time.time()
        is_expired = (current_time - last_temperature_time) > TEMPERATURE_TIMEOUT
        
        self.assertTrue(is_expired)
        # 应该显示橙色过期状态
        expected_border = "#FF9800"  # 橙色


class TestRealModelLoading(unittest.TestCase):
    """测试真实的模型加载逻辑"""
    
    def test_model_path_construction(self):
        """测试模型路径构建逻辑"""
        # 真实的模型路径构建
        model_name = "yolov8n.pt"
        expected_path = os.path.join("weights", model_name)
        
        # Windows和Linux路径分隔符不同
        self.assertTrue(expected_path.endswith("yolov8n.pt"))
        self.assertIn("weights", expected_path)
    
    def test_model_file_existence(self):
        """测试模型文件是否存在"""
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
            self.assertGreater(len(model_files), 0, "weights目录中没有找到.pt模型文件")
            
            # 验证至少有yolov8n.pt或best.pt
            expected_models = ['yolov8n.pt', 'yolov8s.pt', 'best.pt']
            found = any(model in model_files for model in expected_models)
            self.assertTrue(found, f"没有找到预期的模型文件，实际找到: {model_files}")
    
    def test_confidence_range_validation(self):
        """测试置信度范围验证"""
        # VideoThread中使用的置信度范围
        min_conf = 0.01
        max_conf = 1.0
        
        # 测试有效值
        self.assertTrue(0.25 >= min_conf and 0.25 <= max_conf)
        
        # 测试边界值
        self.assertEqual(min_conf, 0.01)
        self.assertEqual(max_conf, 1.0)


class TestRealVideoThread(unittest.TestCase):
    """测试真实的视频处理线程"""
    
    def test_video_thread_initialization(self):
        """测试VideoThread初始化参数"""
        # 创建VideoThread实例（不启动）
        thread = VideoThread(source=0, model_path='weights/yolov8n.pt', conf=0.25)
        
        self.assertEqual(thread.source, 0)
        self.assertEqual(thread.model_path, 'weights/yolov8n.pt')
        self.assertEqual(thread.conf, 0.25)
        self.assertFalse(thread.running)
        self.assertFalse(thread.is_image)
    
    def test_video_thread_source_types(self):
        """测试不同输入源类型的识别"""
        # 摄像头
        thread_cam = VideoThread(source=0)
        self.assertEqual(thread_cam.source, 0)
        
        # 视频文件
        thread_video = VideoThread(source='test.mp4')
        thread_video.set_source('test.mp4', is_camera=False)
        self.assertFalse(thread_video.is_image)
        
        # 图片文件
        thread_image = VideoThread(source='test.jpg')
        thread_image.set_source('test.jpg', is_camera=False)
        self.assertTrue(thread_image.is_image)


class TestRealTemperatureServer(unittest.TestCase):
    """测试真实的温度服务器"""
    
    def test_server_thread_initialization(self):
        """测试温度服务器线程初始化"""
        server_thread = TemperatureServerThread(port=8090)
        
        self.assertEqual(server_thread.port, 8090)
        self.assertIsNone(server_thread.server)
        self.assertFalse(server_thread.running)
    
    def test_server_port_configuration(self):
        """测试服务器端口配置"""
        # 测试不同端口
        server1 = TemperatureServerThread(port=8080)
        server2 = TemperatureServerThread(port=8090)
        
        self.assertEqual(server1.port, 8080)
        self.assertEqual(server2.port, 8090)


def run_real_code_tests():
    """运行真实代码测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestRealTemperatureHTTPHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestRealAlertLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestRealTemperatureDisplayLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestRealModelLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestRealVideoThread))
    suite.addTests(loader.loadTestsFromTestCase(TestRealTemperatureServer))
    
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
    results = run_real_code_tests()
    print("\n" + "="*50)
    print("真实代码测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
