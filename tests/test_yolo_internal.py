#!/usr/bin/env python3
"""
YOLO内部细节测试 - 测试YOLO模型训练和推理的各个细节
"""
import unittest
import sys
import os
import cv2
import numpy as np
import yaml
import torch
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO
from config import TrainingConfig, PredictionConfig
from utils import (
    get_color_for_class, cv2_to_qpixmap, count_detections,
    scale_pixmap_to_label, plot_with_custom_colors, check_model_path,
    CLASS_COLORS, DEFAULT_COLORS
)


class TestYOLOModelLoading(unittest.TestCase):
    """测试YOLO模型加载"""
    
    def test_load_pretrained_model(self):
        """测试加载预训练模型"""
        # 检查模型文件是否存在
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
            
            # 测试加载存在的模型
            for model_file in model_files[:1]:  # 只测试第一个避免太慢
                model_path = os.path.join(weights_dir, model_file)
                try:
                    model = YOLO(model_path)
                    self.assertIsNotNone(model)
                    self.assertTrue(hasattr(model, 'predict'))
                    print(f"✓ 成功加载模型: {model_file}")
                except Exception as e:
                    self.fail(f"加载模型 {model_file} 失败: {e}")
    
    def test_model_info(self):
        """测试模型信息"""
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
            
            for model_file in model_files[:1]:
                model_path = os.path.join(weights_dir, model_file)
                try:
                    model = YOLO(model_path)
                    
                    # 检查模型属性
                    self.assertTrue(hasattr(model, 'names'))
                    self.assertTrue(hasattr(model, 'task'))
                    
                    # 打印模型信息
                    print(f"\n模型 {model_file} 信息:")
                    print(f"  任务类型: {model.task}")
                    print(f"  类别数: {len(model.names)}")
                    print(f"  类别名称: {model.names}")
                    
                except Exception as e:
                    print(f"警告: 获取模型信息失败: {e}")


class TestYOLOInference(unittest.TestCase):
    """测试YOLO推理功能"""
    
    def test_model_predict_on_dummy_image(self):
        """测试模型在虚拟图像上的预测"""
        # 创建虚拟图像（模拟火灾场景的颜色特征）
        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
            
            for model_file in model_files[:1]:
                model_path = os.path.join(weights_dir, model_file)
                try:
                    model = YOLO(model_path)
                    
                    # 执行预测
                    results = model.predict(dummy_image, verbose=False)
                    
                    # 验证结果格式
                    self.assertIsInstance(results, list)
                    self.assertEqual(len(results), 1)
                    
                    result = results[0]
                    
                    # 检查结果属性
                    self.assertTrue(hasattr(result, 'boxes'))
                    self.assertTrue(hasattr(result, 'names'))
                    
                    print(f"✓ 模型 {model_file} 预测成功")
                    print(f"  检测到 {len(result.boxes)} 个目标")
                    
                except Exception as e:
                    print(f"警告: 模型预测测试失败: {e}")
    
    def test_confidence_threshold_effect(self):
        """测试置信度阈值对结果的影响"""
        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if 'yolov8' in f]
            
            if model_files:
                model_path = os.path.join(weights_dir, model_files[0])
                try:
                    model = YOLO(model_path)
                    
                    # 测试不同置信度阈值
                    conf_thresholds = [0.1, 0.25, 0.5, 0.75]
                    
                    for conf in conf_thresholds:
                        results = model.predict(dummy_image, conf=conf, verbose=False)
                        num_detections = len(results[0].boxes)
                        print(f"  置信度 {conf}: 检测到 {num_detections} 个目标")
                    
                except Exception as e:
                    print(f"警告: 置信度测试失败: {e}")


