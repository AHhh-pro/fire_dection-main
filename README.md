# 工厂安全监控系统 - 完整使用与开发指南

---

## 第一部分：功能介绍与操作方法

### 一、系统概述

工厂安全监控系统是一个基于 YOLOv8 深度学习框架的智能安全监控平台，能够实时检测工厂环境中的安全隐患。

#### 1.1 核心功能

| 功能模块 | 功能描述 | 检测目标 |
|---------|---------|---------|
| **烟雾火灾检测** | 检测视频/图像中的烟雾和明火 | smoke（烟雾）、fire（明火） |
| **人员安全检测** | 检测人员是否佩戴安全装备 | person（人员）、helmet（安全帽）、vest（反光背心）、glove（手套） |
| **温度监控** | 接收并显示温度传感器数据 | 温度数值 |
| **用户认证** | 登录注册、权限管理 | 用户账户 |
| **报警管理** | 分级分类报警、报警记录存储 | 各类报警信息 |

#### 1.2 报警分类体系

**A. 生产环境安全报警**
- 火警报警（三级）
- 高温报警（三级）

**B. 生产人员安全报警**
- 安全帽佩戴检测
- 反光背心穿戴检测
- 手套佩戴检测

---

### 二、安装与运行

#### 2.1 环境准备

**步骤1：安装MySQL数据库**
1. 下载MySQL Installer（https://dev.mysql.com/downloads/installer/）
2. 安装时选择"Server only"
3. 设置root密码为：`123456`
4. 确保MySQL服务已启动

**步骤2：安装Python依赖**
```bash
pip install -r requirements.txt
```

**步骤3：初始化数据库**
```bash
python init_database.py
```

此脚本会：
- 创建数据库 `factory_safety`
- 创建用户表 `users`
- 创建报警表 `alerts`
- 创建登录日志表 `login_logs`
- 创建默认管理员账户（用户名：admin，密码：admin123）

#### 2.2 启动程序

```bash
python main.py
```

#### 2.3 登录系统

- 使用默认管理员账户登录：
  - 用户名：`admin`
  - 密码：`admin123`
- 或点击"注册账户"创建新用户

---

### 三、界面操作指南

#### 3.1 主界面布局

```
┌─────────────────────────────────────────────────────────┐
│  菜单栏（文件、视图、帮助）                               │
├──────────────────┬──────────────────────────────────────┤
│   左侧面板        │           中央显示区                  │
│  ├─输入源选择     │           ├─图像/视频显示             │
│  ├─模型设置       │           └─信息面板                  │
│  ├─生产人员安全   │                                      │
│  ├─检测控制       │                                      │
│  ├─检测统计       │                                      │
│  ├─安全警报       │                                      │
│  └─区域温度       │                                      │
└──────────────────┴──────────────────────────────────────┘
```

#### 3.2 各功能区域说明

**输入源选择**
- 摄像头：使用本地摄像头进行实时检测
- 视频文件：选择本地视频文件进行检测
- 图片文件：选择单张图片进行检测

**模型设置**
- 模型选择：切换不同的YOLO模型
- 置信度：调整检测阈值（0.1-1.0）

**生产人员安全（复选框设置）**
- ☑️ **安全帽**（默认勾选）- 检测是否佩戴安全帽
- ☑️ **反光背心**（默认勾选）- 检测是否穿戴反光背心
- ☐ **手套**（默认不勾选）- 检测是否佩戴手套

**重要：只有勾选的项目才会进行检测和报警！**

**检测控制**
- 开始检测：启动检测流程
- 停止检测：停止当前检测

**检测统计**
显示当前帧检测到的各类目标数量

**安全警报**
- 生产环境安全：显示火警、高温报警状态
- 生产人员安全：显示人员安全装备报警状态

**区域温度**
显示从HTTP服务器接收的温度数据

---

### 四、报警系统详解

#### 4.1 火警报警

**检测目标：**
- `fire`（明火/火焰）
- `smoke`（烟雾）

**报警级别规则：**

