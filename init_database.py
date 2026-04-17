"""
数据库初始化脚本
用于创建factory_safety数据库和users表
"""

import pymysql
from database import DatabaseConfig


def init_database():
    """初始化数据库和表结构"""
    config = DatabaseConfig()
    
    # 第一步：连接MySQL服务器（不指定数据库）
    try:
        conn = pymysql.connect(
            host=config.HOST,
            port=config.PORT,
            user=config.USER,
            password=config.PASSWORD,
            charset=config.CHARSET
        )
        print(f"✓ 成功连接到MySQL服务器 ({config.HOST}:{config.PORT})")
    except pymysql.Error as e:
        print(f"✗ 连接MySQL服务器失败: {str(e)}")
        return False
    
    try:
        cursor = conn.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DATABASE} "
                      f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ 数据库 '{config.DATABASE}' 已创建或已存在")
        
        # 使用数据库
        cursor.execute(f"USE {config.DATABASE}")
        
        # 创建用户表
        create_users_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
            username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
            password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希值',
            salt VARCHAR(64) NOT NULL COMMENT '密码盐值',
            email VARCHAR(100) UNIQUE COMMENT '邮箱地址',
            phone VARCHAR(20) COMMENT '手机号码',
            role ENUM('admin', 'user', 'operator') DEFAULT 'user' COMMENT '用户角色',
            status ENUM('active', 'inactive', 'locked') DEFAULT 'active' COMMENT '账户状态',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            last_login TIMESTAMP NULL COMMENT '最后登录时间',
            INDEX idx_username (username),
            INDEX idx_email (email),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表'
        """
        cursor.execute(create_users_table_sql)
        print("✓ 用户表 'users' 已创建或已存在")
        
        # 创建登录日志表
        create_login_logs_table_sql = """
        CREATE TABLE IF NOT EXISTS login_logs (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
            user_id INT COMMENT '用户ID',
            username VARCHAR(50) COMMENT '用户名',
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
            login_ip VARCHAR(45) COMMENT '登录IP地址',
            login_status ENUM('success', 'failed') COMMENT '登录状态',
            fail_reason VARCHAR(255) COMMENT '失败原因',
            INDEX idx_user_id (user_id),
            INDEX idx_login_time (login_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登录日志表'
        """
        cursor.execute(create_login_logs_table_sql)
        print("✓ 登录日志表 'login_logs' 已创建或已存在")
        
        # 创建报警记录表
        create_alerts_table_sql = """
        CREATE TABLE IF NOT EXISTS alerts (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '报警ID',
            alert_type VARCHAR(50) NOT NULL COMMENT '报警类型（fire/smoke/temperature/helmet/vest）',
            alert_category ENUM('environment', 'personnel') NOT NULL COMMENT '报警类别（environment=环境安全/personnel=人员安全）',
            alert_level INT DEFAULT 0 COMMENT '报警级别（0=正常,1=一级,2=二级,3=三级）',
            alert_message TEXT COMMENT '报警详细信息',
            detected_objects JSON COMMENT '检测到的目标信息（JSON格式）',
            temperature_data JSON COMMENT '温度数据（JSON格式）',
            image_path VARCHAR(255) COMMENT '报警截图路径',
            status ENUM('active', 'resolved') DEFAULT 'active' COMMENT '报警状态',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '报警时间',
            resolved_at TIMESTAMP NULL COMMENT '处理时间',
            resolved_by VARCHAR(50) COMMENT '处理人',
            INDEX idx_alert_type (alert_type),
            INDEX idx_alert_category (alert_category),
            INDEX idx_alert_level (alert_level),
            INDEX idx_status (status),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报警记录表'
        """
        cursor.execute(create_alerts_table_sql)
        print("✓ 报警记录表 'alerts' 已创建或已存在")
        
        # 检查是否已存在管理员账户
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        result = cursor.fetchone()
        
        if result[0] == 0:
            # 创建默认管理员账户
            from database import UserRepository
            user_repo = UserRepository()
            
            admin_result = user_repo.create_user(
                username='admin',
                password='admin123',
                email='admin@factory.com',
                role='admin'
            )
            
            if admin_result['success']:
                print("✓ 默认管理员账户已创建")
                print("  用户名: admin")
                print("  密码: admin123")
            else:
                print(f"✗ 创建管理员账户失败: {admin_result['message']}")
        else:
            print("✓ 管理员账户已存在，跳过创建")
        
        conn.commit()
        print("\n✓ 数据库初始化完成！")
        return True
        
    except pymysql.Error as e:
        print(f"✗ 数据库操作失败: {str(e)}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"✗ 发生错误: {str(e)}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("工厂安全监控系统 - 数据库初始化工具")
    print("=" * 50)
    print()
    
    success = init_database()
    
    print()
    if success:
        print("=" * 50)
        print("数据库初始化成功！")
        print("=" * 50)
    else:
        print("=" * 50)
        print("数据库初始化失败，请检查配置后重试")
        print("=" * 50)
    
    input("\n按回车键退出...")
