"""
用户认证管理模块
处理用户登录状态管理和认证相关操作
遵循高内聚低耦合原则
"""

from typing import Optional, Dict, Any, Callable
from database import UserRepository, get_user_repository


class AuthManager:
    """
    认证管理器 - 单例模式
    管理当前登录用户的状态和认证信息
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._user_repository = get_user_repository()
        self._current_user: Optional[Dict[str, Any]] = None
        self._is_authenticated: bool = False
        self._auth_state_changed_callbacks: list = []
    
    # ========== 属性访问器 ==========
    
    @property
    def is_authenticated(self) -> bool:
        """是否已认证"""
        return self._is_authenticated
    
    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        """获取当前登录用户信息"""
        return self._current_user.copy() if self._current_user else None
    
    @property
    def username(self) -> Optional[str]:
        """获取当前用户名"""
        return self._current_user.get('username') if self._current_user else None
    
    @property
    def user_id(self) -> Optional[int]:
        """获取当前用户ID"""
        return self._current_user.get('id') if self._current_user else None
    
    @property
    def role(self) -> Optional[str]:
        """获取当前用户角色"""
        return self._current_user.get('role') if self._current_user else None
    
    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role == 'admin' if self._current_user else False
    
    # ========== 认证操作 ==========
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Dict: 包含登录结果的字典
        """
        result = self._user_repository.verify_user(username, password)
        
        if result['success']:
            self._current_user = result['user']
            self._is_authenticated = True
            self._notify_auth_state_changed(True)
        
        return result
    
    def logout(self):
        """用户登出"""
        self._current_user = None
        self._is_authenticated = False
        self._notify_auth_state_changed(False)
    
    def register(self, username: str, password: str, 
                 email: Optional[str] = None,
                 phone: Optional[str] = None,
                 role: str = 'user') -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱（可选）
            phone: 电话（可选）
            role: 角色，默认为'user'
            
        Returns:
            Dict: 包含注册结果的字典
        """
        return self._user_repository.create_user(
            username=username,
            password=password,
            email=email,
            phone=phone,
            role=role
        )
    
    def change_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            Dict: 包含操作结果的字典
        """
        return self._user_repository.update_password(user_id, new_password)
    
    # ========== 事件回调 ==========
    
    def add_auth_state_changed_listener(self, callback: Callable[[bool], None]):
        """
        添加认证状态变化监听器
        
        Args:
            callback: 回调函数，接收一个布尔参数表示是否已认证
        """
        if callback not in self._auth_state_changed_callbacks:
            self._auth_state_changed_callbacks.append(callback)
    
    def remove_auth_state_changed_listener(self, callback: Callable[[bool], None]):
        """移除认证状态变化监听器"""
        if callback in self._auth_state_changed_callbacks:
            self._auth_state_changed_callbacks.remove(callback)
    
    def _notify_auth_state_changed(self, is_authenticated: bool):
        """通知所有监听器认证状态变化"""
        for callback in self._auth_state_changed_callbacks:
            try:
                callback(is_authenticated)
            except Exception:
                pass  # 忽略回调中的错误
    
    # ========== 权限检查 ==========
    
    def check_permission(self, required_role: str) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            required_role: 所需角色
            
        Returns:
            bool: 是否有权限
        """
        if not self._is_authenticated:
            return False
        
        if required_role == 'user':
            return True  # 任何登录用户都有user权限
        elif required_role == 'admin':
            return self.is_admin
        elif required_role == 'operator':
            return self.role in ['admin', 'operator']
        
        return False
    
    def require_auth(self, func):
        """
        装饰器：要求登录才能访问
        
        用法:
            @auth_manager.require_auth
            def some_function():
                pass
        """
        def wrapper(*args, **kwargs):
            if not self._is_authenticated:
                raise PermissionError("需要登录才能执行此操作")
            return func(*args, **kwargs)
        return wrapper
    
    def require_admin(self, func):
        """
        装饰器：要求管理员权限才能访问
        
        用法:
            @auth_manager.require_admin
            def some_admin_function():
                pass
        """
        def wrapper(*args, **kwargs):
            if not self._is_authenticated:
                raise PermissionError("需要登录才能执行此操作")
            if not self.is_admin:
                raise PermissionError("需要管理员权限才能执行此操作")
            return func(*args, **kwargs)
        return wrapper


# ========== 便捷函数 ==========

def get_auth_manager() -> AuthManager:
    """获取认证管理器实例"""
    return AuthManager()


# 输入验证工具函数
def validate_username(username: str) -> tuple:
    """
    验证用户名有效性
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "用户名不能为空"
    
    if len(username) < 3:
        return False, "用户名长度至少为3个字符"
    
    if len(username) > 50:
        return False, "用户名长度不能超过50个字符"
    
    # 检查是否只包含允许的字符
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
    if not all(c in allowed_chars for c in username):
        return False, "用户名只能包含字母、数字、下划线和横线"
    
    return True, ""


def validate_password(password: str) -> tuple:
    """
    验证密码有效性
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "密码不能为空"
    
    if len(password) < 6:
        return False, "密码长度至少为6个字符"
    
    if len(password) > 128:
        return False, "密码长度不能超过128个字符"
    
    return True, ""


def validate_email(email: str) -> tuple:
    """
    验证邮箱有效性
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not email:
        return True, ""  # 邮箱可选
    
    if len(email) > 100:
        return False, "邮箱长度不能超过100个字符"
    
    # 简单的邮箱格式验证
    if '@' not in email or '.' not in email.split('@')[-1]:
        return False, "邮箱格式不正确"
    
    return True, ""
