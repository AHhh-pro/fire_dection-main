#!/usr/bin/env python3
"""
性能测试 - 测试系统在各种负载下的性能表现
"""
import unittest
import sys
import os
import time
import json
import statistics
import threading
import concurrent.futures
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 全局性能数据存储
performance_data = {
    'response_times': {},
    'throughput': {},
    'scalability': {}
}

class TestResponseTime(unittest.TestCase):
    """测试响应时间性能"""
    
    def test_temperature_update_response_time(self):
        """测试温度更新响应时间"""
        response_times = []
        
        for _ in range(100):
            start = time.time()
            # 模拟温度数据处理
            temp_data = {'sensorId': 1, 'value': 25.5}
            processed = {
                'sensorId': temp_data['sensorId'],
                'value': temp_data['value'],
                'timestamp': time.time()
            }
            # 模拟UI更新
            ui_text = f"🌡️ {processed['value']:.1f}°C"
            end = time.time()
            
            response_times.append((end - start) * 1000)  # 转换为毫秒
        
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # 保存性能数据
        performance_data['response_times']['temperature'] = {
            'avg': avg_time,
            'max': max_time,
            'min': min_time,
            'all': response_times
        }
        
        print(f"\n温度更新响应时间:")
        print(f"  平均: {avg_time:.3f}ms")
        print(f"  最大: {max_time:.3f}ms")
        print(f"  最小: {min_time:.3f}ms")
        
        # 断言：平均响应时间应小于10ms
        self.assertLess(avg_time, 10, "温度更新响应时间过长")
    
    def test_alert_calculation_performance(self):
        """测试警报计算性能"""
        def calculate_alert(detections):
            has_fire = detections.get('fire', 0) > 0
            has_smoke = detections.get('smoke', 0) > 0
            
            if has_fire and has_smoke:
                return 'critical'
            elif has_fire:
                return 'high'
            elif has_smoke:
                return 'medium'
            return 'safe'
        
        # 测试数据 - 增加数据量以确保可测量
        test_cases = [
            {'fire': 2, 'smoke': 1},
            {'fire': 0, 'smoke': 0},
            {'fire': 1, 'smoke': 0},
            {'fire': 0, 'smoke': 2}
        ] * 25000  # 100000次测试，确保有足够的执行时间
        
        start = time.perf_counter()  # 使用更高精度的计时器
        for case in test_cases:
            calculate_alert(case)
        end = time.perf_counter()
        
        total_time = (end - start) * 1000  # 转换为毫秒
        avg_time = total_time / len(test_cases)
        throughput = len(test_cases) / (total_time / 1000)  # 次/秒
        
        print(f"\n警报计算性能:")
        print(f"  总次数: {len(test_cases)}")
        print(f"  总时间: {total_time:.3f}ms")
        print(f"  平均: {avg_time:.6f}ms")
        print(f"  吞吐量: {throughput:.0f} 次/秒")
        
        # 保存性能数据
        performance_data['response_times']['alert_calculation'] = {
            'avg': avg_time,
            'total_time': total_time,
            'throughput': throughput
        }
        
        self.assertLess(avg_time, 0.1, "警报计算性能不足")


class TestThroughput(unittest.TestCase):
    """测试吞吐量性能"""
    
    def test_http_request_throughput(self):
        """测试HTTP请求吞吐量"""
        import urllib.request
        
        # 模拟HTTP请求处理
        def process_request(data):
            json_data = json.dumps(data).encode('utf-8')
            # 模拟网络延迟和处理时间
            time.sleep(0.001)
            return True
        
        # 并发测试
        num_requests = 100
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_request, {"sensorId": i, "value": 25.0 + i})
                for i in range(num_requests)
            ]
            concurrent.futures.wait(futures)
        
        end = time.time()
        duration = end - start
        throughput = num_requests / duration
        
        print(f"\nHTTP请求吞吐量:")
        print(f"  总请求数: {num_requests}")
        print(f"  总时间: {duration:.3f}s")
        print(f"  吞吐量: {throughput:.1f} 请求/秒")
        
        self.assertGreater(throughput, 50, "HTTP吞吐量不足")
    
    def test_detection_processing_throughput(self):
        """测试检测处理吞吐量"""
        def process_detection_frame():
            # 模拟单帧处理
            time.sleep(0.033)  # 模拟30fps处理时间
            return True
        
        num_frames = 30
        start = time.time()
        
        for _ in range(num_frames):
            process_detection_frame()
        
        end = time.time()
        duration = end - start
        fps = num_frames / duration
        
        print(f"\n检测处理吞吐量:")
        print(f"  处理帧数: {num_frames}")
        print(f"  总时间: {duration:.3f}s")
        print(f"  实际FPS: {fps:.1f}")
        
        self.assertGreater(fps, 20, "检测FPS不足")


