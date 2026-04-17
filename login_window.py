"""
登录注册窗口模块
实现用户登录和注册界面
遵循高内聚低耦合原则
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QStackedWidget, QFrame,
    QMessageBox, QCheckBox, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from auth_manager import (
    get_auth_manager, validate_username, validate_password, validate_email
)


class StyledLineEdit(QLineEdit):
    """自定义样式的输入框"""
    
    def __init__(self, placeholder_text="", is_password=False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        if is_password:
            self.setEchoMode(QLineEdit.Password)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #FAFAFA;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border: 2px solid #BDBDBD;
            }
        """)


class StyledButton(QPushButton):
    """自定义样式的按钮"""
    
    def __init__(self, text, is_primary=True, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        
        if is_primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4285F4;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px 24px;
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
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #4285F4;
                    border: 2px solid #4285F4;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                }
                QPushButton:pressed {
                    background-color: #BBDEFB;
                }
            """)


class LoginPage(QWidget):
    """登录页面"""
    
    # 信号定义
    login_success = pyqtSignal(dict)  # 登录成功信号，传递用户信息
    switch_to_register = pyqtSignal()  # 切换到注册页面信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_manager = get_auth_manager()
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # 标题
        title_label = QLabel("欢迎回来")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("请登录您的账户")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #757575;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # 用户名输入
        username_layout = QVBoxLayout()
        username_layout.setSpacing(5)
        username_label = QLabel("用户名")
        username_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        username_layout.addWidget(username_label)
        self.username_input = StyledLineEdit("请输入用户名")
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # 密码输入
        password_layout = QVBoxLayout()
        password_layout.setSpacing(5)
        password_label = QLabel("密码")
        password_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        password_layout.addWidget(password_label)
        self.password_input = StyledLineEdit("请输入密码", is_password=True)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # 记住我和忘记密码
        options_layout = QHBoxLayout()
        self.remember_checkbox = QCheckBox("记住我")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: #666666;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        options_layout.addWidget(self.remember_checkbox)
        options_layout.addStretch()
        
        # 忘记密码按钮
        forgot_btn = QPushButton("忘记密码?")
        forgot_btn.setFlat(True)
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.setStyleSheet("""
            QPushButton {
                color: #4285F4;
                font-size: 13px;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                color: #3367D6;
                text-decoration: underline;
            }
        """)
        forgot_btn.clicked.connect(self.on_forgot_password)
        options_layout.addWidget(forgot_btn)
        layout.addLayout(options_layout)
        
        # 登录按钮
        self.login_btn = StyledButton("登 录", is_primary=True)
        self.login_btn.clicked.connect(self.on_login)
        layout.addWidget(self.login_btn)
        
        # 注册提示
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignCenter)
        
        no_account_label = QLabel("还没有账户?")
        no_account_label.setStyleSheet("color: #666666; font-size: 13px;")
        register_layout.addWidget(no_account_label)
        
        register_btn = QPushButton("立即注册")
        register_btn.setFlat(True)
        register_btn.setCursor(Qt.PointingHandCursor)
        register_btn.setStyleSheet("""
            QPushButton {
                color: #4285F4;
                font-size: 13px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                color: #3367D6;
                text-decoration: underline;
            }
        """)
        register_btn.clicked.connect(self.switch_to_register.emit)
        register_layout.addWidget(register_btn)
        
        layout.addLayout(register_layout)
        layout.addStretch()
    
    def on_login(self):
        """处理登录"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # 验证输入
        if not username:
            QMessageBox.warning(self, "输入错误", "请输入用户名")
            self.username_input.setFocus()
            return
        
        if not password:
            QMessageBox.warning(self, "输入错误", "请输入密码")
            self.password_input.setFocus()
            return
        
        # 禁用登录按钮，防止重复点击
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        
        # 执行登录
        result = self.auth_manager.login(username, password)
        
        # 恢复按钮状态
        self.login_btn.setEnabled(True)
        self.login_btn.setText("登 录")
        
        if result['success']:
            # 先发射信号，让主程序处理跳转
            user_info = result['user']
            self.login_success.emit(user_info)
            # 注意：不要在这里清空输入或显示消息框，因为窗口即将被关闭
        else:
            QMessageBox.warning(self, "登录失败", result['message'])
    
    def on_forgot_password(self):
        """处理忘记密码"""
        QMessageBox.information(
            self, 
            "忘记密码", 
            "请联系系统管理员重置密码。\n管理员邮箱: admin@factory.com"
        )
    
    def clear_inputs(self):
        """清空输入框"""
        self.username_input.clear()
        self.password_input.clear()
        self.remember_checkbox.setChecked(False)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.on_login()
        else:
            super().keyPressEvent(event)


class RegisterPage(QWidget):
    """注册页面"""
    
    # 信号定义
    register_success = pyqtSignal()  # 注册成功信号
    switch_to_login = pyqtSignal()  # 切换到登录页面信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_manager = get_auth_manager()
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # 标题
        title_label = QLabel("创建账户")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("填写以下信息完成注册")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #757575;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # 用户名输入
        username_layout = QVBoxLayout()
        username_layout.setSpacing(5)
        username_label = QLabel("用户名 *")
        username_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        username_layout.addWidget(username_label)
        self.username_input = StyledLineEdit("请输入用户名（3-50个字符）")
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # 密码输入
        password_layout = QVBoxLayout()
        password_layout.setSpacing(5)
        password_label = QLabel("密码 *")
        password_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        password_layout.addWidget(password_label)
        self.password_input = StyledLineEdit("请输入密码（至少6个字符）", is_password=True)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # 确认密码
        confirm_layout = QVBoxLayout()
        confirm_layout.setSpacing(5)
        confirm_label = QLabel("确认密码 *")
        confirm_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        confirm_layout.addWidget(confirm_label)
        self.confirm_input = StyledLineEdit("请再次输入密码", is_password=True)
        confirm_layout.addWidget(self.confirm_input)
        layout.addLayout(confirm_layout)
        
        # 邮箱输入
        email_layout = QVBoxLayout()
        email_layout.setSpacing(5)
        email_label = QLabel("邮箱（可选）")
        email_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        email_layout.addWidget(email_label)
        self.email_input = StyledLineEdit("请输入邮箱地址")
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)
        
        # 手机号输入
        phone_layout = QVBoxLayout()
        phone_layout.setSpacing(5)
        phone_label = QLabel("手机号（可选）")
        phone_label.setStyleSheet("font-size: 13px; color: #555555; font-weight: bold;")
        phone_layout.addWidget(phone_label)
        self.phone_input = StyledLineEdit("请输入手机号码")
        phone_layout.addWidget(self.phone_input)
        layout.addLayout(phone_layout)
        
        # 注册按钮
        self.register_btn = StyledButton("注 册", is_primary=True)
        self.register_btn.clicked.connect(self.on_register)
        layout.addWidget(self.register_btn)
        
        # 登录提示
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignCenter)
        
        has_account_label = QLabel("已有账户?")
        has_account_label.setStyleSheet("color: #666666; font-size: 13px;")
        login_layout.addWidget(has_account_label)
        
        login_btn = QPushButton("立即登录")
        login_btn.setFlat(True)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                color: #4285F4;
                font-size: 13px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                color: #3367D6;
                text-decoration: underline;
            }
        """)
        login_btn.clicked.connect(self.switch_to_login.emit)
        login_layout.addWidget(login_btn)
        
        layout.addLayout(login_layout)
        layout.addStretch()
    
    def on_register(self):
        """处理注册"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_input.text()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        
        # 验证用户名
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            self.username_input.setFocus()
            return
        
        # 验证密码
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            self.password_input.setFocus()
            return
        
        # 验证确认密码
        if password != confirm_password:
            QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
            self.confirm_input.setFocus()
            return
        
        # 验证邮箱
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            self.email_input.setFocus()
            return
        
        # 禁用注册按钮，防止重复点击
        self.register_btn.setEnabled(False)
        self.register_btn.setText("注册中...")
        
        # 执行注册
        result = self.auth_manager.register(
            username=username,
            password=password,
            email=email if email else None,
            phone=phone if phone else None
        )
        
        # 恢复按钮状态
        self.register_btn.setEnabled(True)
        self.register_btn.setText("注 册")
        
        if result['success']:
            QMessageBox.information(self, "注册成功", result['message'])
            self.register_success.emit()
            self.clear_inputs()
        else:
            QMessageBox.warning(self, "注册失败", result['message'])
    
    def clear_inputs(self):
        """清空输入框"""
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.email_input.clear()
        self.phone_input.clear()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.on_register()
        else:
            super().keyPressEvent(event)