| 检测情况 | 报警级别 | 报警消息 | 颜色 |
|---------|---------|---------|------|
| 同时检测到明火和烟雾 | 3级（最高） | "火警三级：检测到明火和烟雾" | 红色 |
| 仅检测到明火 | 2级 | "火警二级：检测到明火" | 橙色 |
| 仅检测到烟雾 | 1级 | "火警一级：检测到烟雾" | 黄色 |
| 均未检测到 | 0级（安全） | "生产环境安全" | 绿色 |

**判断逻辑：**
```python
if fire > 0 and smoke > 0:
    level = 3  # 最高级
elif fire > 0:
    level = 2  # 二级
elif smoke > 0:
    level = 1  # 一级
else:
    level = 0  # 安全
```

#### 4.2 高温报警

**数据来源：**
- HTTP服务器接收温度数据（端口8090）
- C#客户端或其他设备发送温度数据

**温度分级规则：**

| 温度范围 | 报警级别 | 状态显示 | 颜色 |
|---------|---------|---------|------|
| ≤ 30°C | 0级 | 温度正常 | 绿色 |
| 30°C ~ 50°C | 2级 | 温度偏高 | 橙色 |
| > 50°C | 3级 | 温度过高 | 红色 |

**数据格式：**
```json
{
    "sensorId": "temp_001",
    "value": 45.5
}
```

#### 4.3 人员安全报警

**检测目标：**
- `person`（人员）
- `helmet`（安全帽）
- `vest`（反光背心）
- `glove`（手套）

**报警产生规则：**

比较 `person` 数量和各装备数量：
- 如果 `helmet` 数量 < `person` 数量 → 产生安全帽报警
- 如果 `vest` 数量 < `person` 数量 → 产生反光背心报警
- 如果 `glove` 数量 < `person` 数量 → 产生手套报警

**报警消息格式：**
- "X人未佩戴安全帽（共Y人）"
- "X人未穿戴反光背心（共Y人）"
- "X人未佩戴手套（共Y人）"

**示例场景：**

| 检测到 | 勾选项目 | 报警结果 |
|-------|---------|---------|
| 2人，1个安全帽，2件背心 | 安全帽+背心 | "1人未佩戴安全帽" |
| 3人，3个安全帽，2件背心 | 安全帽+背心 | "1人未穿戴反光背心" |
| 2人，2个安全帽 | 仅安全帽 | 无报警（全部合规） |
| 2人，0个安全帽 | 安全帽+手套 | "2人未佩戴安全帽"（手套不报警，因为数量为0但勾选） |

**注意：** 如果某装备数量为0且未勾选，则不报警；如果勾选但数量为0，则全部人员都算未佩戴。

#### 4.4 报警防重复机制

**为什么需要防重复？**

在视频或摄像头实时检测时，每秒钟会处理多帧图像。如果不加控制，同一报警会每秒都被保存到数据库，产生大量重复记录。

**防重复规则：**

**区分检测类型：**

| 检测类型 | 防重复机制 |
|---------|-----------|
| 图片检测 | 不启用，每次检测都保存报警 |
| 视频检测 | 启用，防止重复保存 |
| 摄像头检测 | 启用，防止重复保存 |

**防重复逻辑：**

对于实时检测（视频/摄像头）：

| 报警变化情况 | 是否保存 | 说明 |
|-------------|---------|------|
| 首次出现该类型报警 | ✅ 保存 | 记录初始状态 |
| 报警级别升高 | ✅ 保存 | 如1级→2级、2级→3级 |
| 报警级别不变 | ❌ 不保存 | 60秒内只保存一次 |
| 报警级别降低 | ❌ 不保存 | 如3级→2级，需等60秒 |

**冷却时间：** 60秒

**示例流程：**
```
时间轴：
0秒   - 检测到烟雾（1级）→ 保存到数据库
5秒   - 仍检测到烟雾（1级）→ 不保存（冷却期内）
10秒  - 检测到明火+烟雾（3级）→ 保存（级别升高）
20秒  - 仍检测到明火+烟雾（3级）→ 不保存（冷却期内）
70秒  - 仍检测到明火+烟雾（3级）→ 保存（冷却期过）
80秒  - 仅检测到烟雾（1级）→ 不保存（级别降低，等冷却）
130秒 - 仅检测到烟雾（1级）→ 保存（冷却期过）
```

