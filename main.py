"""
工厂安全监控系统 - 主程序入口
整合登录注册功能和YOLO检测主界面
"""

import sys
import os

# 确保可以导入本地模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from login_window import LoginWindow
from yolo_detector_gui import YOLODetectorGUI
from auth_manager import get_auth_manager


class ApplicationManager:
    """
    应用程序管理器
    负责管理登录窗口和主窗口的生命周期
    """
    
    def __init__(self):
        self.app = None
        self.login_window = None
        self.main_window = None
        self.auth_manager = get_auth_manager()
    
    def run(self):
        """运行应用程序"""
        # 创建应用程序
        self.app = QApplication(sys.argv)
        
        # 设置应用程序属性
        self._setup_application()
        
        # 显示登录窗口
        self._show_login_window()
        
        # 运行应用程序
        sys.exit(self.app.exec_())
    
    def _setup_application(self):
        """设置应用程序属性"""
        # 设置全局字体
        font = QFont("Microsoft YaHei", 10)
        self.app.setFont(font)
        
        # 设置应用程序样式
        self.app.setStyle('Fusion')
        
        # 启用高DPI支持
        self.app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    def _show_login_window(self):
        """显示登录窗口"""
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self._on_login_success)
        self.login_window.show()
    
    def _on_login_success(self, user_info: dict):
        """登录成功后的处理"""
        print(f"[ApplicationManager] 接收到登录成功信号: {user_info.get('username')}")
        print(f"用户 '{user_info['username']}' 登录成功，正在启动主程序...")
        
        # 先显示主窗口
        self._show_main_window(user_info)
        
        # 再关闭登录窗口（避免Qt事件循环结束）
        if self.login_window:
            self.login_window.hide()  # 使用hide而不是close
            self.login_window.close()
            self.login_window = None
    
    def _show_main_window(self, user_info: dict):
        """显示主窗口"""
        print("[ApplicationManager] 正在创建主窗口...")
        try:
            self.main_window = YOLODetectorGUI()
            print("[ApplicationManager] 主窗口创建成功")
            
            # 更新窗口标题，显示当前登录用户
            self.main_window.setWindowTitle(
                f"YOLO 烟雾与火灾检测器 - 当前用户: {user_info['username']} ({user_info['role']})"
            )
            
            # 连接主窗口关闭事件
            self.main_window.closeEvent = self._on_main_window_close
            
            print("[ApplicationManager] 正在显示主窗口...")
            self.main_window.show()
            print("[ApplicationManager] 主窗口已显示")
        except Exception as e:
            print(f"[ApplicationManager] 创建主窗口失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _on_main_window_close(self, event):
        """主窗口关闭事件处理"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 询问用户是退出程序还是切换账户
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle("退出确认")
        msg_box.setText("您想要做什么？")
        msg_box.setIcon(QMessageBox.Question)
        
        exit_btn = msg_box.addButton("退出程序", QMessageBox.AcceptRole)
        logout_btn = msg_box.addButton("切换账户", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
        
        msg_box.exec_()
        
        clicked_btn = msg_box.clickedButton()
        
        if clicked_btn == exit_btn:
            # 退出程序
            self.auth_manager.logout()
            event.accept()
            
        elif clicked_btn == logout_btn:
            # 切换账户
            event.ignore()
            self.auth_manager.logout()
            self.main_window.close()
            self.main_window = None
            self._show_login_window()
            
        else:
            # 取消
            event.ignore()


def check_database_connection():
    """检查数据库连接是否正常"""
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
    except Exception as e:
        print(f"数据库连接失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("工厂安全监控系统")
    print("=" * 50)
    print()
    
    # 检查数据库连接
    print("正在检查数据库连接...")
    if not check_database_connection():
        print()
        print("✗ 无法连接到数据库，请检查：")
        print("  1. MySQL服务是否已启动")
        print("  2. 数据库配置是否正确（端口: 3306, 密码: 123456）")
        print("  3. 是否已运行 init_database.py 初始化数据库")
        print()
        print("按回车键退出...")
        input()
        return
    
    print("✓ 数据库连接成功")
    print()
    
    # 启动应用程序
    app_manager = ApplicationManager()
    app_manager.run()


if __name__ == "__main__":
    main()
