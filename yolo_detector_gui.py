import sys
import os
import cv2
import numpy as np
import json
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QComboBox, QSlider, QFileDialog, 
                           QStatusBar, QMenuBar, QAction, QTabWidget, QFrame, 
                           QSplitter, QGroupBox, QFormLayout, QMessageBox, QTextEdit,
                           QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QColor, QPalette
from ultralytics import YOLO
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import time

# 导入自定义工具函数
import utils

# 导入数据库相关
from database import get_alert_repository
from auth_manager import get_auth_manager

# 全局变量存储最新温度数据
latest_temperature = None
last_temperature_time = 0
TEMPERATURE_TIMEOUT = 10  # 温度数据超时时间（秒）

class TemperatureHTTPHandler(BaseHTTPRequestHandler):
    """处理温度数据HTTP请求"""
    
    def do_POST(self):
        """处理POST请求"""
        global latest_temperature, last_temperature_time
        
        try:
            # 获取Content-Length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            
            # 解析JSON数据
            temperature_data = json.loads(post_data.decode('utf-8'))
            
            # 提取温度值
            sensor_id = temperature_data.get('sensorId', '未知')
            value = temperature_data.get('value', None)
            
            if value is not None:
                latest_temperature = {
                    'sensorId': sensor_id,
                    'value': value,
                    'timestamp': time.time()
                }
                last_temperature_time = time.time()
                
                # 发送成功响应
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'status': 'success', 'message': 'Temperature data received'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                # 发送错误响应
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'status': 'error', 'message': 'Invalid temperature data'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            # 发送错误响应
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'status': 'error', 'message': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """禁用默认日志输出"""
        pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """支持多线程的HTTP服务器"""
    pass

class TemperatureServerThread(QThread):
    """温度数据HTTP服务器线程"""
    update_status = pyqtSignal(str)
    
    def __init__(self, port=8090):
        super().__init__()
        self.port = port
        self.server = None
        self.running = False
        
    def run(self):
        try:
            self.server = ThreadedHTTPServer(('0.0.0.0', self.port), TemperatureHTTPHandler)
            self.server.timeout = 1.0  # 设置超时，使服务器可以定期检查running状态
            self.running = True
            self.update_status.emit(f"温度服务器已启动，端口: {self.port}")
            while self.running:
                try:
                    self.server.handle_request()
                except Exception as e:
                    if self.running:  # 只有还在运行时才报告错误
                        self.update_status.emit(f"温度服务器处理请求错误: {str(e)}")
        except Exception as e:
            self.update_status.emit(f"温度服务器错误: {str(e)}")
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.server_close()

class VideoThread(QThread):
    update_frame = pyqtSignal(np.ndarray, list)
    update_fps = pyqtSignal(float)
    update_status = pyqtSignal(str, str)  # 添加状态更新信号
    detection_finished = pyqtSignal()  # 检测完成信号（图片或视频结束）
    
    def __init__(self, source=0, model_path='yolov8n.pt', conf=0.25):
        super().__init__()
        self.source = source
        self.model_path = model_path
        self.conf = conf
        self.running = False
        self.use_camera = False
        self.fps = 0
        self.is_image = False
        
    def set_source(self, source, is_camera=False):
        self.source = source
        self.use_camera = is_camera
        # 检查是否是图片文件
        if isinstance(source, str) and source.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            self.is_image = True
        else:
            self.is_image = False
        
    def set_model(self, model_path):
        self.model_path = model_path
        
    def set_conf(self, conf):
        self.conf = conf
        
    def run(self):
        # 发送状态更新信号
        self.update_status.emit("正在加载模型...", "#FFA500")  # 橙色
        
        try:
            model = YOLO(self.model_path)
            self.update_status.emit("模型加载成功，准备视频源...", "#4CAF50")  # 绿色
            
            # 如果是图片，特殊处理
            if self.is_image:
                self.process_image(model)
                return
                
            cap = cv2.VideoCapture(self.source)
            
            if not cap.isOpened():
                self.update_status.emit(f"无法打开视频源: {self.source}", "#EA4335")  # 红色
                return
                
            self.running = True
            fps_counter = 0
            fps_timer = cv2.getTickCount()
            
            self.update_status.emit("检测中...", "#4CAF50")  # 绿色
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    if not self.use_camera:  # 如果是视频文件，结束线程
                        self.update_status.emit("视频结束", "#FFA500")  # 橙色
                        break
                    else:  # 如果是摄像头，尝试重新连接
                        self.update_status.emit("尝试重新连接摄像头...", "#FFA500")  # 橙色
                        cap = cv2.VideoCapture(self.source)
                        continue
                        
                # 执行YOLO预测
                results = model.predict(frame, conf=self.conf, verbose=False)
                
                # 发出更新信号
                self.update_frame.emit(frame, results)
                
                # 计算FPS
                fps_counter += 1
                if cv2.getTickCount() - fps_timer > cv2.getTickFrequency():
                    self.fps = fps_counter
                    self.update_fps.emit(fps_counter)
                    fps_counter = 0
                    fps_timer = cv2.getTickCount()
                    
            cap.release()
            # 视频播放完成，发送检测完成信号
            if not self.use_camera:
                self.detection_finished.emit()
            
        except Exception as e:
            self.update_status.emit(f"错误: {str(e)}", "#EA4335")  # 红色
            self.detection_finished.emit()
        
    def process_image(self, model):
        """处理单张图片"""
        try:
            # 读取图片
            img = cv2.imread(self.source)
            if img is None:
                self.update_status.emit(f"无法读取图片: {self.source}", "#EA4335")  # 红色
                return
                
            # 进行预测
            results = model.predict(img, conf=self.conf, verbose=False)
            
            # 发出更新信号
            self.update_frame.emit(img, results)
            
            # 发送一个合理的FPS
            self.update_fps.emit(0)
            
            # 完成状态
            self.update_status.emit("图片检测完成", "#4CAF50")  # 绿色
            # 发送检测完成信号
            self.detection_finished.emit()
            
        except Exception as e:
            self.update_status.emit(f"图片处理错误: {str(e)}", "#EA4335")  # 红色
            self.detection_finished.emit()
        
    def stop(self):
        self.running = False
        self.wait()

class YOLODetectorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO 烟雾与火灾检测器")
        self.setMinimumSize(1200, 700)
        
        # 设置主窗口颜色和字体
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#F5F7FA"))
        palette.setColor(QPalette.WindowText, QColor("#333333"))
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, QColor("#F5F7FA"))
        palette.setColor(QPalette.ToolTipBase, QColor("#333333"))
        palette.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
        palette.setColor(QPalette.Text, QColor("#333333"))
        palette.setColor(QPalette.Button, QColor("#4285F4"))
        palette.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
        palette.setColor(QPalette.BrightText, QColor("#EA4335"))
        palette.setColor(QPalette.Highlight, QColor("#4285F4"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(palette)
        
        # 设置全局字体
        font = self.font()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(10)
        self.setFont(font)
        
        # 初始化变量
        self.current_model = "yolov8n.pt"
        self.confidence = 0.25
        self.video_thread = None
        self.detection_running = False
        self.last_detection_counts = {}
        self.current_input_file = ""  # 当前输入文件路径
        self.temperature_server = None  # 温度数据服务器
        self.current_temperature_alert = None  # 当前温度报警状态
        
        # 报警去重控制（用于视频/摄像头实时检测）
        self.last_alert_states = {}  # 上次报警状态 {alert_key: {'level': int, 'time': timestamp}}
        self.alert_cooldown_seconds = 60  # 报警冷却时间（秒）
        self.is_realtime_detection = False  # 是否为实时检测（视频/摄像头）
        
        # 创建界面
        self.init_ui()
        
        # 显示欢迎信息
        self.show_welcome_message()
        
        # 扫描可用模型
        self.scan_available_models()
        
        # 启动温度数据服务器
        self.start_temperature_server()
        
        # 启动温度显示定时器
        self.start_temperature_timer()
        
    def init_ui(self):
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建左侧控制区
        left_panel = self.create_left_panel()
        
        # 创建中央显示区
        display_area = self.create_display_area()
        
        # 添加到主布局
        main_layout.addWidget(left_panel, 1)  # 1份宽度
        main_layout.addWidget(display_area, 3)  # 3份宽度
        
        # 创建状态栏
        self.create_statusbar()
        
        # 设置初始状态
        self.set_status("就绪，请选择输入源和模型", "#CCCCCC")
        
        # 添加键盘快捷键
        self.setup_shortcuts()
        
    def create_menubar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            background-color: #F5F7FA;
            border-bottom: 1px solid #E0E0E0;
            padding: 4px 0;
        """)
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        open_image_action = QAction("打开图片", self)
        open_image_action.setShortcut("Ctrl+O")
        open_image_action.triggered.connect(self.open_image)
        file_menu.addAction(open_image_action)
        
        open_video_action = QAction("打开视频", self)
        open_video_action.setShortcut("Ctrl+V")
        open_video_action.triggered.connect(self.open_video)
        file_menu.addAction(open_video_action)
        
        camera_action = QAction("摄像头开关", self)
        camera_action.setShortcut("Ctrl+C")
        camera_action.triggered.connect(self.toggle_camera)
        file_menu.addAction(camera_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Esc")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 检测菜单
        detect_menu = menubar.addMenu("检测")
        
        start_action = QAction("开始检测", self)
        start_action.triggered.connect(self.start_detection)
        detect_menu.addAction(start_action)
        
        stop_action = QAction("停止检测", self)
        stop_action.triggered.connect(self.stop_detection)
        detect_menu.addAction(stop_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        show_stats_action = QAction("显示统计信息", self)
        show_stats_action.setCheckable(True)
        show_stats_action.setChecked(True)
        show_stats_action.triggered.connect(self.toggle_stats_view)
        view_menu.addAction(show_stats_action)
        
        view_menu.addSeparator()
        
        # 报警记录查看
        view_alerts_action = QAction("📋 查看报警记录", self)
        view_alerts_action.triggered.connect(self.open_alert_view_window)
        view_menu.addAction(view_alerts_action)
        
    def open_alert_view_window(self):
        """打开报警查看窗口"""
        try:
            from alert_view_window import AlertViewWindow
            
            # 创建并显示报警查看窗口
            self.alert_view_window = AlertViewWindow(self)
            self.alert_view_window.setWindowModality(Qt.NonModal)  # 非模态窗口
            self.alert_view_window.show()
            self.alert_view_window.raise_()
            self.alert_view_window.activateWindow()
            
            self.log_info("已打开报警记录查看窗口")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开报警查看窗口失败: {str(e)}")
            self.log_info(f"打开报警查看窗口失败: {str(e)}")
        
    def create_left_panel(self):
        # 创建左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 输入源选择组
        source_group = QGroupBox("输入源选择")
        source_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                margin-top: 20px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        source_layout = QVBoxLayout(source_group)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头", "视频文件", "图片文件"])
        self.source_combo.currentIndexChanged.connect(self.source_changed)
        source_layout.addWidget(self.source_combo)
        
        # 添加浏览文件按钮
        self.browse_file_button = QPushButton("浏览文件...")
        self.browse_file_button.clicked.connect(self.browse_input_file)
        self.browse_file_button.setStyleSheet("""
            background-color: #4285F4;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 100px;
        """)
        source_layout.addWidget(self.browse_file_button)
        
        # 显示当前输入文件路径
        self.input_path_label = QLabel("")
        self.input_path_label.setWordWrap(True)
        source_layout.addWidget(self.input_path_label)
        
        # 模型设置组
        model_group = QGroupBox("模型设置")
        model_layout = QFormLayout(model_group)
        
        # 只使用下拉菜单选择模型
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.model_changed)
        model_layout.addRow("模型:", self.model_combo)
        
        # 显示当前模型路径
        self.model_path_label = QLabel(self.current_model)
        self.model_path_label.setWordWrap(True)
        model_layout.addRow("路径:", self.model_path_label)
        
        # 置信度滑块
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(1, 100)
        self.conf_slider.setValue(int(self.confidence * 100))
        self.conf_slider.valueChanged.connect(self.conf_changed)
        
        self.conf_label = QLabel(f"置信度: {self.confidence:.2f}")
        model_layout.addRow(self.conf_label, self.conf_slider)
        
        # 生产人员安全检测选项
        safety_group = QGroupBox("生产人员安全检测")
        safety_layout = QVBoxLayout(safety_group)
        safety_layout.setSpacing(5)
        safety_layout.setContentsMargins(10, 10, 10, 10)
        
        self.helmet_checkbox = QCheckBox("安全帽")
        self.helmet_checkbox.setChecked(True)
        self.helmet_checkbox.setStyleSheet("font-size: 11px;")
        safety_layout.addWidget(self.helmet_checkbox)
        
        self.vest_checkbox = QCheckBox("反光背心")
        self.vest_checkbox.setChecked(True)
        self.vest_checkbox.setStyleSheet("font-size: 11px;")
        safety_layout.addWidget(self.vest_checkbox)
        
        self.glove_checkbox = QCheckBox("手套")
        self.glove_checkbox.setChecked(False)
        self.glove_checkbox.setStyleSheet("font-size: 11px;")
        safety_layout.addWidget(self.glove_checkbox)
        
        model_layout.addRow(safety_group)
        
        # 检测控制组
        control_group = QGroupBox("检测控制")
        control_layout = QVBoxLayout(control_group)
        
        self.start_button = QPushButton("开始检测")
        self.start_button.clicked.connect(self.start_detection)
        self.start_button.setStyleSheet("""
            background-color: #4285F4;
            color: white;
            font-weight: bold;
            padding: 12px 24px;
            border-radius: 4px;
            min-width: 120px;
            font-family: Microsoft YaHei;
        """)
        
        self.stop_button = QPushButton("停止检测")
        self.stop_button.clicked.connect(self.stop_detection)
        self.stop_button.setStyleSheet("""
            background-color: #EA4335;
            color: white;
            font-weight: bold;
            padding: 12px 24px;
            border-radius: 4px;
            min-width: 120px;
            font-family: Microsoft YaHei;
        """)
        self.stop_button.setEnabled(False)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        
        # 检测结果统计组
        stats_group = QGroupBox("检测统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_table = QTableWidget(0, 2)  # 0行，2列
        self.stats_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
                alternate-background-color: #F5F7FA;
            }
            QHeaderView::section {
                background-color: #4285F4;
                color: white;
                padding: 6px;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)
        self.stats_table.setHorizontalHeaderLabels(["目标类别", "检测数量"])
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        stats_layout.addWidget(self.stats_table)
        
        # 安全警报区域 - 合并显示生产环境和人员安全警报
        alert_group = QGroupBox("安全警报")
        alert_layout = QVBoxLayout(alert_group)
        alert_layout.setSpacing(8)
        
        # 环境安全警报标签
        env_alert_label = QLabel("生产环境：")
        env_alert_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #333;")
        alert_layout.addWidget(env_alert_label)
        
        self.env_alert_text = QTextEdit()
        self.env_alert_text.setReadOnly(True)
        self.env_alert_text.setMaximumHeight(70)
        self.env_alert_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #4CAF50;
                border-radius: 6px;
                background-color: #E8F5E9;
                color: #2E7D32;
                font-size: 11px;
                padding: 5px;
            }
        """)
        alert_layout.addWidget(self.env_alert_text)
        
        # 人员安全警报标签
        person_alert_label = QLabel("生产人员：")
        person_alert_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #333;")
        alert_layout.addWidget(person_alert_label)
        
        self.person_alert_text = QTextEdit()
        self.person_alert_text.setReadOnly(True)
        self.person_alert_text.setMaximumHeight(50)
        self.person_alert_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #4CAF50;
                border-radius: 6px;
                background-color: #E8F5E9;
                color: #2E7D32;
                font-size: 11px;
                padding: 5px;
            }
        """)
        alert_layout.addWidget(self.person_alert_text)
        
        # 温度显示组
        temp_group = QGroupBox("区域温度")
        temp_layout = QVBoxLayout(temp_group)
        
        self.temp_label = QLabel("🌡️ 无数据")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setWordWrap(True)
        self.temp_label.setMinimumHeight(50)
        self.temp_label.setStyleSheet("""
            QLabel {
                border: 2px solid #9E9E9E;
                border-radius: 8px;
                background-color: #F5F5F5;
                color: #616161;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        temp_layout.addWidget(self.temp_label)
        
        # 温度状态说明
        self.temp_status_label = QLabel("等待温度数据...")
        self.temp_status_label.setAlignment(Qt.AlignCenter)
        self.temp_status_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 10px;
                padding: 2px;
            }
        """)
        temp_layout.addWidget(self.temp_status_label)
        
        # 添加所有组到左侧布局
        left_layout.addWidget(source_group)
        left_layout.addWidget(model_group)
        left_layout.addWidget(control_group)
        left_layout.addWidget(stats_group)
        left_layout.addWidget(alert_group)
        left_layout.addWidget(temp_group)
        left_layout.addStretch()
        
        return left_panel
        
    def create_display_area(self):
        # 创建中央显示区
        self.tab_widget = QTabWidget()
        
        # 实时检测标签页
        self.detection_tab = QWidget()
        detection_layout = QVBoxLayout(self.detection_tab)
        
        # 图像/视频显示标签
        self.display_label = QLabel("请选择输入源")
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setMinimumHeight(400)
        self.display_label.setStyleSheet("""
            border: 1px solid #E0E0E0;
            background-color: #FFFFFF;
            border-radius: 4px;
            padding: 8px;
        """)
        
        # 信息面板
        self.info_panel = QTextEdit()
        self.info_panel.setReadOnly(True)
        self.info_panel.setMinimumHeight(150)  # 增加最小高度
        self.info_panel.setStyleSheet("""
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            padding: 8px;
            font-family: Microsoft YaHei;
            font-size: 10pt;
        """)
        
        detection_layout.addWidget(self.display_label, 7)  # 占7份高度
        detection_layout.addWidget(self.info_panel, 3)     # 占3份高度
        
        # 添加标签页
        self.tab_widget.addTab(self.detection_tab, "实时检测")
        

        
        return self.tab_widget
        
    def create_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # 状态指示灯
        self.status_light = QLabel()
        self.status_light.setFixedSize(16, 16)
        self.status_light.setStyleSheet("""
            background-color: #CCCCCC;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
        """)
        self.statusbar.addWidget(self.status_light)
        
        # 状态文本
        self.status_text = QLabel()
        self.statusbar.addWidget(self.status_text)
        
        # FPS显示
        self.fps_label = QLabel("FPS: 0")
        self.statusbar.addPermanentWidget(self.fps_label)
        
        # 分辨率显示
        self.resolution_label = QLabel("分辨率: 0x0")
        self.statusbar.addPermanentWidget(self.resolution_label)
        
        # 模型状态
        self.model_status = QLabel("模型加载: ✗")
        self.statusbar.addPermanentWidget(self.model_status)
    
    def setup_shortcuts(self):
        """设置键盘快捷键"""
        # 快捷键已在创建操作时设置
        pass
        
    def show_welcome_message(self):
        """显示欢迎信息"""
        welcome_text = """
        <h3>欢迎使用 YOLO 烟雾与火灾检测器</h3>
        <p>本应用可以检测图像或视频中的烟雾和火灾。</p>
        <p><b>使用方法：</b></p>
        <ol>
            <li>从左侧面板选择输入源（摄像头、视频文件或图片文件）</li>
            <li>选择模型（可使用预设模型或自定义模型）</li>
            <li>调整检测置信度</li>
            <li>点击"开始检测"按钮</li>
        </ol>
        <p><b>快捷键：</b></p>
        <ul>
            <li>Ctrl+O：打开图片</li>
            <li>Ctrl+V：打开视频</li>
            <li>Ctrl+C：切换摄像头</li>
            <li>Esc：退出程序</li>
        </ul>
        """
        self.info_panel.setHtml(welcome_text)
        
    def set_status(self, text, color="#CCCCCC"):
        """设置状态栏状态"""
        self.status_text.setText(text)
        self.status_light.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
        # 同时在信息面板中显示状态变化
        self.log_info(f"状态: {text}")
        
    def log_info(self, text):
        """记录信息到信息面板"""
        current_text = self.info_panel.toPlainText()
        # 添加换行符，但避免开头多余的换行
        if current_text:
            text = "\n" + text
        self.info_panel.moveCursor(self.info_panel.textCursor().End)
        self.info_panel.insertPlainText(text)
        # 滚动到底部
        scrollbar = self.info_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def source_changed(self, index):
        """输入源变化处理"""
        self.log_info(f"选择输入源: {self.source_combo.currentText()}")
        if index == 0:  # 摄像头
            pass
        elif index == 1:  # 视频文件
            self.open_video()
        elif index == 2:  # 图片文件
            self.open_image()
            
    def model_changed(self, index):
        """模型变化处理"""
        if index < 0:
            return
            
        # 获取选中模型的数据
        model_path = self.model_combo.itemData(index)
        if model_path:
            self.current_model = model_path
            self.model_path_label.setText(self.current_model)
            self.log_info(f"选择模型: {self.current_model}")
            self.model_status.setText("模型加载: ✗")
            
    def scan_available_models(self):
        """扫描weights目录下可用的模型文件"""
        self.log_info("扫描可用模型文件...")
        try:
            # 获取weights目录路径
            weights_dir = os.path.join(os.getcwd(), "weights")
            model_files = []
            
            # 确保weights目录存在
            if not os.path.exists(weights_dir):
                os.makedirs(weights_dir)
                self.log_info(f"创建weights目录: {weights_dir}")
                
            # 搜索weights目录下的所有.pt文件
            if os.path.exists(weights_dir) and os.path.isdir(weights_dir):
                for file in os.listdir(weights_dir):
                    if file.endswith(".pt"):
                        model_path = os.path.join("weights", file)
                        model_files.append(model_path)
                        self.log_info(f"找到模型: {model_path}")
            
            # 清除当前模型列表
            self.model_combo.clear()
            
            # 添加预设模型（使用weights目录路径）
            self.model_combo.addItem("YOLOv8n", os.path.join("weights", "yolov8n.pt"))
            self.model_combo.addItem("YOLOv8s", os.path.join("weights", "yolov8s.pt"))
            self.model_combo.addItem("YOLOv8m", os.path.join("weights", "yolov8m.pt"))
            
            # 添加发现的模型
            if model_files:
                for model_file in model_files:
                    # 避免重复添加标准模型
                    if os.path.basename(model_file) not in ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]:
                        self.model_combo.addItem(os.path.basename(model_file), model_file)
                        
                self.log_info(f"从weights目录找到 {len(model_files)} 个模型文件")
            else:
                self.log_info("weights目录中未找到模型文件")
                
            return model_files
            
        except Exception as e:
            self.log_info(f"扫描模型文件时出错: {str(e)}")
            return []
            
    def browse_input_file(self):
        """浏览输入文件（图片或视频）"""
        current_source = self.source_combo.currentIndex()
        
        if current_source == 1:  # 视频文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择视频文件", "", 
                "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
            )
            if file_path:
                self.input_path_label.setText(file_path)
                self.log_info(f"选择视频文件: {file_path}")
                # 加载并显示第一帧预览
                self.load_video_preview(file_path)
                
        elif current_source == 2:  # 图片文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择图片文件", "", 
                "图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)"
            )
            if file_path:
                self.input_path_label.setText(file_path)
                self.log_info(f"选择图片文件: {file_path}")
                # 加载并显示图片预览
                self.load_image_preview(file_path)
                
    def load_video_preview(self, video_path):
        """加载视频的第一帧作为预览"""
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # 获取视频信息
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    # 更新分辨率标签
                    self.resolution_label.setText(f"分辨率: {width}x{height}")
                    
                    # 记录视频信息
                    self.log_info(f"视频信息: {width}x{height}, {fps:.2f}fps, {frame_count}帧")
                    
                    # 转换帧为QPixmap并显示
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_img)
                    self.display_image(pixmap)
                cap.release()
        except Exception as e:
            self.log_info(f"无法加载视频预览: {str(e)}")
            
    def load_image_preview(self, image_path):
        """加载图片预览"""
        try:
            img = cv2.imread(image_path)
            if img is not None:
                # 获取图片尺寸
                height, width = img.shape[:2]
                
                # 更新分辨率标签
                self.resolution_label.setText(f"分辨率: {width}x{height}")
                
                # 记录图片信息
                self.log_info(f"图片尺寸: {width}x{height}")
                
                # 转换为RGB并显示
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                h, w, ch = img_rgb.shape
                bytes_per_line = ch * w
                q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                self.display_image(pixmap)
        except Exception as e:
            self.log_info(f"无法加载图片预览: {str(e)}")
            
    def conf_changed(self, value):
        """置信度变化处理"""
        old_conf = self.confidence
        self.confidence = value / 100.0
        self.conf_label.setText(f"置信度: {self.confidence:.2f}")
        
        # 只在数值有显著变化时记录日志，避免滑块拖动产生大量日志
        if abs(old_conf - self.confidence) >= 0.05:
            self.log_info(f"置信度调整为: {self.confidence:.2f}")
            
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.set_conf(self.confidence)
            
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图像文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        
        if file_path:
            # 显示图片
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.display_image(pixmap)
                self.source_file = file_path
                self.source_combo.setCurrentIndex(2)  # 设置为图片文件
                self.resolution_label.setText(f"分辨率: {pixmap.width()}x{pixmap.height()}")
                self.log_info(f"打开图片: {file_path}")
                self.set_status("图片已加载，可以开始检测", "#4CAF50")  # 绿色
                
    def open_video(self):
        """打开视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.log_info(f"打开视频: {file_path}")
            # 打开视频并显示第一帧
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    height, width = frame.shape[:2]
                    self.resolution_label.setText(f"分辨率: {width}x{height}")
                    self.log_info(f"视频分辨率: {width}x{height}")
                    
                    # 转换并显示第一帧
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_img)
                    self.display_image(pixmap)
                    self.set_status("视频已加载，可以开始检测", "#4CAF50")  # 绿色
                    
                cap.release()
                
            self.source_file = file_path
            self.source_combo.setCurrentIndex(1)  # 设置为视频文件
            
    def toggle_camera(self):
        """切换摄像头状态"""
        if self.detection_running and self.source_combo.currentIndex() == 0:
            self.stop_detection()
            self.log_info("摄像头关闭")
        else:
            self.source_combo.setCurrentIndex(0)  # 设置为摄像头
            self.log_info("摄像头开启")
            self.start_detection()
            
    def toggle_stats_view(self, checked):
        """切换统计信息显示"""
        if hasattr(self, 'stats_table'):
            if checked:
                self.stats_table.parent().show()
                self.log_info("显示统计信息")
            else:
                self.stats_table.parent().hide()
                self.log_info("隐藏统计信息")
            
    def display_image(self, pixmap):
        """显示图像"""
        self.display_label.setPixmap(pixmap.scaled(
            self.display_label.width(), self.display_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
            
    def start_detection(self):
        """开始检测"""
        # 如果检测正在进行中，先停止当前检测
        if self.detection_running:
            self.log_info("检测已在进行中，先停止当前检测...")
            self.stop_detection()
            # 等待线程完全结束
            if self.video_thread:
                self.video_thread.wait(1000)  # 最多等待1秒
            
        # 根据选择的输入源设置
        source_index = self.source_combo.currentIndex()
        
        # 检查是否有选择模型
        if not self.current_model:
            QMessageBox.warning(self, "模型错误", "请选择模型")
            return
            
        # 检查模型文件是否存在
        model_path = self.current_model
        if os.path.exists(model_path):
            # 模型文件直接存在
            pass
        elif os.path.exists(os.path.join(os.getcwd(), model_path)):
            # 模型文件相对于当前工作目录
            model_path = os.path.join(os.getcwd(), model_path)
        else:
            QMessageBox.warning(self, "模型错误", f"找不到模型文件: {self.current_model}")
            self.log_info(f"错误: 找不到模型文件 {self.current_model}")
            return
            
        self.log_info(f"使用模型: {model_path}")
            
        try:
            # 根据输入源类型设置
            is_camera = False
            if source_index == 0:  # 摄像头
                source = 0
                is_camera = True
                self.log_info("使用摄像头作为输入源")
            elif source_index == 1:  # 视频文件
                input_path = self.input_path_label.text()
                if not input_path:
                    file_path, _ = QFileDialog.getOpenFileName(
                        self, "选择视频文件", "", 
                        "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
                    )
                    if not file_path:
                        self.log_info("未选择视频文件")
                        return
                    input_path = file_path
                    self.input_path_label.setText(input_path)
                
                if not os.path.exists(input_path):
                    QMessageBox.warning(self, "文件错误", f"无法访问视频文件: {input_path}")
                    return
                    
                source = input_path
                self.log_info(f"使用视频文件作为输入源: {input_path}")
            elif source_index == 2:  # 图片文件
                input_path = self.input_path_label.text()
                if not input_path:
                    file_path, _ = QFileDialog.getOpenFileName(
                        self, "选择图片文件", "", 
                        "图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)"
                    )
                    if not file_path:
                        self.log_info("未选择图片文件")
                        return
                    input_path = file_path
                    self.input_path_label.setText(input_path)
                
                if not os.path.exists(input_path):
                    QMessageBox.warning(self, "文件错误", f"无法访问图片文件: {input_path}")
                    return
                    
                source = input_path
                self.log_info(f"使用图片文件作为输入源: {input_path}")
            else:
                self.log_info("未知输入源类型")
                return
                
            # 创建并启动视频线程
            self.clear_detection_stats()
            self.detection_running = True
            
            # 判断是否为实时检测（视频或摄像头），用于报警去重控制
            # 图片检测时清空报警状态记录，视频/摄像头启用防重复机制
            self.is_realtime_detection = (source_index == 0) or (source_index == 1)
            if not self.is_realtime_detection:
                self.last_alert_states = {}
                self.log_info("图片检测模式：报警防重复机制已禁用")
            else:
                self.log_info("实时检测模式：报警防重复机制已启用（冷却期60秒）")
            
            # 禁用控制按钮
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.set_status("正在检测中...", "#4CAF50")  # 绿色
            self.model_status.setText("模型加载: ✓")
            
            # 创建视频处理线程
            self.video_thread = VideoThread(source, model_path, self.confidence)
            self.video_thread.set_source(source, is_camera)
            
            # 设置信号连接
            self.setup_video_thread_connections()
            
            # 启动线程
            self.video_thread.start()
            
        except Exception as e:
            self.detection_running = False
            self.log_info(f"启动检测出错: {str(e)}")
            self.set_status(f"检测启动失败: {str(e)}", "#EA4335")  # 红色
            
    def setup_video_thread_connections(self):
        """设置视频线程的信号连接"""
        self.video_thread.update_frame.connect(self.update_display)
        self.video_thread.update_fps.connect(self.update_fps)
        self.video_thread.update_status.connect(self.set_status)  # 连接状态更新信号
        self.video_thread.detection_finished.connect(self.on_detection_finished)  # 检测完成信号
                    
    def stop_detection(self):
        """停止检测"""
        if self.video_thread and self.video_thread.isRunning():
            self.log_info("停止检测")
            self.video_thread.stop()
            
        self._reset_detection_state()
    
    def on_detection_finished(self):
        """检测完成回调（图片处理完成或视频播放结束）"""
        self.log_info("检测完成，自动重置状态")
        self._reset_detection_state()
    
    def _reset_detection_state(self):
        """重置检测状态"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.detection_running = False
        self.set_status("就绪", "#CCCCCC")  # 灰色
        
    def update_display(self, frame, results):
        """更新显示画面和检测结果"""
        if not self.detection_running:
            return
            
        # 使用YOLO结果绘制框
        processed_img = None
        if results and len(results) > 0:
            # 获取第一个结果（通常只有一个）
            result = results[0]
            # 在图像上绘制检测框
            processed_img = result.plot()
            
            # 更新检测统计
            self.update_detection_stats(results)
        else:
            processed_img = frame
            
        # 转换为RGB并显示
        img_rgb = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # 显示图像
        self.display_image(pixmap)
        
    def update_detection_stats(self, results):
        """更新检测统计信息"""
        try:
            if not results:
                return
                
            # 清空当前统计
            current_counts = {}
            
            # 汇总当前帧的检测结果
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = r.names.get(cls_id, f"未知类别-{cls_id}")
                    
                    if cls_name in current_counts:
                        current_counts[cls_name] += 1
                    else:
                        current_counts[cls_name] = 1
            
            # 更新统计表格
            self.stats_table.setRowCount(len(current_counts))
            
            for row, (cls_name, count) in enumerate(current_counts.items()):
                # 类别名称
                name_item = QTableWidgetItem(cls_name)
                self.stats_table.setItem(row, 0, name_item)
                
                # 数量
                count_item = QTableWidgetItem(str(count))
                count_item.setTextAlignment(Qt.AlignCenter)
                self.stats_table.setItem(row, 1, count_item)
                
            # 保存当前统计结果
            self.last_detection_counts = current_counts
            
            # 更新安全警报（传递当前温度报警状态）
            self.update_alert(current_counts, self.current_temperature_alert)
            
        except Exception as e:
            self.log_info(f"更新统计信息出错: {str(e)}")
            
    def update_alert(self, current_counts, temperature_alert=None):
        """
        根据检测结果更新安全警报显示
        
        Args:
            current_counts: 检测到的目标类别和数量
            temperature_alert: 温度报警信息，格式为 {'level': 1/2/3, 'message': '...'}
        """
        try:
            # 获取检测到的类别（转换为小写以便匹配）
            detected_classes = set()
            class_counts = {}
            for cls_name, count in current_counts.items():
                cls_lower = cls_name.lower()
                detected_classes.add(cls_lower)
                class_counts[cls_lower] = count
            
            # 生产环境安全警报
            env_alerts = []
            env_max_level = 0  # 0=安全, 1=低, 2=中, 3=高
            
            # 火警检测（fire和smoke）
            has_fire = "fire" in detected_classes
            has_smoke = "smoke" in detected_classes
            
            if has_fire and has_smoke:
                env_alerts.append(f"🔥⚠️ 火警三级（最高）：检测到明火和烟雾，数量：火={class_counts.get('fire', 0)}, 烟={class_counts.get('smoke', 0)}")
                env_max_level = max(env_max_level, 3)
            elif has_fire:
                env_alerts.append(f"🔥 火警二级：检测到明火，数量：{class_counts.get('fire', 0)}")
                env_max_level = max(env_max_level, 2)
            elif has_smoke:
                env_alerts.append(f"💨 火警一级：检测到烟雾，数量：{class_counts.get('smoke', 0)}")
                env_max_level = max(env_max_level, 1)
            
            # 高温报警（从温度数据获取）
            if temperature_alert:
                temp_level = temperature_alert.get('level', 0)
                temp_msg = temperature_alert.get('message', '')
                if temp_level == 3:
                    env_alerts.append(f"🌡️⚠️ 高温三级（最高）：{temp_msg}")
                    env_max_level = max(env_max_level, 3)
                elif temp_level == 2:
                    env_alerts.append(f"🌡️ 高温二级：{temp_msg}")
                    env_max_level = max(env_max_level, 2)
                elif temp_level == 1:
                    env_alerts.append(f"🌡️ 高温一级：{temp_msg}")
                    env_max_level = max(env_max_level, 1)
            
            # 设置环境安全警报显示
            if env_alerts:
                env_text = "\n".join(env_alerts)
                env_style = self._get_alert_style(env_max_level)
            else:
                env_text = "✅ 生产环境安全"
                env_style = self._get_alert_style(0)
            
            self.env_alert_text.setText(env_text)
            self.env_alert_text.setStyleSheet(env_style)
            
            # 生产人员安全警报
            person_alerts = []
            person_alert_level = 0  # 0=正常, 1=警告
            
            # 获取勾选的检测项
            check_helmet = self.helmet_checkbox.isChecked()
            check_vest = self.vest_checkbox.isChecked()
            check_glove = self.glove_checkbox.isChecked()
            
            # 获取检测到的数量
            person_count = class_counts.get('person', 0)
            helmet_count = class_counts.get('helmet', 0)
            vest_count = class_counts.get('vest', 0)
            glove_count = class_counts.get('glove', 0)
            
            # 只有当检测到人员时才进行安全检测
            if person_count > 0:
                # 检查安全帽
                if check_helmet:
                    if helmet_count < person_count:
                        missing_helmet = person_count - helmet_count
                        person_alerts.append(f"⚠️ {missing_helmet}人未佩戴安全帽")
                        person_alert_level = max(person_alert_level, 1)
                    else:
                        person_alerts.append(f"✅ 安全帽：{helmet_count}人佩戴")
                
                # 检查反光背心
                if check_vest:
                    if vest_count < person_count:
                        missing_vest = person_count - vest_count
                        person_alerts.append(f"⚠️ {missing_vest}人未穿戴反光背心")
                        person_alert_level = max(person_alert_level, 1)
                    else:
                        person_alerts.append(f"✅ 反光背心：{vest_count}人穿戴")
                
                # 检查手套
                if check_glove:
                    if glove_count < person_count:
                        missing_glove = person_count - glove_count
                        person_alerts.append(f"⚠️ {missing_glove}人未佩戴手套")
                        person_alert_level = max(person_alert_level, 1)
                    else:
                        person_alerts.append(f"✅ 手套：{glove_count}人佩戴")
                
                # 如果没有勾选任何检测项
                if not (check_helmet or check_vest or check_glove):
                    person_alerts.append(f"ℹ️ 检测到{person_count}人（未启用安全检测）")
            else:
                person_alerts.append("ℹ️ 未检测到人员")
            
            # 设置人员安全警报显示
            if person_alerts:
                person_text = "\n".join(person_alerts)
                person_style = self._get_person_alert_style(person_alert_level)
            else:
                person_text = "ℹ️ 未检测到人员"
                person_style = self._get_person_alert_style(0)
            
            self.person_alert_text.setText(person_text)
            self.person_alert_text.setStyleSheet(person_style)
            
            # 保存报警信息到数据库（如果有报警）
            if env_max_level > 0 or person_alert_level > 0:
                self._save_alerts_to_database(env_alerts, person_alerts, class_counts, temperature_alert)
            
        except Exception as e:
            self.log_info(f"更新警报出错: {str(e)}")
    
    def _get_person_alert_style(self, level):
        """根据人员安全警报级别返回样式"""
        styles = {
            0: """
                QTextEdit {
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                    background-color: #E8F5E9;
                    color: #2E7D32;
                    font-size: 11px;
                    padding: 5px;
                }
            """,
            1: """
                QTextEdit {
                    border: 2px solid #F57C00;
                    border-radius: 6px;
                    background-color: #FFF3E0;
                    color: #E65100;
                    font-size: 11px;
                    padding: 5px;
                }
            """
        }
        return styles.get(level, styles[0])
    
    def _get_alert_style(self, level):
        """根据警报级别返回样式"""
        styles = {
            0: """
                QTextEdit {
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                    background-color: #E8F5E9;
                    color: #2E7D32;
                    font-size: 11px;
                    padding: 5px;
                }
            """,
            1: """
                QTextEdit {
                    border: 2px solid #FBC02D;
                    border-radius: 6px;
                    background-color: #FFFDE7;
                    color: #F57F17;
                    font-size: 11px;
                    padding: 5px;
                }
            """,
            2: """
                QTextEdit {
                    border: 2px solid #F57C00;
                    border-radius: 6px;
                    background-color: #FFF3E0;
                    color: #E65100;
                    font-size: 11px;
                    padding: 5px;
                }
            """,
            3: """
                QTextEdit {
                    border: 2px solid #D32F2F;
                    border-radius: 6px;
                    background-color: #FFEBEE;
                    color: #B71C1C;
                    font-size: 11px;
                    padding: 5px;
                }
            """
        }
        return styles.get(level, styles[0])
    
    def _should_save_alert(self, alert_key, alert_level):
        """
        判断是否应保存报警（防重复逻辑）
        
        规则：
        1. 图片检测：不受限制，每次都保存
        2. 实时检测（视频/摄像头）：
           - 报警级别升高（如1级→2级、2级→3级）：立即保存，不受时间限制
           - 报警级别不变或降低：需要间隔60秒才保存
           - 首次出现该类型报警：立即保存
        
        Args:
            alert_key: 报警类型标识（如 'fire', 'helmet' 等）
            alert_level: 报警级别
            
        Returns:
            bool: 是否应该保存报警
        """
        # 非实时检测（图片），直接保存
        if not self.is_realtime_detection:
            return True
        
        current_time = time.time()
        
        # 检查该类型报警的上次状态
        if alert_key in self.last_alert_states:
            last_state = self.last_alert_states[alert_key]
            last_level = last_state['level']
            last_time = last_state['time']
            
            # 报警级别升高，立即保存（如1级→2级、2级→3级）
            if alert_level > last_level:
                self.log_info(f"[{alert_key}] 报警级别升高 ({last_level}级→{alert_level}级)，立即保存")
                self.last_alert_states[alert_key] = {'level': alert_level, 'time': current_time}
                return True
            
            # 报警级别不变或降低，检查冷却时间
            elapsed = current_time - last_time
            if elapsed < self.alert_cooldown_seconds:
                # 冷却时间内，不保存
                action = "保持不变" if alert_level == last_level else "降低"
                self.log_info(f"[{alert_key}] 报警级别{action} ({last_level}级→{alert_level}级)，冷却中还需 {int(self.alert_cooldown_seconds - elapsed)} 秒")
                return False
            
            # 冷却时间已过，更新状态并保存
            self.last_alert_states[alert_key] = {'level': alert_level, 'time': current_time}
            return True
        else:
            # 首次出现该类型报警，保存并记录状态
            self.last_alert_states[alert_key] = {'level': alert_level, 'time': current_time}
            return True
    
    def _save_alerts_to_database(self, env_alerts, person_alerts, class_counts, temperature_alert):
        """
        保存报警信息到数据库
        
        Args:
            env_alerts: 环境安全警报列表
            person_alerts: 人员安全警报列表
            class_counts: 检测到的类别数量
            temperature_alert: 温度报警信息
        """
        try:
            alert_repo = get_alert_repository()
            auth_manager = get_auth_manager()
            
            # 获取当前用户信息
            current_user = auth_manager.current_user
            resolved_by = current_user.get('username') if current_user else 'system'
            
            # 保存环境安全报警
            detected_objects = {
                'fire': class_counts.get('fire', 0),
                'smoke': class_counts.get('smoke', 0),
                'person': class_counts.get('person', 0),
                'helmet': class_counts.get('helmet', 0),
                'vest': class_counts.get('vest', 0),
                'glove': class_counts.get('glove', 0)
            }
            
            # 火警报警
            if class_counts.get('fire', 0) > 0 or class_counts.get('smoke', 0) > 0:
                fire_level = 0
                if class_counts.get('fire', 0) > 0 and class_counts.get('smoke', 0) > 0:
                    fire_level = 3
                elif class_counts.get('fire', 0) > 0:
                    fire_level = 2
                elif class_counts.get('smoke', 0) > 0:
                    fire_level = 1
                
                # 检查是否应该保存（防重复）
                if self._should_save_alert('fire', fire_level):
                    fire_message = "; ".join([alert for alert in env_alerts if '火警' in alert])
                    
                    result = alert_repo.create_alert(
                        alert_type='fire',
                        alert_category='environment',
                        alert_level=fire_level,
                        alert_message=fire_message,
                        detected_objects=detected_objects,
                        temperature_data=temperature_alert
                    )
                    if result['success']:
                        self.log_info(f"火警报警已保存到数据库，ID: {result.get('alert_id')}")
                else:
                    self.log_info("火警报警处于冷却期，跳过保存")
            
            # 高温报警
            if temperature_alert and temperature_alert.get('level', 0) > 0:
                temp_level = temperature_alert.get('level', 1)
                
                # 检查是否应该保存（防重复）
                if self._should_save_alert('temperature', temp_level):
                    result = alert_repo.create_alert(
                        alert_type='temperature',
                        alert_category='environment',
                        alert_level=temp_level,
                        alert_message=temperature_alert.get('message', '温度异常'),
                        detected_objects=detected_objects,
                        temperature_data=temperature_alert
                    )
                    if result['success']:
                        self.log_info(f"高温报警已保存到数据库，ID: {result.get('alert_id')}")
                else:
                    self.log_info("高温报警处于冷却期，跳过保存")
            
            # 人员安全报警 - 根据勾选和检测数量判断是否报警
            person_count = class_counts.get('person', 0)
            helmet_count = class_counts.get('helmet', 0)
            vest_count = class_counts.get('vest', 0)
            glove_count = class_counts.get('glove', 0)
            
            # 获取勾选的检测项
            check_helmet = self.helmet_checkbox.isChecked()
            check_vest = self.vest_checkbox.isChecked()
            check_glove = self.glove_checkbox.isChecked()
            
            # 只有当检测到人员且勾选了检测项时才保存报警
            if person_count > 0:
                # 安全帽报警
                if check_helmet and helmet_count < person_count:
                    # 检查是否应该保存（防重复）
                    if self._should_save_alert('helmet', 1):
                        missing = person_count - helmet_count
                        result = alert_repo.create_alert(
                            alert_type='helmet',
                            alert_category='personnel',
                            alert_level=1,
                            alert_message=f"{missing}人未佩戴安全帽（共{person_count}人）",
                            detected_objects=detected_objects
                        )
                        if result['success']:
                            self.log_info(f"安全帽报警已保存到数据库，ID: {result.get('alert_id')}")
                    else:
                        self.log_info("安全帽报警处于冷却期，跳过保存")
                
                # 反光背心报警
                if check_vest and vest_count < person_count:
                    # 检查是否应该保存（防重复）
                    if self._should_save_alert('vest', 1):
                        missing = person_count - vest_count
                        result = alert_repo.create_alert(
                            alert_type='vest',
                            alert_category='personnel',
                            alert_level=1,
                            alert_message=f"{missing}人未穿戴反光背心（共{person_count}人）",
                            detected_objects=detected_objects
                        )
                        if result['success']:
                            self.log_info(f"反光背心报警已保存到数据库，ID: {result.get('alert_id')}")
                    else:
                        self.log_info("反光背心报警处于冷却期，跳过保存")
                
                # 手套报警
                if check_glove and glove_count < person_count:
                    # 检查是否应该保存（防重复）
                    if self._should_save_alert('glove', 1):
                        missing = person_count - glove_count
                        result = alert_repo.create_alert(
                            alert_type='glove',
                            alert_category='personnel',
                            alert_level=1,
                            alert_message=f"{missing}人未佩戴手套（共{person_count}人）",
                            detected_objects=detected_objects
                        )
                        if result['success']:
                            self.log_info(f"手套报警已保存到数据库，ID: {result.get('alert_id')}")
                    else:
                        self.log_info("手套报警处于冷却期，跳过保存")
                    
        except Exception as e:
            self.log_info(f"保存报警到数据库失败: {str(e)}")
            
    def clear_detection_stats(self):
        """清空检测统计"""
        self.last_detection_counts = {}
        self.stats_table.setRowCount(0)
        # 重置环境安全警报为安全状态
        self.env_alert_text.setText("✅ 生产环境安全")
        self.env_alert_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #4CAF50;
                border-radius: 6px;
                background-color: #E8F5E9;
                color: #2E7D32;
                font-size: 11px;
                padding: 5px;
            }
        """)
        # 重置人员安全警报
        self.person_alert_text.setText("ℹ️ 未检测到人员")
        self.person_alert_text.setStyleSheet(self._get_person_alert_style(0))
            
    def update_fps(self, fps):
        """更新FPS显示"""
        self.fps_label.setText(f"FPS: {int(fps)}")
        
    def start_temperature_server(self):
        """启动温度数据HTTP服务器"""
        try:
            self.temperature_server = TemperatureServerThread(port=8090)
            self.temperature_server.update_status.connect(self.log_info)
            self.temperature_server.start()
            self.log_info("温度数据接收服务已启动 (端口: 8090)")
        except Exception as e:
            self.log_info(f"启动温度服务器失败: {str(e)}")
    
    def start_temperature_timer(self):
        """启动温度显示定时器"""
        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temperature_display)
        self.temp_timer.start(1000)  # 每秒更新一次
        self.log_info("温度显示定时器已启动")
    
    def update_temperature_display(self):
        """更新温度显示"""
        global latest_temperature, last_temperature_time, TEMPERATURE_TIMEOUT
        
        try:
            current_time = time.time()
            
            # 检查是否有温度数据
            if latest_temperature is None:
                # 无数据状态
                self.temp_label.setText("🌡️ 无数据")
                self.temp_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #9E9E9E;
                        border-radius: 8px;
                        background-color: #F5F5F5;
                        color: #616161;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """)
                self.temp_status_label.setText("等待温度数据...")
                self.temp_status_label.setStyleSheet("""
                    QLabel {
                        color: #9E9E9E;
                        font-size: 10px;
                        padding: 2px;
                    }
                """)
            elif current_time - last_temperature_time > TEMPERATURE_TIMEOUT:
                # 数据超时
                self.temp_label.setText(f"🌡️ {latest_temperature['value']:.1f}°C")
                self.temp_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #FF9800;
                        border-radius: 8px;
                        background-color: #FFF3E0;
                        color: #E65100;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """)
                self.temp_status_label.setText(f"传感器 {latest_temperature['sensorId']} - 数据已过期")
                self.temp_status_label.setStyleSheet("""
                    QLabel {
                        color: #FF9800;
                        font-size: 10px;
                        padding: 2px;
                    }
                """)
            else:
                # 正常数据
                temp_value = latest_temperature['value']
                sensor_id = latest_temperature['sensorId']
                
                # 根据温度值设置不同颜色和报警级别
                if temp_value > 50:
                    # 高温警告 - 三级
                    border_color = "#D32F2F"
                    bg_color = "#FFEBEE"
                    text_color = "#B71C1C"
                    status_text = "⚠️ 温度过高！"
                    status_color = "#D32F2F"
                    self.current_temperature_alert = {
                        'level': 3,
                        'message': f'温度{temp_value:.1f}°C超过50°C',
                        'value': temp_value,
                        'sensor_id': sensor_id
                    }
                elif temp_value > 30:
                    # 中等温度 - 二级
                    border_color = "#FF9800"
                    bg_color = "#FFF3E0"
                    text_color = "#E65100"
                    status_text = "温度偏高"
                    status_color = "#FF9800"
                    self.current_temperature_alert = {
                        'level': 2,
                        'message': f'温度{temp_value:.1f}°C超过30°C',
                        'value': temp_value,
                        'sensor_id': sensor_id
                    }
                else:
                    # 正常温度
                    border_color = "#4CAF50"
                    bg_color = "#E8F5E9"
                    text_color = "#2E7D32"
                    status_text = "温度正常"
                    status_color = "#4CAF50"
                    self.current_temperature_alert = None
                
                self.temp_label.setText(f"🌡️ {temp_value:.1f}°C")
                self.temp_label.setStyleSheet(f"""
                    QLabel {{
                        border: 2px solid {border_color};
                        border-radius: 8px;
                        background-color: {bg_color};
                        color: {text_color};
                        font-size: 16px;
                        font-weight: bold;
                        padding: 10px;
                    }}
                """)
                self.temp_status_label.setText(f"传感器 {sensor_id} - {status_text}")
                self.temp_status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {status_color};
                        font-size: 10px;
                        padding: 2px;
                    }}
                """)
                
        except Exception as e:
            self.log_info(f"更新温度显示出错: {str(e)}")
        
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 关闭窗口时停止线程
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
        
        # 停止温度服务器
        if self.temperature_server and self.temperature_server.isRunning():
            self.temperature_server.stop()
            self.temperature_server.wait()
            self.log_info("温度服务器已停止")
        
        # 停止温度定时器
        if hasattr(self, 'temp_timer'):
            self.temp_timer.stop()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YOLODetectorGUI()
    window.show()
    sys.exit(app.exec_())