**查看防重复日志：**

在信息面板中可以看到以下日志：
- `"实时检测模式：报警防重复机制已启用（冷却期60秒）"`
- `"[fire] 报警级别升高 (1级→2级)，立即保存"`
- `"[fire] 报警级别保持不变 (2级→2级)，冷却中还需 45 秒"`
- `"火警报警处于冷却期，跳过保存"`

---

### 五、菜单功能

**文件菜单：**
- 打开图片（Ctrl+O）
- 打开视频（Ctrl+V）
- 摄像头开关（Ctrl+C）
- 退出（Esc）

**视图菜单：**
- 显示/隐藏统计信息
- 查看报警记录（打开报警查看窗口）

**检测菜单：**
- 开始检测
- 停止检测

---

### 六、报警查看窗口

通过菜单"视图"→"查看报警记录"打开，功能包括：

**功能列表：**
- 显示所有历史报警记录
- 按类别筛选（全部/环境安全/人员安全）
- 按级别筛选（全部/一级/二级/三级）
- 按状态筛选（全部/未处理/已处理）
- 按日期范围查询
- 关键词搜索
- 处理报警（标记为已处理）
- 分页显示
- 自动刷新（30秒）

---

### 七、温度数据接收

#### 7.1 HTTP服务器配置

- 端口：8090
- 地址：http://localhost:8090

#### 7.2 数据格式

发送POST请求，Content-Type: application/json

请求体：
```json
{
    "sensorId": "temp_001",
    "value": 45.5
}
```

#### 7.3 C#发送示例

```csharp
using (var client = new HttpClient())
{
    var data = new { sensorId = "temp_001", value = 45.5 };
    var json = JsonConvert.SerializeObject(data);
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    var response = await client.PostAsync("http://localhost:8090", content);
}
```

---

## 第二部分：核心方法详解

### 一、文件结构

```
fire_dection-main/
├── main.py                      # 程序入口，管理登录和主窗口
├── yolo_detector_gui.py         # 主检测界面（核心文件）
├── login_window.py              # 登录注册界面
├── auth_manager.py              # 用户认证管理
├── database.py                  # 数据库操作模块
├── init_database.py             # 数据库初始化脚本
├── alert_view_window.py         # 报警查看窗口
├── utils.py                     # 工具函数(不用管)
├── train.py                     # YOLO模型训练脚本（不用管）
├── requirements.txt             # Python依赖列表
├── weights/                     # 模型权重文件目录
│   ├── yolov8n.pt              # YOLOv8 Nano模型（不用管）
│   ├── yolov8s.pt              # YOLOv8 Small模型（不用管）
│   ├── best.pt                 # 烟雾火灾检测模型
│   └── woker_safety.pt         # 人员安全检测模型
└── runs/                        # 训练和检测结果目录（不用管）
```

---

### 二、main.py - 程序入口

#### 类：ApplicationManager

**职责：** 管理应用程序生命周期，协调登录窗口和主窗口

**核心方法：**

##### `run()`
- **功能：** 运行应用程序
- **流程：**
  1. 创建QApplication
  2. 设置应用程序属性（字体、样式、高DPI）
  3. 显示登录窗口
  4. 进入事件循环

##### `_on_login_success(user_info)`
- **功能：** 登录成功后的处理
- **参数：** `user_info` - 包含用户信息的字典
- **流程：**
  1. 创建并显示主窗口
  2. 更新窗口标题显示当前用户
  3. 关闭登录窗口

##### `_on_main_window_close(event)`
- **功能：** 主窗口关闭事件处理
- **行为：** 弹出对话框询问用户是退出程序还是切换账户

---

### 三、yolo_detector_gui.py - 主检测界面

#### 类：YOLODetectorGUI（主窗口类）