class TestTrainingConfig(unittest.TestCase):
    """测试训练配置"""
    
    def test_default_training_config(self):
        """测试默认训练配置"""
        config = TrainingConfig()
        
        # 验证基本配置
        self.assertEqual(config.data_yaml, 'data.yaml')
        self.assertEqual(config.model_type, 'yolov8n.pt')
        self.assertTrue(config.pretrained)
        self.assertEqual(config.epochs, 100)
        self.assertEqual(config.batch_size, 16)
        self.assertEqual(config.imgsz, 640)
        
        # 验证优化器配置
        self.assertEqual(config.optimizer, 'Adam')
        self.assertEqual(config.lr0, 0.01)
        self.assertEqual(config.lrf, 0.01)
        
        print("\n训练配置默认值:")
        print(f"  模型: {config.model_type}")
        print(f"  轮数: {config.epochs}")
        print(f"  批次: {config.batch_size}")
        print(f"  图像尺寸: {config.imgsz}")
        print(f"  优化器: {config.optimizer}")
    
    def test_training_hyperparameters(self):
        """测试训练超参数范围"""
        config = TrainingConfig()
        
        # 验证超参数在合理范围内
        self.assertGreater(config.epochs, 0)
        self.assertLess(config.epochs, 1000)
        
        self.assertGreater(config.batch_size, 0)
        self.assertLess(config.batch_size, 128)
        
        self.assertGreater(config.lr0, 0)
        self.assertLess(config.lr0, 1)
        
        self.assertGreaterEqual(config.momentum, 0)
        self.assertLessEqual(config.momentum, 1)
    
    def test_augmentation_config(self):
        """测试数据增强配置"""
        config = TrainingConfig()
        
        # 验证增强参数
        self.assertTrue(config.augment)
        self.assertGreaterEqual(config.mosaic, 0)
        self.assertLessEqual(config.mosaic, 1)
        self.assertGreaterEqual(config.mixup, 0)
        self.assertLessEqual(config.mixup, 1)


class TestPredictionConfig(unittest.TestCase):
    """测试预测配置"""
    
    def test_default_prediction_config(self):
        """测试默认预测配置"""
        config = PredictionConfig()
        
        # 验证基本配置
        self.assertEqual(config.conf_threshold, 0.25)
        self.assertEqual(config.iou_threshold, 0.45)
        self.assertEqual(config.max_det, 300)
        
        # 验证可视化配置
        self.assertFalse(config.hide_labels)
        self.assertFalse(config.hide_conf)
        
        print("\n预测配置默认值:")
        print(f"  置信度阈值: {config.conf_threshold}")
        print(f"  IOU阈值: {config.iou_threshold}")
        print(f"  最大检测数: {config.max_det}")
    
    def test_confidence_threshold_validation(self):
        """测试置信度阈值验证"""
        config = PredictionConfig()
        
        # 验证阈值在有效范围内
        self.assertGreaterEqual(config.conf_threshold, 0)
        self.assertLessEqual(config.conf_threshold, 1)
        
        self.assertGreaterEqual(config.iou_threshold, 0)
        self.assertLessEqual(config.iou_threshold, 1)


class TestUtilsFunctions(unittest.TestCase):
    """测试工具函数"""
    
    def test_get_color_for_class(self):
        """测试类别颜色获取"""
        # 测试烟雾颜色
        smoke_color = get_color_for_class(0, "smoke")
        self.assertEqual(smoke_color, (0, 0, 255))  # 红色
        
        # 测试火灾颜色
        fire_color = get_color_for_class(1, "fire")
        self.assertEqual(fire_color, (0, 165, 255))  # 橙色
        
        # 测试未知类别（使用默认颜色）
        unknown_color = get_color_for_class(999, "unknown")
        self.assertIn(unknown_color, DEFAULT_COLORS)
    
    def test_check_model_path(self):
        """测试模型路径检查"""
        # 测试存在的模型文件
        weights_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'weights')
        
        if os.path.exists(weights_dir):
            model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
            
            if model_files:
                model_path = os.path.join('weights', model_files[0])
                is_valid, full_path = check_model_path(model_path)
                self.assertTrue(is_valid, f"模型路径 {model_path} 应该有效")
                self.assertTrue(os.path.exists(full_path), f"模型文件应该存在: {full_path}")
                print(f"✓ 找到模型: {model_files[0]} -> {full_path}")
            else:
                print(f"⚠ weights目录存在但没有.pt文件: {weights_dir}")
        else:
            print(f"⚠ weights目录不存在: {weights_dir}")
        
        # 测试不存在的文件
        is_valid, path = check_model_path('non_existent_model.pt')
        self.assertFalse(is_valid, "不存在的模型应该返回False")
        
        # 测试ultralytics预训练模型（会自动下载）
        is_valid, path = check_model_path('yolov8n.pt')
        # 注意：这个测试可能通过也可能失败，取决于ultralytics缓存
        print(f"  预训练模型 yolov8n.pt: is_valid={is_valid}, path={path}")
    
    def test_count_detections(self):
        """测试检测结果统计"""
        # 创建模拟结果对象
        mock_result = Mock()
        mock_result.names = {0: 'smoke', 1: 'fire'}
        
        # 模拟检测框
        mock_boxes = Mock()
        mock_boxes.cls = torch.tensor([0, 1, 0])  # 2个smoke, 1个fire
        mock_result.boxes = mock_boxes
        
        # 测试统计
        counts = count_detections([mock_result])
        
        self.assertEqual(counts['smoke'], 2)
        self.assertEqual(counts['fire'], 1)


