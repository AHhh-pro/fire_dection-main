"""
数据库模块 - 处理MySQL连接和用户数据操作
遵循高内聚低耦合原则，将数据库操作封装在此模块中
"""

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import hashlib
import secrets
from typing import Optional, Dict, Any, List


class DatabaseConfig:
    """数据库配置类"""
    HOST = 'localhost'
    PORT = 3306
    USER = 'root'
    PASSWORD = '123456'
    DATABASE = 'factory_safety'
    CHARSET = 'utf8mb4'


class DatabaseManager:
    """数据库管理器 - 单例模式"""
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
        self._config = DatabaseConfig()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = pymysql.connect(
                host=self._config.HOST,
                port=self._config.PORT,
                user=self._config.USER,
                password=self._config.PASSWORD,
                database=self._config.DATABASE,
                charset=self._config.CHARSET,
                cursorclass=DictCursor
            )
            yield conn
        except pymysql.Error as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()


class UserRepository:
    """用户数据仓库 - 处理用户相关的数据库操作"""
    
    def __init__(self):
        self._db = DatabaseManager()
    
    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """
        对密码进行哈希处理
        
        Args:
            password: 原始密码
            salt: 盐值，如果为None则生成新的盐值
            
        Returns:
            tuple: (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )
        return hashed.hex(), salt
    
    def create_user(self, username: str, password: str, email: Optional[str] = None,
                   phone: Optional[str] = None, role: str = 'user') -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱（可选）
            phone: 电话（可选）
            role: 角色，默认为'user'
            
        Returns:
            Dict: 包含操作结果的字典
        """
        try:
            # 检查用户名是否已存在
            if self.get_user_by_username(username):
                return {'success': False, 'message': '用户名已存在'}
            
            # 检查邮箱是否已存在
            if email and self.get_user_by_email(email):
                return {'success': False, 'message': '邮箱已被注册'}
            
            # 哈希密码
            hashed_password, salt = self._hash_password(password)
            
            with self._db.get_cursor() as cursor:
                sql = """
                    INSERT INTO users (username, password_hash, salt, email, phone, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active')
                """
                cursor.execute(sql, (username, hashed_password, salt, email, phone, role))
                
                # 获取新创建用户的ID
                user_id = cursor.lastrowid
                
                return {
                    'success': True,
                    'message': '用户创建成功',
                    'user_id': user_id,
                    'username': username
                }
                
        except pymysql.Error as e:
            return {'success': False, 'message': f'数据库错误: {str(e)}'}
        except Exception as e:
            return {'success': False, 'message': f'系统错误: {str(e)}'}
    
    def verify_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        验证用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Dict: 包含验证结果的字典
        """
        try:
            user = self.get_user_by_username(username)
            
            if not user:
                return {'success': False, 'message': '用户名或密码错误'}
            
            # 检查用户状态
            if user.get('status') != 'active':
                return {'success': False, 'message': '账户已被禁用'}
            
            # 验证密码
            salt = user.get('salt', '')
            hashed_password, _ = self._hash_password(password, salt)
            
            if hashed_password != user.get('password_hash'):
                return {'success': False, 'message': '用户名或密码错误'}
            
            # 更新最后登录时间
            self._update_last_login(user['id'])
            
            return {
                'success': True,
                'message': '登录成功',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'role': user.get('role', 'user'),
                    'created_at': user.get('created_at')
                }
            }
            
        except pymysql.Error as e:
            return {'success': False, 'message': f'数据库错误: {str(e)}'}
        except Exception as e:
            return {'success': False, 'message': f'系统错误: {str(e)}'}
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名获取用户信息"""
        try:
            with self._db.get_cursor() as cursor:
                sql = "SELECT * FROM users WHERE username = %s"
                cursor.execute(sql, (username,))
                return cursor.fetchone()
        except Exception:
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """根据邮箱获取用户信息"""
        try:
            with self._db.get_cursor() as cursor:
                sql = "SELECT * FROM users WHERE email = %s"
                cursor.execute(sql, (email,))
                return cursor.fetchone()
        except Exception:
            return None
    
    def _update_last_login(self, user_id: int):
        """更新用户最后登录时间"""
        try:
            with self._db.get_cursor() as cursor:
                sql = "UPDATE users SET last_login = NOW() WHERE id = %s"
                cursor.execute(sql, (user_id,))
        except Exception:
            pass  # 登录时间更新失败不影响登录流程
    
    def update_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """更新用户密码"""
        try:
            hashed_password, salt = self._hash_password(new_password)
            
            with self._db.get_cursor() as cursor:
                sql = "UPDATE users SET password_hash = %s, salt = %s, updated_at = NOW() WHERE id = %s"
                cursor.execute(sql, (hashed_password, salt, user_id))
                
                if cursor.rowcount > 0:
                    return {'success': True, 'message': '密码更新成功'}
                else:
                    return {'success': False, 'message': '用户不存在'}
                    
        except Exception as e:
            return {'success': False, 'message': f'更新失败: {str(e)}'}
    
    def get_all_users(self) -> List[Dict]:
        """获取所有用户列表（不包含敏感信息）"""
        try:
            with self._db.get_cursor() as cursor:
                sql = """
                    SELECT id, username, email, phone, role, status, 
                           created_at, last_login
                    FROM users
                    ORDER BY created_at DESC
                """
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception:
            return []