**职责：** 提供完整的检测界面，处理视频/图片检测，显示结果，管理报警

**核心属性：**
```python
self.is_realtime_detection = False      # 是否为实时检测
self.last_alert_states = {}             # 上次报警状态
self.alert_cooldown_seconds = 60        # 报警冷却时间
```

**核心方法：**

##### `start_detection()`
- **功能：** 开始检测
- **流程：**
  1. 获取选择的输入源
  2. 获取模型路径和置信度
  3. 设置检测线程参数
  4. 启动检测线程
  5. 设置`is_realtime_detection`标志（视频/摄像头为True，图片为False）

##### `stop_detection()`
- **功能：** 停止检测
- **操作：**
  1. 停止检测线程
  2. 释放视频资源
  3. 重置报警状态

##### `on_frame_received(frame, detections)`
- **功能：** 接收检测帧的回调
- **参数：**
  - `frame` - 图像帧
  - `detections` - 检测结果列表
- **操作：**
  1. 更新图像显示
  2. 更新检测统计
  3. 检查并更新报警状态
  4. 保存报警到数据库

##### `check_alerts(detections)`
- **功能：** 检查并更新报警状态
- **参数：** `detections` - 检测结果
- **流程：**
  1. 统计各类目标数量
  2. 检查火警（调用`calculate_fire_level`）
  3. 检查人员安全（调用`check_person_safety`）
  4. 更新报警显示
  5. 保存报警到数据库（调用`_save_alerts_to_database`）

##### `calculate_fire_level(fire_count, smoke_count)`
- **功能：** 计算火警级别
- **参数：** `fire_count` - 明火数量，`smoke_count` - 烟雾数量
- **返回值：** 报警级别（0-3）
- **规则：**
  - fire>0 and smoke>0 → 3级
  - fire>0 → 2级
  - smoke>0 → 1级
  - 其他 → 0级

##### `check_person_safety(person_count, helmet_count, vest_count, glove_count)`
- **功能：** 检查人员安全
- **参数：** 人员数量和各装备数量
- **返回值：** 报警消息列表
- **逻辑：**
  1. 检查复选框勾选状态
  2. 对比装备数量和人员数量
  3. 生成报警消息（如"X人未佩戴安全帽"）

##### `_should_save_alert(alert_key, alert_level)`
- **功能：** 判断是否应保存报警（防重复逻辑）
- **参数：**
  - `alert_key` - 报警类型标识（如'fire'、'helmet'）
  - `alert_level` - 报警级别
- **返回值：** bool（是否保存）
- **规则：**
  - 图片检测：直接保存
  - 首次出现：保存
  - 级别升高：保存（如1级→2级）
  - 级别不变/降低：检查冷却时间（60秒）

##### `_save_alerts_to_database(env_level, person_alerts)`
- **功能：** 保存报警到数据库
- **参数：**
  - `env_level` - 环境报警级别
  - `person_alerts` - 人员安全报警列表
- **操作：**
  1. 调用`_should_save_alert`检查是否应该保存
  2. 构建报警数据
  3. 调用AlertRepository保存到数据库

##### `check_temperature_alert(temperature)`
- **功能：** 检查温度报警
- **参数：** `temperature` - 温度值
- **返回值：** 报警级别（0-3）
- **规则：**
  - ≤30°C → 0级
  - 30-50°C → 2级
  - >50°C → 3级

##### `open_alert_view_window()`
- **功能：** 打开报警查看窗口

---

### 四、login_window.py - 登录注册界面

#### 类：LoginPage（登录页面）

**核心方法：**

##### `on_login()`
- **功能：** 登录按钮点击处理
- **流程：**
  1. 获取输入的用户名和密码
  2. 调用AuthManager验证
  3. 成功则发射login_success信号
  4. 失败则显示错误信息

#### 类：RegisterPage（注册页面）

**核心方法：**

##### `on_register()`
- **功能：** 注册按钮点击处理
- **流程：**
  1. 获取输入信息
  2. 验证表单数据（用户名格式、密码强度等）
  3. 调用AuthManager注册
  4. 成功则提示并切换页面

