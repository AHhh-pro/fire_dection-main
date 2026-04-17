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
            
        except Exception as e:
            self.update_status.emit(f"错误: {str(e)}", "#EA4335")  # 红色
        
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
            
        except Exception as e:
            self.update_status.emit(f"图片处理错误: {str(e)}", "#EA4335")  # 红色
        
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
        self.save_detection_results = False  # 是否保存检测结果
        self.current_input_file = ""  # 当前输入文件路径
        self.temperature_server = None  # 温度数据服务器
        
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
        
        # 添加保存检测结果选项
        self.save_results_checkbox = QCheckBox("保存检测结果")
        self.save_results_checkbox.setChecked(self.save_detection_results)
        self.save_results_checkbox.stateChanged.connect(self.toggle_save_results)
        model_layout.addRow("保存选项:", self.save_results_checkbox)
        
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
        
        # 检测结果告知栏
        alert_group = QGroupBox("安全警报")
        alert_layout = QVBoxLayout(alert_group)
        
        self.alert_label = QLabel("未检测到危险")
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setWordWrap(True)
        self.alert_label.setMinimumHeight(60)
        self.alert_label.setStyleSheet("""
            QLabel {
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #E8F5E9;
                color: #2E7D32;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        alert_layout.addWidget(self.alert_label)
        
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
        if self.detection_running:
            self.log_info("检测已在进行中")
            return
            
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
                    
    def stop_detection(self):
        """停止检测"""
        if self.video_thread and self.video_thread.isRunning():
            self.log_info("停止检测")
            self.video_thread.stop()
            
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
            
            # 如果启用了保存功能，保存处理后的图像
            if self.save_detection_results:
                self.save_detection_image(processed_img)
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
        
    def save_detection_image(self, image):
        """保存处理后的检测图像"""
        try:
            # 创建results目录（如果不存在）
            save_dir = os.path.join(os.getcwd(), "results")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            # 生成文件名（使用时间戳）
            timestamp = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
            filename = f"detection_{timestamp}.jpg"
            save_path = os.path.join(save_dir, filename)
            
            # 保存图像
            cv2.imwrite(save_path, image)
            self.log_info(f"已保存检测结果: {save_path}")
            
        except Exception as e:
            self.log_info(f"保存检测结果出错: {str(e)}")
            
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
            
            # 更新安全警报
            self.update_alert(current_counts)
            
        except Exception as e:
            self.log_info(f"更新统计信息出错: {str(e)}")
            
    def update_alert(self, current_counts):
        """根据检测结果更新安全警报显示"""
        try:
            # 获取检测到的类别（转换为小写以便匹配）
            detected_classes = set()
            for cls_name in current_counts.keys():
                detected_classes.add(cls_name.lower())
            
            # 判断危险等级
            has_fire = "fire" in detected_classes
            has_smoke = "smoke" in detected_classes
            
            if has_fire and has_smoke:
                # 最高级别：同时检测到火焰和烟雾
                alert_text = "⚠️ 警告！检测到火焰和烟雾！\n请立即采取紧急措施！"
                alert_style = """
                    QLabel {
                        border: 3px solid #D32F2F;
                        border-radius: 8px;
                        background-color: #FFEBEE;
                        color: #B71C1C;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """
            elif has_fire:
                # 高级别：检测到火焰
                alert_text = "🔥 警告！检测到火焰！\n请立即处理！"
                alert_style = """
                    QLabel {
                        border: 3px solid #F57C00;
                        border-radius: 8px;
                        background-color: #FFF3E0;
                        color: #E65100;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """
            elif has_smoke:
                # 中级别：检测到烟雾
                alert_text = "💨 注意！检测到烟雾！\n请密切关注！"
                alert_style = """
                    QLabel {
                        border: 3px solid #FBC02D;
                        border-radius: 8px;
                        background-color: #FFFDE7;
                        color: #F57F17;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """
            else:
                # 安全状态
                alert_text = "✅ 未检测到危险\n环境安全"
                alert_style = """
                    QLabel {
                        border: 2px solid #4CAF50;
                        border-radius: 8px;
                        background-color: #E8F5E9;
                        color: #2E7D32;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """
            
            self.alert_label.setText(alert_text)
            self.alert_label.setStyleSheet(alert_style)
            
        except Exception as e:
            self.log_info(f"更新警报出错: {str(e)}")
            
    def clear_detection_stats(self):
        """清空检测统计"""
        self.last_detection_counts = {}
        self.stats_table.setRowCount(0)
        # 重置警报为安全状态
        self.alert_label.setText("✅ 未检测到危险\n环境安全")
        self.alert_label.setStyleSheet("""
            QLabel {
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #E8F5E9;
                color: #2E7D32;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
        """)
            
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
                
                # 根据温度值设置不同颜色
                if temp_value > 50:
                    # 高温警告
                    border_color = "#D32F2F"
                    bg_color = "#FFEBEE"
                    text_color = "#B71C1C"
                    status_text = "⚠️ 温度过高！"
                    status_color = "#D32F2F"
                elif temp_value > 30:
                    # 中等温度
                    border_color = "#FF9800"
                    bg_color = "#FFF3E0"
                    text_color = "#E65100"
                    status_text = "温度偏高"
                    status_color = "#FF9800"
                else:
                    # 正常温度
                    border_color = "#4CAF50"
                    bg_color = "#E8F5E9"
                    text_color = "#2E7D32"
                    status_text = "温度正常"
                    status_color = "#4CAF50"
                
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

    def toggle_save_results(self, state):
        """切换是否保存检测结果"""
        self.save_detection_results = bool(state)
        self.log_info(f"{'启用' if self.save_detection_results else '禁用'}检测结果保存")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YOLODetectorGUI()
    window.show()
    sys.exit(app.exec_())