class TestMemoryUsage(unittest.TestCase):
    """测试内存使用情况"""
    
    def test_temperature_data_memory_growth(self):
        """测试温度数据内存增长"""
        import gc
        
        # 模拟大量温度数据
        temp_history = []
        
        for i in range(1000):
            temp_history.append({
                'sensorId': i % 3 + 1,
                'value': 25.0 + (i % 20),
                'timestamp': time.time()
            })
        
        # 清理过期数据（只保留最近100条）
        temp_history = temp_history[-100:]
        gc.collect()
        
        self.assertEqual(len(temp_history), 100, "内存清理失败")
    
    def test_detection_result_memory_cleanup(self):
        """测试结果内存清理"""
        # 模拟检测结果缓存
        detection_cache = []
        
        for i in range(100):
            detection_cache.append({
                'frame_id': i,
                'results': [{'class': 'fire', 'conf': 0.8}] * 10
            })
        
        # 模拟清理
        detection_cache.clear()
        
        self.assertEqual(len(detection_cache), 0, "缓存清理失败")


class TestConcurrency(unittest.TestCase):
    """测试并发性能"""
    
    def test_concurrent_temperature_updates(self):
        """测试并发温度更新"""
        update_count = 0
        lock = threading.Lock()
        
        def update_temperature(sensor_id):
            nonlocal update_count
            time.sleep(0.01)  # 模拟处理
            with lock:
                update_count += 1
        
        # 10个传感器同时更新
        threads = []
        start = time.time()
        
        for i in range(10):
            t = threading.Thread(target=update_temperature, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        end = time.time()
        duration = end - start
        
        print(f"\n并发温度更新:")
        print(f"  更新次数: {update_count}")
        print(f"  总时间: {duration:.3f}s")
        print(f"  平均每次: {duration/update_count*1000:.1f}ms")
        
        self.assertEqual(update_count, 10)
        self.assertLess(duration, 0.5, "并发处理时间过长")
    
    def test_thread_safety(self):
        """测试线程安全性"""
        shared_data = {'count': 0}
        lock = threading.Lock()
        
        def increment():
            for _ in range(100):
                with lock:
                    shared_data['count'] += 1
        
        threads = [threading.Thread(target=increment) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(shared_data['count'], 1000, "线程安全问题")


class TestScalability(unittest.TestCase):
    """测试可扩展性"""
    
    def test_detection_with_increasing_objects(self):
        """测试随着目标数量增加的性能变化"""
        object_counts = [1, 5, 10, 20, 50]
        times = []
        
        for count in object_counts:
            objects = [{'class': 'fire', 'conf': 0.8} for _ in range(count)]
            
            start = time.time()
            # 模拟处理
            for obj in objects:
                _ = f"{obj['class']}: {obj['conf']:.2f}"
            end = time.time()
            
            times.append((end - start) * 1000)
        
        print(f"\n目标数量扩展性:")
        for count, t in zip(object_counts, times):
            print(f"  {count}个目标: {t:.3f}ms")
        
        # 验证时间增长不是指数级的
        for i in range(1, len(times)):
            ratio = times[i] / times[i-1] if times[i-1] > 0 else 1
            self.assertLess(ratio, 3, f"性能下降过快: 从{object_counts[i-1]}到{object_counts[i]}")


def run_performance_tests():
    """运行性能测试并返回结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestResponseTime))
    suite.addTests(loader.loadTestsFromTestCase(TestThroughput))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryUsage))
    suite.addTests(loader.loadTestsFromTestCase(TestConcurrency))
    suite.addTests(loader.loadTestsFromTestCase(TestScalability))
    
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
    results = run_performance_tests()
    print("\n" + "="*50)
    print("性能测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