---

### 五、auth_manager.py - 用户认证管理

#### 类：AuthManager（单例模式）

**职责：** 管理用户认证状态和权限

**核心方法：**

##### `login(username, password)`
- **功能：** 用户登录
- **参数：** `username` - 用户名，`password` - 密码
- **返回值：** 包含登录结果的字典
- **流程：**
  1. 调用UserRepository验证用户
  2. 成功则设置当前用户和认证状态

##### `register(username, password, email, phone, role)`
- **功能：** 用户注册
- **返回值：** 包含注册结果的字典

##### `check_permission(required_role)`
- **功能：** 检查用户权限
- **参数：** `required_role` - 所需角色（admin/operator/user）
- **返回值：** bool

---

### 六、database.py - 数据库模块

#### 类：DatabaseManager（单例模式）

**核心方法：**

##### `get_connection()`
- **功能：** 获取数据库连接（上下文管理器）
- **用法：**
  ```python
  with db.get_connection() as conn:
      # 使用连接
  ```

#### 类：UserRepository

**核心方法：**

##### `create_user(username, password, email, phone, role)`
- **功能：** 创建新用户
- **操作：**
  1. 检查用户名和邮箱是否已存在
  2. 使用PBKDF2+SHA256生成密码哈希和盐值
  3. 插入数据库

##### `verify_user(username, password)`
- **功能：** 验证用户登录
- **操作：**
  1. 查询用户信息
  2. 使用PBKDF2验证密码哈希
  3. 更新最后登录时间

#### 类：AlertRepository

**核心方法：**

##### `create_alert(alert_type, alert_category, alert_level, ...)`
- **功能：** 创建报警记录

##### `get_alerts_by_date_range(start_date, end_date, ...)`
- **功能：** 按条件查询报警

##### `resolve_alert(alert_id, resolved_by)`
- **功能：** 处理报警（标记为已处理）

---

### 七、alert_view_window.py - 报警查看窗口

#### 类：AlertViewWindow

**核心方法：**

##### `load_alerts()`
- **功能：** 加载报警数据
- **操作：**
  1. 获取筛选条件（类别、级别、状态、日期）
  2. 调用AlertRepository查询
  3. 更新表格显示

##### `resolve_selected_alert()`
- **功能：** 处理选中的报警
- **操作：**
  1. 获取选中的报警ID
  2. 调用AlertRepository处理
  3. 刷新列表

---

### 八、init_database.py - 数据库初始化

#### 函数：init_database()

**功能：** 初始化数据库和表结构

**操作：**
1. 创建数据库 `factory_safety`
2. 创建users表（用户表）
3. 创建login_logs表（登录日志表）
4. 创建alerts表（报警记录表）
5. 创建默认管理员账户（admin/admin123）

---

## 附录：数据库表结构

### users表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键，自增 |
| username | VARCHAR(50) | 用户名，唯一 |
| password_hash | VARCHAR(255) | 密码哈希（PBKDF2+SHA256） |
| salt | VARCHAR(64) | 盐值 |
| email | VARCHAR(100) | 邮箱，唯一 |
| role | ENUM | 角色：admin/user/operator |
| status | ENUM | 状态：active/inactive/locked |
| created_at | TIMESTAMP | 创建时间 |
| last_login | TIMESTAMP | 最后登录时间 |

### alerts表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键，自增 |
| alert_type | VARCHAR(50) | 类型：fire/smoke/temperature/helmet/vest/glove |
| alert_category | ENUM | 类别：environment/personnel |
| alert_level | INT | 级别：0-3 |
| alert_message | TEXT | 报警消息 |
| detected_objects | JSON | 检测到的对象 |
| status | ENUM | 状态：active/resolved |
| created_at | TIMESTAMP | 创建时间 |
| resolved_by | VARCHAR(50) | 处理人 |

---

**文档版本：** v2.0  
**更新日期：** 2026年4月18日  
**作者：** AHhh  
**扩展自：** https://github.com/wn6078/fire_dection
