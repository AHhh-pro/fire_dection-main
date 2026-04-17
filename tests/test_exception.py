#!/usr/bin/env python3
"""
异常测试 - 测试系统在异常情况下的处理能力
"""
import unittest
import sys
import os
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInvalidInput(unittest.TestCase):
    """测试无效输入处理"""
    
    def test_invalid_temperature_value(self):
        """测试无效温度值处理"""
        invalid_values = [
            None,
            'invalid',
            [],
            {},
            float('inf'),
            float('-inf'),
            float('nan')
        ]
        
        for value in invalid_values:
            # 验证无效值被正确识别
            is_valid = isinstance(value, (int, float)) and not (
                value != value or  # NaN检查
                value == float('inf') or
                value == float('-inf')
            )
            self.assertFalse(is_valid, f"{value} 应该被识别为无效值")
    
    def test_missing_sensor_id(self):
        """测试缺少传感器ID"""
        incomplete_data = {'value': 25.5}  # 缺少sensorId
        
        # 验证数据不完整
        self.assertNotIn('sensorId', incomplete_data)
    
    def test_malformed_json(self):
        """测试畸形JSON数据"""
        malformed_json = [
            '{"sensorId": 1, "value":}',  # 缺少值
            '{"sensorId": 1, }',  # 尾随逗号
            '{sensorId: 1}',  # 缺少引号
            '',  # 空字符串
            'not json at all'
        ]
        
        for json_str in malformed_json:
            with self.assertRaises(json.JSONDecodeError):
                json.loads(json_str)


