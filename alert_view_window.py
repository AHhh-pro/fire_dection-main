"""
报警查看窗口模块
用于显示和管理历史报警记录
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QLineEdit, QGroupBox, QSplitter, QFrame,
    QMessageBox, QAbstractItemView, QMenu, QAction, QStatusBar,
    QTabWidget, QGridLayout, QSpinBox
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QBrush
from datetime import datetime, timedelta
import json

from database import get_alert_repository
from auth_manager import get_auth_manager


class AlertViewWindow(QMainWindow):
    """报警查看窗口"""
    
    # 信号定义
    alert_resolved = pyqtSignal(int)  # 报警已处理信号，传递报警ID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("报警记录管理")
        self.setMinimumSize(1200, 800)
        self.alert_repo = get_alert_repository()
        self.auth_manager = get_auth_manager()
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F7FA;
            }
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333;
            }
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3367D6;
            }
            QPushButton:pressed {
                background-color: #2A56C6;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
            QPushButton#secondary {
                background-color: #757575;
            }
            QPushButton#secondary:hover {
                background-color: #616161;
            }
            QPushButton#success {
                background-color: #4CAF50;
            }
            QPushButton#success:hover {
                background-color: #388E3C;
            }
            QPushButton#danger {
                background-color: #F44336;
            }
            QPushButton#danger:hover {
                background-color: #D32F2F;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                gridline-color: #EEEEEE;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EEEEEE;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #4285F4;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QComboBox, QDateEdit, QLineEdit, QSpinBox {
                padding: 6px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QComboBox:hover, QDateEdit:hover, QLineEdit:hover {
                border-color: #4285F4;
            }
            QComboBox:focus, QDateEdit:focus, QLineEdit:focus {
                border-color: #4285F4;
            }
            QLabel {
                font-size: 12px;
                color: #333;
            }
            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            QLabel#stats {
                font-size: 14px;
                font-weight: bold;
                color: #4285F4;
            }
        """)
        
        self.init_ui()
        self.load_alerts()
        
        # 启动定时器，每30秒自动刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_alerts)
        self.refresh_timer.start(30000)
    
    def init_ui(self):
        """初始化界面"""
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        title_label = QLabel("📋 报警记录管理")
        title_label.setObjectName("title")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 自动刷新开关
        self.auto_refresh_checkbox = QPushButton("🔄 自动刷新: 开")
        self.auto_refresh_checkbox.setCheckable(True)
        self.auto_refresh_checkbox.setChecked(True)
        self.auto_refresh_checkbox.clicked.connect(self.toggle_auto_refresh)
        self.auto_refresh_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
            QPushButton:!checked {
                background-color: #757575;
            }
        """)
        title_layout.addWidget(self.auto_refresh_checkbox)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 立即刷新")
        refresh_btn.clicked.connect(self.load_alerts)
        refresh_btn.setObjectName("secondary")
        title_layout.addWidget(refresh_btn)
        
        # 关闭按钮
        close_btn = QPushButton("❌ 关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setObjectName("danger")
        title_layout.addWidget(close_btn)
        
        main_layout.addLayout(title_layout)
        
        # 统计信息区域
        stats_group = QGroupBox("📊 统计概览")
        stats_layout = QHBoxLayout(stats_group)
        
        self.total_label = QLabel("总报警数: 0")
        self.total_label.setObjectName("stats")
        stats_layout.addWidget(self.total_label)
        
        stats_layout.addSpacing(30)
        
        self.active_label = QLabel("未处理: 0")
        self.active_label.setObjectName("stats")
        self.active_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #F44336;")
        stats_layout.addWidget(self.active_label)
        
        stats_layout.addSpacing(30)
        
        self.env_label = QLabel("环境安全: 0")
        self.env_label.setObjectName("stats")
        self.env_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF9800;")
        stats_layout.addWidget(self.env_label)
        
        stats_layout.addSpacing(30)
        
        self.person_label = QLabel("人员安全: 0")
        self.person_label.setObjectName("stats")
        self.person_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
        stats_layout.addWidget(self.person_label)
        
        stats_layout.addStretch()
        
        main_layout.addWidget(stats_group)
        
        # 筛选区域
        filter_group = QGroupBox("🔍 筛选条件")
        filter_layout = QGridLayout(filter_group)
        filter_layout.setSpacing(10)
        
        # 报警类别
        filter_layout.addWidget(QLabel("报警类别:"), 0, 0)
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "环境安全", "人员安全"])
        self.category_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.category_combo, 0, 1)
        
        # 报警级别
        filter_layout.addWidget(QLabel("报警级别:"), 0, 2)
        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "一级", "二级", "三级"])
        self.level_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.level_combo, 0, 3)
        
        # 处理状态
        filter_layout.addWidget(QLabel("处理状态:"), 0, 4)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "未处理", "已处理"])
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.status_combo, 0, 5)
        
        # 日期范围
        filter_layout.addWidget(QLabel("开始日期:"), 1, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.dateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.start_date, 1, 1)
        
        filter_layout.addWidget(QLabel("结束日期:"), 1, 2)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.end_date, 1, 3)
        
        # 搜索框
        filter_layout.addWidget(QLabel("关键词:"), 1, 4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索报警类型、消息...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.search_input, 1, 5)
        
        # 重置按钮
        reset_btn = QPushButton("🔄 重置筛选")
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setObjectName("secondary")
        filter_layout.addWidget(reset_btn, 0, 6, 2, 1)
        
        filter_layout.setColumnStretch(6, 1)
        
        main_layout.addWidget(filter_group)
        
        # 报警列表
        list_group = QGroupBox("📋 报警列表")
        list_layout = QVBoxLayout(list_group)
        
        # 创建表格
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(9)
        self.alert_table.setHorizontalHeaderLabels([
            "ID", "报警时间", "类别", "类型", "级别", "状态", "报警消息", "处理人", "操作"
        ])
        
        # 设置列宽
        self.alert_table.setColumnWidth(0, 50)   # ID
        self.alert_table.setColumnWidth(1, 150)  # 时间
        self.alert_table.setColumnWidth(2, 80)   # 类别
        self.alert_table.setColumnWidth(3, 80)   # 类型
        self.alert_table.setColumnWidth(4, 60)   # 级别
        self.alert_table.setColumnWidth(5, 70)   # 状态
        self.alert_table.setColumnWidth(6, 300)  # 消息
        self.alert_table.setColumnWidth(7, 80)   # 处理人
        self.alert_table.setColumnWidth(8, 80)   # 操作
        
        self.alert_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.alert_table.verticalHeader().setVisible(False)
        self.alert_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.alert_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.alert_table.setAlternatingRowColors(True)
        self.alert_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.alert_table.customContextMenuRequested.connect(self.show_context_menu)
        
        list_layout.addWidget(self.alert_table)
        
        # 批量操作按钮
        btn_layout = QHBoxLayout()
        
        self.resolve_selected_btn = QPushButton("✓ 处理选中报警")
        self.resolve_selected_btn.clicked.connect(self.resolve_selected_alert)
        self.resolve_selected_btn.setObjectName("success")
        btn_layout.addWidget(self.resolve_selected_btn)
        
        btn_layout.addStretch()
        
        # 分页控制
        btn_layout.addWidget(QLabel("每页显示:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100", "全部"])
        self.page_size_combo.setCurrentIndex(1)
        self.page_size_combo.currentIndexChanged.connect(self.load_alerts)
        btn_layout.addWidget(self.page_size_combo)
        
        btn_layout.addSpacing(20)
        
        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        btn_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("第 1 页")
        btn_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.clicked.connect(self.next_page)
        btn_layout.addWidget(self.next_btn)
        
        list_layout.addLayout(btn_layout)
        
        main_layout.addWidget(list_group, 1)
        
        # 状态栏
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")
        
        # 当前页码
        self.current_page = 1
        self.all_alerts = []
    
    def load_alerts(self):
        """加载报警数据"""
        try:
            self.statusbar.showMessage("正在加载报警数据...")
            
            # 获取日期范围
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().addDays(1).toString("yyyy-MM-dd")
            
            # 从数据库获取报警
            alerts = self.alert_repo.get_alerts_by_date_range(start_date, end_date)
            self.all_alerts = alerts
            
            # 应用筛选
            filtered_alerts = self.filter_alerts(alerts)
            
            # 更新统计
            self.update_statistics(alerts)
            
            # 分页显示
            self.display_alerts(filtered_alerts)
            
            self.statusbar.showMessage(f"共加载 {len(filtered_alerts)} 条报警记录")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载报警数据失败: {str(e)}")
            self.statusbar.showMessage("加载失败")
    
    def filter_alerts(self, alerts):
        """根据筛选条件过滤报警"""
        filtered = []
        
        category_filter = self.category_combo.currentIndex()
        level_filter = self.level_combo.currentIndex()
        status_filter = self.status_combo.currentIndex()
        keyword = self.search_input.text().lower()
        
        for alert in alerts:
            # 类别筛选
            if category_filter == 1 and alert.get('alert_category') != 'environment':
                continue
            if category_filter == 2 and alert.get('alert_category') != 'personnel':
                continue
            
            # 级别筛选
            if level_filter > 0 and alert.get('alert_level') != level_filter:
                continue
            
            # 状态筛选
            if status_filter == 1 and alert.get('status') != 'active':
                continue
            if status_filter == 2 and alert.get('status') != 'resolved':
                continue
            
            # 关键词搜索
            if keyword:
                alert_type = alert.get('alert_type', '').lower()
                message = alert.get('alert_message', '').lower()
                if keyword not in alert_type and keyword not in message:
                    continue
            
            filtered.append(alert)
        
        return filtered
    
    def display_alerts(self, alerts):
        """显示报警列表"""
        # 获取分页设置
        page_size_text = self.page_size_combo.currentText()
        if page_size_text == "全部":
            page_size = len(alerts)
            self.current_page = 1
        else:
            page_size = int(page_size_text)
        
        # 计算分页
        total_pages = max(1, (len(alerts) + page_size - 1) // page_size)
        self.current_page = min(self.current_page, total_pages)
        
        start_idx = (self.current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(alerts))
        page_alerts = alerts[start_idx:end_idx]
        
        # 更新分页按钮状态
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)
        self.page_label.setText(f"第 {self.current_page} / {total_pages} 页 (共 {len(alerts)} 条)")
        
        # 填充表格
        self.alert_table.setRowCount(len(page_alerts))
        
        for row, alert in enumerate(page_alerts):
            # ID
            self.alert_table.setItem(row, 0, QTableWidgetItem(str(alert.get('id', ''))))
            
            # 时间
            created_at = alert.get('created_at', '')
            if isinstance(created_at, datetime):
                created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
            self.alert_table.setItem(row, 1, QTableWidgetItem(str(created_at)))
            
            # 类别
            category = alert.get('alert_category', '')
            category_text = "环境安全" if category == 'environment' else "人员安全"
            category_item = QTableWidgetItem(category_text)
            if category == 'environment':
                category_item.setForeground(QBrush(QColor("#FF9800")))
            else:
                category_item.setForeground(QBrush(QColor("#2196F3")))
            self.alert_table.setItem(row, 2, category_item)
            
            # 类型
            alert_type = alert.get('alert_type', '')
            type_map = {
                'fire': '火警',
                'smoke': '烟雾',
                'temperature': '高温',
                'helmet': '安全帽',
                'vest': '反光背心',
                'glove': '手套'
            }
            self.alert_table.setItem(row, 3, QTableWidgetItem(type_map.get(alert_type, alert_type)))
            
            # 级别
            level = alert.get('alert_level', 0)
            level_item = QTableWidgetItem(f"{level}级")
            if level == 3:
                level_item.setBackground(QBrush(QColor("#FFEBEE")))
                level_item.setForeground(QBrush(QColor("#B71C1C")))
            elif level == 2:
                level_item.setBackground(QBrush(QColor("#FFF3E0")))
                level_item.setForeground(QBrush(QColor("#E65100")))
            elif level == 1:
                level_item.setBackground(QBrush(QColor("#FFFDE7")))
                level_item.setForeground(QBrush(QColor("#F57F17")))
            self.alert_table.setItem(row, 4, level_item)
            
            # 状态
            status = alert.get('status', '')
            status_text = "未处理" if status == 'active' else "已处理"
            status_item = QTableWidgetItem(status_text)
            if status == 'active':
                status_item.setForeground(QBrush(QColor("#F44336")))
                status_item.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            else:
                status_item.setForeground(QBrush(QColor("#4CAF50")))
            self.alert_table.setItem(row, 5, status_item)
            
            # 消息
            self.alert_table.setItem(row, 6, QTableWidgetItem(alert.get('alert_message', '')))
            
            # 处理人
            resolved_by = alert.get('resolved_by', '')
            self.alert_table.setItem(row, 7, QTableWidgetItem(resolved_by if resolved_by else '-'))
            
            # 操作按钮
            if status == 'active':
                resolve_btn = QPushButton("处理")
                resolve_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        padding: 4px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #388E3C;
                    }
                """)
                resolve_btn.clicked.connect(lambda checked, aid=alert.get('id'): self.resolve_alert(aid))
                self.alert_table.setCellWidget(row, 8, resolve_btn)
            else:
                self.alert_table.setItem(row, 8, QTableWidgetItem("-"))
    
    def update_statistics(self, alerts):
        """更新统计信息"""
        total = len(alerts)
        active = sum(1 for a in alerts if a.get('status') == 'active')
        env = sum(1 for a in alerts if a.get('alert_category') == 'environment')
        person = sum(1 for a in alerts if a.get('alert_category') == 'personnel')
        
        self.total_label.setText(f"总报警数: {total}")
        self.active_label.setText(f"未处理: {active}")
        self.env_label.setText(f"环境安全: {env}")
        self.person_label.setText(f"人员安全: {person}")
    
    def on_filter_changed(self):
        """筛选条件改变时重新加载"""
        self.current_page = 1
        filtered = self.filter_alerts(self.all_alerts)
        self.display_alerts(filtered)
    
    def reset_filters(self):
        """重置筛选条件"""
        self.category_combo.setCurrentIndex(0)
        self.level_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.search_input.clear()
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.end_date.setDate(QDate.currentDate())
        self.load_alerts()
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            filtered = self.filter_alerts(self.all_alerts)
            self.display_alerts(filtered)
    
    def next_page(self):
        """下一页"""
        filtered = self.filter_alerts(self.all_alerts)
        page_size_text = self.page_size_combo.currentText()
        if page_size_text == "全部":
            return
        page_size = int(page_size_text)
        total_pages = (len(filtered) + page_size - 1) // page_size
        
        if self.current_page < total_pages:
            self.current_page += 1
            self.display_alerts(filtered)
    
    def resolve_alert(self, alert_id):
        """处理单个报警"""
        try:
            current_user = self.auth_manager.current_user
            resolved_by = current_user.get('username') if current_user else 'admin'
            
            result = self.alert_repo.resolve_alert(alert_id, resolved_by)
            
            if result['success']:
                QMessageBox.information(self, "成功", "报警已标记为已处理")
                self.alert_resolved.emit(alert_id)
                self.load_alerts()
            else:
                QMessageBox.warning(self, "失败", result.get('message', '处理失败'))
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理报警失败: {str(e)}")
    
    def resolve_selected_alert(self):
        """处理选中的报警"""
        selected_row = self.alert_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条报警记录")
            return
        
        alert_id = int(self.alert_table.item(selected_row, 0).text())
        self.resolve_alert(alert_id)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        row = self.alert_table.rowAt(position.y())
        if row < 0:
            return
        
        self.alert_table.selectRow(row)
        
        menu = QMenu()
        
        view_action = QAction("查看详情", self)
        view_action.triggered.connect(lambda: self.view_alert_detail(row))
        menu.addAction(view_action)
        
        menu.addSeparator()
        
        status = self.alert_table.item(row, 5).text()
        if status == "未处理":
            resolve_action = QAction("标记为已处理", self)
            resolve_action.triggered.connect(self.resolve_selected_alert)
            menu.addAction(resolve_action)
        
        menu.exec_(self.alert_table.viewport().mapToGlobal(position))
    
    def view_alert_detail(self, row):
        """查看报警详情"""
        alert_id = int(self.alert_table.item(row, 0).text())
        
        # 查找报警详情
        alert = None
        for a in self.all_alerts:
            if a.get('id') == alert_id:
                alert = a
                break
        
        if not alert:
            return
        
        # 构建详情文本
        detail_text = f"""
        <h3>报警详情</h3>
        <table>
        <tr><td><b>报警ID:</b></td><td>{alert.get('id')}</td></tr>
        <tr><td><b>报警时间:</b></td><td>{alert.get('created_at')}</td></tr>
        <tr><td><b>报警类别:</b></td><td>{alert.get('alert_category')}</td></tr>
        <tr><td><b>报警类型:</b></td><td>{alert.get('alert_type')}</td></tr>
        <tr><td><b>报警级别:</b></td><td>{alert.get('alert_level')}级</td></tr>
        <tr><td><b>处理状态:</b></td><td>{alert.get('status')}</td></tr>
        <tr><td><b>报警消息:</b></td><td>{alert.get('alert_message')}</td></tr>
        </table>
        """
        
        # 检测对象详情
        detected_objects = alert.get('detected_objects')
        if detected_objects:
            if isinstance(detected_objects, str):
                try:
                    detected_objects = json.loads(detected_objects)
                except:
                    detected_objects = {}
            detail_text += "<h4>检测对象:</h4><ul>"
            for key, value in detected_objects.items():
                detail_text += f"<li>{key}: {value}</li>"
            detail_text += "</ul>"
        
        # 温度数据
        temperature_data = alert.get('temperature_data')
        if temperature_data:
            if isinstance(temperature_data, str):
                try:
                    temperature_data = json.loads(temperature_data)
                except:
                    temperature_data = None
            if temperature_data:
                detail_text += f"<h4>温度数据:</h4><p>{temperature_data}</p>"
        
        # 处理信息
        if alert.get('resolved_at'):
            detail_text += f"""
            <h4>处理信息:</h4>
            <table>
            <tr><td><b>处理时间:</b></td><td>{alert.get('resolved_at')}</td></tr>
            <tr><td><b>处理人:</b></td><td>{alert.get('resolved_by')}</td></tr>
            </table>
            """
        
        QMessageBox.information(self, "报警详情", detail_text)
    
    def toggle_auto_refresh(self):
        """切换自动刷新"""
        if self.auto_refresh_checkbox.isChecked():
            self.refresh_timer.start(30000)
            self.auto_refresh_checkbox.setText("🔄 自动刷新: 开")
        else:
            self.refresh_timer.stop()
            self.auto_refresh_checkbox.setText("🔄 自动刷新: 关")
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止定时器
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlertViewWindow()
    window.show()
    sys.exit(app.exec_())
