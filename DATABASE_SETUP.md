# 数据库环境迁移与初始化指南

## 概述

本文档详细说明如何将项目迁移到新环境后，正确建立数据库和数据表结构。

---

## 一、环境准备

### 1.1 安装 MySQL

**Windows 安装步骤：**

1. 下载 MySQL Installer：https://dev.mysql.com/downloads/installer/
2. 选择 "Server only" 或 "Full" 安装类型
3. 记住设置的 root 密码（建议设置为 `123456` 以匹配项目配置）
4. 确保 MySQL 服务已启动

**验证安装：**
```bash
# 打开命令提示符或 PowerShell
mysql --version

# 登录 MySQL
mysql -u root -p
# 输入密码: 123456
```

### 1.2 安装 Python 依赖

```bash
# 在项目根目录执行
pip install -r requirements.txt

# 或单独安装数据库相关依赖
pip install PyMySQL cryptography
```

---

## 二、数据库配置

### 2.1 修改数据库配置（如需要）

如果 MySQL 配置与项目默认配置不同，修改 `database.py`：

```python
class DatabaseConfig:
    """数据库配置类"""
    HOST = 'localhost'      # 数据库主机地址
    PORT = 3306            # 数据库端口
    USER = 'root'          # 数据库用户名
    PASSWORD = '123456'    # 数据库密码（修改为你的密码）
    DATABASE = 'factory_safety'  # 数据库名称
    CHARSET = 'utf8mb4'    # 字符集
```

### 2.2 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| HOST | localhost | 数据库服务器地址，本地开发保持 localhost |
| PORT | 3306 | MySQL 默认端口 |
| USER | root | MySQL 管理员账号 |
| PASSWORD | 123456 | root 用户密码 |
| DATABASE | factory_safety | 项目数据库名称 |
| CHARSET | utf8mb4 | 支持中文和特殊字符 |

---

## 三、自动初始化（推荐）

### 3.1 运行初始化脚本

项目提供了自动初始化脚本 `init_database.py`，会完成以下操作：

1. 连接 MySQL 服务器
2. 创建数据库 `factory_safety`
3. 创建数据表（users, login_logs, alerts）
4. 创建默认管理员账户

**执行命令：**
```bash
# 在项目根目录执行
python init_database.py
```

**预期输出：**
```
==================================================
工厂安全监控系统 - 数据库初始化工具
==================================================

✓ 成功连接到MySQL服务器 (localhost:3306)
✓ 数据库 'factory_safety' 已创建或已存在
✓ 用户表 'users' 已创建或已存在
✓ 登录日志表 'login_logs' 已创建或已存在
✓ 报警记录表 'alerts' 已创建或已存在
✓ 默认管理员账户已创建
  用户名: admin
  密码: admin123

✓ 数据库初始化完成！

==================================================
数据库初始化成功！
==================================================

按回车键退出...
```

---

## 四、手动初始化（备选）

如果自动初始化失败，可以手动执行 SQL 语句。

### 4.1 登录 MySQL

```bash
mysql -u root -p
# 输入密码
```

### 4.2 创建数据库

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS factory_safety 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE factory_safety;
```

### 4.3 创建用户表

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
```

### 4.4 创建登录日志表

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登录日志表';
```

### 4.5 创建报警记录表

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报警记录表';
```

### 4.6 创建默认管理员账户

```sql
-- 注意：密码需要通过 Python 代码生成哈希值
-- 以下仅为示例，实际应使用 init_database.py 创建

-- 或者直接运行 init_database.py 的创建用户部分
```

---

## 五、验证数据库

### 5.1 检查数据库是否存在

```sql
SHOW DATABASES LIKE 'factory_safety';
```

### 5.2 检查数据表

```sql
USE factory_safety;
SHOW TABLES;
```

**预期输出：**
```
+--------------------------+
| Tables_in_factory_safety |
+--------------------------+
| alerts                   |
| login_logs               |
| users                    |
+--------------------------+
```

### 5.3 检查表结构

```sql
DESCRIBE users;
DESCRIBE login_logs;
DESCRIBE alerts;
```