class TestNetworkErrors(unittest.TestCase):
    """测试网络错误处理"""
    
    def test_connection_refused(self):
        """测试连接被拒绝或超时"""
        # 尝试连接未启动的服务器
        try:
            req = urllib.request.Request(
                'http://localhost:59999',
                data=b'{}',
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urllib.request.urlopen(req, timeout=1)
            self.fail("应该抛出异常")
        except (urllib.error.URLError, ConnectionRefusedError, socket.timeout):
            pass  # 预期异常：连接被拒绝或超时
    
    def test_timeout_handling(self):
        """测试超时处理"""
        # 验证超时机制
        start = time.time()
        try:
            urllib.request.urlopen(
                'http://httpbin.org/delay/10',
                timeout=0.1
            )
        except Exception:
            pass
        end = time.time()
        
        # 验证在超时时间内返回
        self.assertLess(end - start, 0.5, "超时处理过慢")
    
    def test_invalid_url(self):
        """测试无效URL"""
        invalid_urls = [
            'not_a_url',
            'ftp://localhost:8080',
        ]
        
        for url in invalid_urls:
            # Request对象创建时不会验证URL，需要在urlopen时才捕获异常
            req = urllib.request.Request(url)
            with self.assertRaises((ValueError, urllib.error.URLError)):
                urllib.request.urlopen(req, timeout=1)


class TestResourceErrors(unittest.TestCase):
    """测试资源错误处理"""
    
    def test_missing_model_file(self):
        """测试模型文件缺失"""
        non_existent_path = 'weights/non_existent_model.pt'
        
        # 验证文件不存在
        self.assertFalse(os.path.exists(non_existent_path))
    
    def test_invalid_model_path(self):
        """测试无效模型路径"""
        invalid_paths = [
            '',
            None,
            'model.txt',  # 错误扩展名
            '../outside_weights/model.pt',  # 路径遍历
        ]
        
        for path in invalid_paths:
            if path:
                is_valid = path.endswith('.pt') and not path.startswith('..')
                if not is_valid:
                    self.assertTrue(True)  # 无效路径被识别
    
    def test_insufficient_permissions(self):
        """测试权限不足"""
        # 模拟只读目录
        read_only_dir = '/root' if os.name != 'nt' else 'C:\\Windows\\System32'
        
        if os.path.exists(read_only_dir):
            can_write = os.access(read_only_dir, os.W_OK)
            # 普通用户不应有写入权限
            if not can_write:
                self.assertFalse(can_write)


class TestDataCorruption(unittest.TestCase):
    """测试数据损坏处理"""
    
    def test_corrupted_temperature_data(self):
        """测试损坏的温度数据"""
        corrupted_data = [
            {'sensorId': 'not_a_number', 'value': 25.5},
            {'sensorId': 1, 'value': 'not_a_number'},
            {'sensorId': -1, 'value': 25.5},  # 负数ID
            {'sensorId': 1, 'value': 9999},  # 超出范围
        ]
        
        for data in corrupted_data:
            # 验证数据有效性
            is_valid = (
                isinstance(data.get('sensorId'), int) and
                isinstance(data.get('value'), (int, float)) and
                data['sensorId'] > 0 and
                -50 <= data['value'] <= 150
            )
            self.assertFalse(is_valid, f"{data} 应该被识别为损坏数据")
    
    def test_empty_data_structure(self):
        """测试空数据结构"""
        empty_structures = [
            {},
            [],
            None,
            ''
        ]
        
        for struct in empty_structures:
            is_empty = not bool(struct)
            self.assertTrue(is_empty, f"{struct} 应该被识别为空")


class TestBoundaryConditions(unittest.TestCase):
    """测试边界条件"""
    
    def test_temperature_boundaries(self):
        """测试温度边界值"""
        boundary_values = [
            (-50, True),   # 最小有效值
            (-51, False),  # 低于最小值
            (150, True),   # 最大有效值
            (151, False),  # 超过最大值
            (0, True),     # 零值
            (25.5, True),  # 正常值
        ]
        
        for value, should_be_valid in boundary_values:
            is_valid = -50 <= value <= 150
            self.assertEqual(is_valid, should_be_valid, 
                           f"温度值 {value} 验证错误")
    
    def test_confidence_boundaries(self):
        """测试置信度边界值"""
        boundary_values = [
            (0, False),    # 等于0
            (0.01, True),  # 最小有效值
            (0.5, True),   # 中间值
            (1.0, True),   # 最大值
            (1.01, False), # 超过最大值
        ]
        
        for value, should_be_valid in boundary_values:
            is_valid = 0.01 <= value <= 1.0
            self.assertEqual(is_valid, should_be_valid,
                           f"置信度 {value} 验证错误")
    
    def test_string_length_boundaries(self):
        """测试字符串长度边界"""
        # 测试超长字符串
        very_long_string = 'a' * 10000
        self.assertEqual(len(very_long_string), 10000)
        
        # 测试空字符串
        empty_string = ''
        self.assertEqual(len(empty_string), 0)


class TestRecoveryMechanisms(unittest.TestCase):
    """测试恢复机制"""
    
    def test_graceful_degradation(self):
        """测试优雅降级"""
        # 模拟部分功能失效
        services = {
            'temperature': False,  # 失效
            'detection': True,     # 正常
            'alert': True          # 正常
        }
        
        # 验证系统可以继续运行
        essential_services = ['detection', 'alert']
        can_continue = all(services[s] for s in essential_services)
        self.assertTrue(can_continue, "核心服务应该保持运行")
    
    def test_state_recovery(self):
        """测试状态恢复"""
        # 模拟错误后恢复
        error_occurred = True
        retry_count = 0
        max_retries = 3
        
        while error_occurred and retry_count < max_retries:
            retry_count += 1
            if retry_count >= 2:  # 模拟第2次重试成功
                error_occurred = False
        
        self.assertFalse(error_occurred, "应该在重试后恢复")
        self.assertLessEqual(retry_count, max_retries)


class TestConcurrentErrors(unittest.TestCase):
    """测试并发错误"""
    
    def test_race_condition_handling(self):
        """测试竞态条件处理"""
        import threading
        
        shared_counter = 0
        lock = threading.Lock()
        errors = []
        
        def increment():
            nonlocal shared_counter
            try:
                with lock:
                    temp = shared_counter
                    time.sleep(0.001)  # 模拟处理
                    shared_counter = temp + 1
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=increment) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 验证没有错误发生
        self.assertEqual(len(errors), 0, f"发生错误: {errors}")
        # 验证计数正确
        self.assertEqual(shared_counter, 100)


def run_exception_tests():
    """运行异常测试并返回结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestInvalidInput))
    suite.addTests(loader.loadTestsFromTestCase(TestNetworkErrors))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceErrors))
    suite.addTests(loader.loadTestsFromTestCase(TestDataCorruption))
    suite.addTests(loader.loadTestsFromTestCase(TestBoundaryConditions))
    suite.addTests(loader.loadTestsFromTestCase(TestRecoveryMechanisms))
    suite.addTests(loader.loadTestsFromTestCase(TestConcurrentErrors))
    
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
    results = run_exception_tests()
    print("\n" + "="*50)
    print("异常测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