class LoginWindow(QMainWindow):
    """
    登录注册主窗口
    包含登录和注册两个页面的切换
    """
    
    # 信号定义
    login_success = pyqtSignal(dict)  # 登录成功信号，传递用户信息
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("工厂安全监控系统 - 登录")
        self.setMinimumSize(450, 600)
        self.setMaximumSize(500, 700)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F7FA;
            }
        """)
        
        # 初始化UI
        self.init_ui()
        
        # 窗口居中显示
        self.center_window()
    
    def init_ui(self):
        """初始化界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建卡片容器
        card = QFrame()
        card.setMinimumWidth(400)
        card.setMaximumWidth(450)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        
        # 卡片布局
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # 创建堆叠部件用于切换登录和注册页面
        self.stacked_widget = QStackedWidget()
        
        # 创建登录页面
        self.login_page = LoginPage()
        self.login_page.login_success.connect(self.on_login_success)
        self.login_page.switch_to_register.connect(self.show_register_page)
        
        # 创建注册页面
        self.register_page = RegisterPage()
        self.register_page.register_success.connect(self.show_login_page)
        self.register_page.switch_to_login.connect(self.show_login_page)
        
        # 添加页面到堆叠部件
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.register_page)
        
        card_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(card)
        
        # 底部版权信息
        copyright_label = QLabel("© 2024 工厂安全监控系统 v1.0")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 12px;
                margin-top: 20px;
            }
        """)
        main_layout.addWidget(copyright_label)
    
    def show_login_page(self):
        """显示登录页面"""
        self.stacked_widget.setCurrentIndex(0)
        self.setWindowTitle("工厂安全监控系统 - 登录")
    
    def show_register_page(self):
        """显示注册页面"""
        self.stacked_widget.setCurrentIndex(1)
        self.setWindowTitle("工厂安全监控系统 - 注册")
    
    def on_login_success(self, user_info: dict):
        """处理登录成功 - 转发信号到主程序"""
        print(f"[LoginWindow] 登录成功，转发信号: {user_info.get('username')}")
        self.login_success.emit(user_info)
    
    def center_window(self):
        """将窗口居中显示"""
        from PyQt5.QtWidgets import QDesktopWidget
        
        # 获取屏幕几何信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口几何信息
        size = self.geometry()
        # 计算居中位置
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 如果没有登录成功就关闭窗口，则退出应用程序
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "确定要退出程序吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                event.accept()
                QApplication.instance().quit()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = LoginWindow()
    window.show()
    
    sys.exit(app.exec_())