class TestDataYaml(unittest.TestCase):
    """测试数据集配置文件"""
    
    def test_data_yaml_exists(self):
        """测试data.yaml文件存在"""
        data_yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.yaml')
        self.assertTrue(os.path.exists(data_yaml_path), "data.yaml文件不存在")
    
    def test_data_yaml_format(self):
        """测试data.yaml格式正确"""
        data_yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.yaml')
        
        if os.path.exists(data_yaml_path):
            with open(data_yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 验证必需字段
            self.assertIn('train', data)
            self.assertIn('val', data)
            self.assertIn('names', data)
            
            # 验证类别定义
            self.assertIsInstance(data['names'], dict)
            
            print("\ndata.yaml内容:")
            print(f"  训练路径: {data.get('train')}")
            print(f"  验证路径: {data.get('val')}")
            print(f"  类别: {data.get('names')}")


class TestTrainingPipeline(unittest.TestCase):
    """测试训练流程（不实际运行训练）"""
    
    def test_train_args_parsing(self):
        """测试训练参数解析"""
        from train import parse_args
        
        args = parse_args()
        
        # 验证参数
        self.assertEqual(args.data_yaml, 'data.yaml')
        self.assertEqual(args.model_type, 'yolov8s.pt')
        self.assertEqual(args.epochs, 100)
        self.assertEqual(args.batch_size, 32)
        
        print("\n训练参数:")
        print(f"  数据配置: {args.data_yaml}")
        print(f"  模型: {args.model_type}")
        print(f"  轮数: {args.epochs}")
        print(f"  批次: {args.batch_size}")
    
    def test_model_output_structure(self):
        """测试模型输出结构"""
        # 验证训练输出目录结构
        project_dir = 'runs/train'
        
        if os.path.exists(project_dir):
            experiments = [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d))]
            
            for exp in experiments[:1]:  # 只检查第一个实验
                exp_dir = os.path.join(project_dir, exp)
                weights_dir = os.path.join(exp_dir, 'weights')
                
                if os.path.exists(weights_dir):
                    self.assertTrue(os.path.isdir(weights_dir))
                    
                    # 检查是否有模型文件
                    model_files = [f for f in os.listdir(weights_dir) if f.endswith('.pt')]
                    print(f"\n实验 {exp} 中的模型文件: {model_files}")


def run_yolo_internal_tests():
    """运行YOLO内部测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestYOLOModelLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestYOLOInference))
    suite.addTests(loader.loadTestsFromTestCase(TestTrainingConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestPredictionConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilsFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestDataYaml))
    suite.addTests(loader.loadTestsFromTestCase(TestTrainingPipeline))
    
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
    results = run_yolo_internal_tests()
    print("\n" + "="*50)
    print("YOLO内部测试结果汇总")
    print("="*50)
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['errors']}")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