class AlertRepository:
    """报警数据仓库 - 处理报警相关的数据库操作"""
    
    def __init__(self):
        self._db = DatabaseManager()
    
    def create_alert(self, alert_type: str, alert_category: str, alert_level: int,
                     alert_message: str, detected_objects: dict = None,
                     temperature_data: dict = None, image_path: str = None) -> Dict[str, Any]:
        """
        创建新的报警记录
        
        Args:
            alert_type: 报警类型（fire/smoke/temperature/helmet/vest等）
            alert_category: 报警类别（environment/personnel）
            alert_level: 报警级别（0-3，0=正常，3=最高）
            alert_message: 报警详细信息
            detected_objects: 检测到的目标信息（JSON格式）
            temperature_data: 温度数据（JSON格式）
            image_path: 报警截图路径
            
        Returns:
            Dict: 包含操作结果的字典
        """
        try:
            with self._db.get_cursor() as cursor:
                sql = """
                    INSERT INTO alerts 
                    (alert_type, alert_category, alert_level, alert_message, 
                     detected_objects, temperature_data, image_path, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                """
                import json
                cursor.execute(sql, (
                    alert_type,
                    alert_category,
                    alert_level,
                    alert_message,
                    json.dumps(detected_objects) if detected_objects else None,
                    json.dumps(temperature_data) if temperature_data else None,
                    image_path
                ))
                
                alert_id = cursor.lastrowid
                
                return {
                    'success': True,
                    'message': '报警记录创建成功',
                    'alert_id': alert_id
                }
                
        except Exception as e:
            return {'success': False, 'message': f'创建报警记录失败: {str(e)}'}
    
    def get_active_alerts(self) -> List[Dict]:
        """获取所有未处理的报警"""
        try:
            with self._db.get_cursor() as cursor:
                sql = """
                    SELECT * FROM alerts 
                    WHERE status = 'active'
                    ORDER BY alert_level DESC, created_at DESC
                """
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception:
            return []
    
    def get_alerts_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """获取指定日期范围内的报警"""
        try:
            with self._db.get_cursor() as cursor:
                sql = """
                    SELECT * FROM alerts 
                    WHERE created_at BETWEEN %s AND %s
                    ORDER BY created_at DESC
                """
                cursor.execute(sql, (start_date, end_date))
                return cursor.fetchall()
        except Exception:
            return []
    
    def resolve_alert(self, alert_id: int, resolved_by: str = None) -> Dict[str, Any]:
        """
        处理（解决）报警
        
        Args:
            alert_id: 报警ID
            resolved_by: 处理人
            
        Returns:
            Dict: 包含操作结果的字典
        """
        try:
            with self._db.get_cursor() as cursor:
                sql = """
                    UPDATE alerts 
                    SET status = 'resolved', 
                        resolved_at = NOW(),
                        resolved_by = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (resolved_by, alert_id))
                
                if cursor.rowcount > 0:
                    return {'success': True, 'message': '报警已处理'}
                else:
                    return {'success': False, 'message': '报警不存在'}
                    
        except Exception as e:
            return {'success': False, 'message': f'处理报警失败: {str(e)}'}
    
    def get_alert_statistics(self, days: int = 7) -> Dict:
        """获取报警统计数据"""
        try:
            with self._db.get_cursor() as cursor:
                # 按类别统计
                sql_category = """
                    SELECT alert_category, COUNT(*) as count
                    FROM alerts
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    GROUP BY alert_category
                """
                cursor.execute(sql_category, (days,))
                category_stats = cursor.fetchall()
                
                # 按级别统计
                sql_level = """
                    SELECT alert_level, COUNT(*) as count
                    FROM alerts
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    GROUP BY alert_level
                """
                cursor.execute(sql_level, (days,))
                level_stats = cursor.fetchall()
                
                return {
                    'success': True,
                    'category_stats': category_stats,
                    'level_stats': level_stats
                }
                
        except Exception as e:
            return {'success': False, 'message': str(e)}


# 便捷函数，供外部直接调用
def get_user_repository() -> UserRepository:
    """获取用户仓库实例"""
    return UserRepository()


def get_alert_repository() -> AlertRepository:
    """获取报警仓库实例"""
    return AlertRepository()