### 5.4 验证 Python 连接

```bash
# 在项目根目录执行
python -c "from database import DatabaseManager; db = DatabaseManager(); print('连接成功')"
```

---

## 六、常见问题

### 6.1 连接被拒绝

**错误信息：**
```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on 'localhost' (...)")
```

**解决方案：**
1. 检查 MySQL 服务是否启动
   ```bash
   # Windows
   net start MySQL80
   
   # 或在服务管理器中启动 MySQL 服务
   ```

2. 检查端口是否正确
   ```bash
   # 查看 MySQL 端口
   mysql -u root -p -e "SHOW VARIABLES LIKE 'port';"
   ```

### 6.2 认证失败

**错误信息：**
```
pymysql.err.OperationalError: (1045, "Access denied for user 'root'@'localhost' (...)")
```

**解决方案：**
1. 确认密码正确
2. 重置 root 密码（如忘记）
3. 检查 database.py 中的密码配置

### 6.3 数据库已存在

**错误信息：**
```
数据库 'factory_safety' 已存在
```

**说明：**这是正常提示，不是错误。脚本会自动跳过已存在的数据库。

### 6.4 表已存在

**说明：**脚本使用 `CREATE TABLE IF NOT EXISTS`，不会重复创建表。

### 6.5 字符集问题

**错误信息：**
```
Incorrect string value: '\xE7\x94\xA8\xE6\x88\xB7' for column 'username'
```

**解决方案：**
确保数据库和表使用 `utf8mb4` 字符集：
```sql
ALTER DATABASE factory_safety CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## 七、数据备份与恢复

### 7.1 备份数据库

```bash
# 使用 mysqldump 备份
mysqldump -u root -p factory_safety > backup_$(date +%Y%m%d).sql
```

### 7.2 恢复数据库

```bash
# 恢复数据
mysql -u root -p factory_safety < backup_20240101.sql
```

---

## 八、数据库维护

### 8.1 清理旧数据

```sql
-- 清理 30 天前的报警记录
DELETE FROM alerts WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 清理 90 天前的登录日志
DELETE FROM login_logs WHERE login_time < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### 8.2 查看统计信息

```sql
-- 用户数量
SELECT COUNT(*) as total_users FROM users;

-- 报警统计
SELECT alert_type, COUNT(*) as count FROM alerts GROUP BY alert_type;

-- 今日报警
SELECT COUNT(*) as today_alerts FROM alerts 
WHERE DATE(created_at) = CURDATE();
```

---

## 九、更新数据库结构

如果项目升级需要修改表结构：

### 9.1 添加新字段

```sql
ALTER TABLE users ADD COLUMN department VARCHAR(50) COMMENT '部门';
```

### 9.2 修改字段

```sql
ALTER TABLE alerts MODIFY COLUMN alert_message VARCHAR(500);
```

### 9.3 添加索引

```sql
CREATE INDEX idx_department ON users(department);
```

---

## 十、总结

### 快速开始清单

- [ ] 安装 MySQL 8.0+
- [ ] 记住 root 密码（建议 123456）
- [ ] 安装 Python 依赖 `pip install -r requirements.txt`
- [ ] 运行 `python init_database.py`
- [ ] 验证数据库连接
- [ ] 运行主程序 `python main.py`
- [ ] 使用默认账户登录（admin / admin123）

### 关键文件

| 文件 | 用途 |
|------|------|
| `database.py` | 数据库连接配置和操作类 |
| `init_database.py` | 数据库初始化脚本 |
| `DATABASE_SETUP.md` | 本指南文档 |

---

## 附录：SQL 速查

```sql
-- 查看所有用户
SELECT id, username, email, role, status, created_at FROM users;

-- 查看最近报警
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;

-- 查看活跃报警
SELECT * FROM alerts WHERE status = 'active';

-- 统计报警类型
SELECT alert_type, alert_category, COUNT(*) as count 
FROM alerts 
GROUP BY alert_type, alert_category;

-- 重置用户密码（需要 Python 生成哈希）
-- 建议通过应用界面修改密码
```
