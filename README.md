# Multi-Agent 协作平台

本项目旨在建立通用的Agent解决方案，允许用户创建、管理和利用AI代理来协同完成各种任务。

## 产品概述

我们的multi-agent协作平台让用户能够创建具有不同角色和技能的AI代理，这些代理可以相互协作以完成复杂任务。平台支持娱乐场景（如虚拟陪伴、对话）和商业场景（如App开发、数据分析），通过多代理协作模拟人类团队合作，解决用户对高效、可扩展AI协助的需求。

### 独特优势

- **完全定制化代理角色和技能**：适应多样化需求场景
- **多代理实时协作**：模拟人类团队动态，适用于娱乐和商业双场景
- **自然语言交互与监控**：提供直观的用户体验和任务管理

## 目标用户

### 个人用户
- 寻求AI代理进行有意义的对话，提供情感支持或作为虚拟朋友
- 需要帮助处理日程安排、提醒或个性化推荐
- 艺术家、作家和创意人士希望AI代理帮助头脑风暴、生成内容或提供反馈

### 中小企业
- 使用AI代理处理客户询问、支持票据和个性化营销
- 代理处理和分析业务数据，提供决策洞察
- 简化重复性任务，如发票处理、库存管理和合规检查

### 开发者和创业者
- 利用AI代理协助编码、测试和调试，加速开发周期
- 使用AI代理模拟用户行为和市场反应，测试产品创意
- 利用AI代理探索新技术、算法和解决方案

## 关键功能

1. **代理创建和管理**
   - 自定义角色：选择预定义代理角色或创建自定义角色
   - 技能配置：为每个代理配置特定技能或基于特定数据集进行训练
   - 权限和访问控制：设置代理的权限，控制数据访问范围

2. **任务分配与协作**
   - 任务创建：创建包含详细描述、截止日期和优先级的任务
   - 代理分配：任务可分配给单个代理或代理组
   - 实时协作：代理通过实时通信和数据交换协作完成任务

3. **用户监控和干预**
   - 仪表板：全面的仪表板，显示任务进度、代理状态和性能指标
   - 自然语言命令：通过自然语言输入框发布命令，控制代理行为
   - 实时更新：实时查看任务和代理状态变化

4. **安全和数据隐私**
   - 加密保护：数据传输和存储加密
   - 多租户架构：租户隔离确保数据安全
   - 合规性：符合国际数据保护法规

## 系统架构

### 架构概览图

```
+-----------------------------------------------------------------------------------+
|                                 Multi-Agent协作平台                                 |
+-----------------------------------------------------------------------------------+
          |                        |                      |                    |
+-----------------+     +-------------------+     +----------------+    +---------------+
|    用户管理       |     |     代理管理       |     |    消息处理      |    |    群组管理    |
| (users模块)      |     |  (agents模块)     |     | (messaging模块) |    | (groups模块)  |
+-----------------+     +-------------------+     +----------------+    +---------------+
          |                        |                      |                    |
          |                        |                      |                    |
          v                        v                      v                    v
+-----------------------------------------------------------------------------------+
|                                  WebSocket通信层                                    |
|                           (ASGI, Channels, Redis)                                  |
+-----------------------------------------------------------------------------------+
          |                                                                 |
          v                                                                 v
+------------------------+                                        +---------------------+
|      数据库存储          |                                        |     前端界面          |
| (SQLite/PostgreSQL)    |                                        | (HTML, CSS, JS)     |
+------------------------+                                        +---------------------+
```

### 详细代码结构图

```
项目根目录
│
├── manage.py                    # Django项目管理脚本
├── requirements.txt             # 项目依赖包
├── README.md                    # 项目说明文档
├── Task_list.md                 # 任务列表
├── 开发规范.md                   # 开发规范文档
├── .env.example                 # 环境变量示例
│
├── chatbot_platform/            # 主项目配置目录
│   ├── __init__.py              # 包初始化文件
│   ├── asgi.py                  # ASGI配置（WebSocket支持）
│   ├── settings.py              # Django项目设置
│   ├── urls.py                  # 主URL配置
│   ├── wsgi.py                  # WSGI配置
│   ├── middleware.py            # 中间件定义
│   ├── error_codes.py           # 错误代码定义
│   └── error_utils.py           # 错误处理工具
│
├── agents/                      # 代理管理应用
│   ├── __init__.py              # 包初始化文件
│   ├── admin.py                 # 管理界面配置
│   ├── apps.py                  # 应用配置
│   ├── models.py                # 数据模型定义
│   ├── serializers.py           # API序列化器
│   ├── services.py              # 业务逻辑服务
│   ├── signals.py               # 信号处理
│   ├── urls.py                  # URL路由
│   ├── views.py                 # 视图函数/类
│   ├── permissions.py           # 权限控制
│   ├── async_processor.py       # 异步消息处理器
│   ├── handlers.py              # 响应处理器
│   ├── utils.py                 # 工具函数
│   │
│   ├── utils/                   # 工具子包
│   │   ├── sentiment_analyzer.py # 情感分析工具
│   │   └── topic_analyzer.py    # 主题分析工具
│   │
│   ├── tests/                   # 测试子包
│   │   ├── test_rule_engine.py  # 规则引擎测试
│   │   └── test_async_processor.py # 异步处理器测试
│   │
│   ├── migrations/              # 数据库迁移文件
│   ├── static/                  # 静态资源
│   └── templates/               # HTML模板
│
├── messaging/                   # 消息处理应用
│   ├── __init__.py              # 包初始化文件
│   ├── admin.py                 # 管理界面配置
│   ├── apps.py                  # 应用配置
│   ├── models.py                # 数据模型定义
│   ├── consumers.py             # WebSocket消费者
│   ├── routing.py               # WebSocket路由
│   ├── serializers.py           # API序列化器
│   ├── signals.py               # 信号处理
│   ├── urls.py                  # HTTP URL路由
│   ├── urls_websocket.py        # WebSocket URL路由
│   ├── validators.py            # 消息验证器
│   ├── views.py                 # 视图函数/类
│   ├── migrations/              # 数据库迁移文件
│   └── templates/               # HTML模板
│
├── groups/                      # 群组管理应用
│   ├── __init__.py              # 包初始化文件
│   ├── admin.py                 # 管理界面配置
│   ├── apps.py                  # 应用配置
│   ├── models.py                # 数据模型定义
│   ├── serializers.py           # API序列化器
│   ├── signals.py               # 信号处理
│   ├── urls.py                  # URL路由
│   ├── views.py                 # 视图函数/类
│   ├── permissions.py           # 权限控制
│   ├── migrations/              # 数据库迁移文件
│   └── static/                  # 静态资源
│
├── task_management/             # 任务管理应用
│   ├── __init__.py              # 包初始化文件
│   ├── admin.py                 # 管理界面配置
│   ├── apps.py                  # 应用配置
│   ├── models.py                # 数据模型定义
│   ├── serializers.py           # API序列化器
│   ├── signals.py               # 信号处理
│   ├── urls.py                  # URL路由
│   ├── views.py                 # 视图函数/类
│   ├── tests.py                 # 测试代码
│   ├── migrations/              # 数据库迁移文件
│   ├── static/                  # 静态资源
│   │   ├── css/                 # CSS样式文件
│   │   └── js/                  # JavaScript文件
│   └── templates/               # HTML模板
│
├── users/                       # 用户管理应用
│   ├── __init__.py              # 包初始化文件
│   ├── admin.py                 # 管理界面配置
│   ├── apps.py                  # 应用配置
│   ├── models.py                # 数据模型定义
│   ├── serializers.py           # API序列化器
│   ├── signals.py               # 信号处理
│   ├── urls.py                  # URL路由
│   ├── views.py                 # 视图函数/类
│   ├── permissions.py           # 权限控制
│   ├── utils.py                 # 工具函数
│   ├── tests.py                 # 测试代码
│   └── migrations/              # 数据库迁移文件
│
├── static/                      # 全局静态资源
├── templates/                   # 全局HTML模板
├── docs/                        # 文档目录
└── logs/                        # 日志目录
```

## 模块功能详解

### 1. agents - 代理管理模块

代理管理模块是平台的核心，负责AI代理的创建、配置、监听规则和响应处理。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Agent、AgentListeningRule等数据模型，包含代理属性、能力和监听规则的所有相关字段 |
| services.py | 提供代理相关业务逻辑服务，包含RuleEngine类实现消息匹配和规则处理 |
| views.py | 实现代理相关的API视图，包含代理创建、更新、查询和监听规则管理 |
| async_processor.py | 异步消息处理器，负责将消息放入队列并异步处理代理响应 |
| handlers.py | 响应处理器，定义各类型响应的处理函数（自动回复、通知、任务创建、动作执行等） |
| utils/sentiment_analyzer.py | 情感分析工具，用于分析消息情感倾向 |
| utils/topic_analyzer.py | 主题分析工具，用于分析消息主题相关性 |
| tests/test_rule_engine.py | 规则引擎的单元测试代码 |
| tests/test_async_processor.py | 异步处理器的单元测试代码 |

### 2. messaging - 消息处理模块

消息处理模块负责所有消息的传递、存储和WebSocket通信。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Message、MessageDeliveryStatus等数据模型 |
| consumers.py | WebSocket消费者，处理实时消息通信，包含连接、接收、广播等功能 |
| routing.py | WebSocket路由配置 |
| validators.py | 消息验证器，确保消息格式正确 |
| views.py | 实现消息相关的HTTP API |

### 3. groups - 群组管理模块

群组管理模块负责用户群组的创建和管理，支持多人和多代理协作。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Group、GroupMember等数据模型 |
| views.py | 实现群组相关的API，包含创建、加入、退出等功能 |
| permissions.py | 群组权限控制，定义不同角色的权限 |
| serializers.py | API序列化器，处理群组数据的序列化和反序列化 |

### 4. task_management - 任务管理模块

任务管理模块负责项目任务的创建、分配、跟踪和管理，支持用户和代理协作完成任务。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Task、TaskAssignment、TaskComment、TaskTag等数据模型 |
| views.py | 实现任务相关的API，包含创建、分配、状态更新、批量操作等功能 |
| serializers.py | API序列化器，处理任务数据的序列化和反序列化 |
| signals.py | 信号处理器，处理任务状态变更、任务分配等事件的通知 |
| admin.py | 管理界面配置，提供直观的任务管理UI |
| tests.py | 任务模块的单元测试代码 |
| static/js/task_management.js | 前端交互逻辑，处理任务列表、创建、编辑等操作 |
| static/css/task_management.css | 任务界面样式 |
| templates/tasks/task_list.html | 任务列表页面模板 |

### 5. users - 用户管理模块

用户管理模块负责用户账户的注册、认证和管理。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 自定义用户模型 |
| views.py | 实现用户相关的API，包含注册、登录、个人资料管理等 |
| serializers.py | 用户数据序列化器 |
| utils.py | 用户相关工具函数，如密码重置、邮件验证等 |

### 6. chatbot_platform - 核心配置模块

项目的核心配置模块，包含全局设置和配置。

| 文件/目录 | 功能描述 |
|---------|---------|
| settings.py | Django项目设置，包含数据库、中间件、认证等配置 |
| urls.py | 全局URL路由配置 |
| asgi.py | ASGI配置，支持WebSocket |
| middleware.py | 自定义中间件，处理认证、日志等 |
| error_codes.py | 错误代码定义 |
| error_utils.py | 错误处理工具 |

## 关键工作流程

### 消息处理和代理响应流程

```
 用户
  |
  | 发送消息
  v
+---------------------+
| WebSocket消费者      |
| (MessageConsumer)   |
+---------------------+
  |
  | 消息验证和保存
  v
+---------------------+
| 异步消息处理器       |
| (AsyncMessageProcessor) 
+---------------------+
  |
  | 规则匹配
  v
+---------------------+
| 规则引擎            |
| (RuleEngine)        |
+---------------------+
  |
  | 生成响应
  v
+---------------------+
| 响应处理器          |
| (各类型处理函数)     |
+---------------------+
  |
  | 发送响应
  v
+---------------------+
| WebSocket群组广播   |
+---------------------+
  |
  v
 用户
```

### 任务创建和管理流程

```
 用户/代理
  |
  | 创建任务
  v
+---------------------+
| 任务视图            |
| (TaskViewSet)       |
+---------------------+
  |
  | 任务验证和保存
  v
+---------------------+
| 数据库操作          |
| (Task Model)        |
+---------------------+
  |
  | 任务分配
  v
+---------------------+
| 任务分配处理        |
| (TaskAssignment)    |
+---------------------+
  |
  | 状态更新
  v
+---------------------+
| 信号处理器          |
| (task_signals)      |
+---------------------+
  |
  | 通知
  v
+---------------------+
| WebSocket通知       |
+---------------------+
  |
  v
 用户/代理
```

## 技术栈

- **后端**: Django (Python)
- **数据库**: SQLite (开发环境) / PostgreSQL (生产环境)
- **前端**: HTML, CSS, JavaScript
- **WebSocket**: Django Channels
- **消息队列**: 内置异步队列 (AsyncMessageProcessor)
- **NLP工具**: TextBlob (情感分析), Jieba (中文分词), Word2Vec (主题分析)
- **认证**: JWT (JSON Web Tokens)
- **容器化**: Docker（规划中）

## 开发环境设置

### 后端设置

1. 克隆代码库:
   ```
   git clone <repository-url>
   cd multi-agent-platform
   ```

2. 创建虚拟环境:
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

4. 应用数据库迁移:
   ```
   python manage.py migrate
   ```

5. 创建超级用户:
   ```
   python manage.py createsuperuser
   ```

6. 运行开发服务器:
   ```
   python manage.py runserver
   ```

7. 访问管理界面:
   http://127.0.0.1:8000/admin/

## 贡献指南

请参考[开发规范.md](./开发规范.md)了解代码风格和贡献流程。 

## 当前开发状态

- [x] 用户认证系统
- [x] 代理创建和管理
- [x] 群组聊天功能
- [x] WebSocket实时通信
- [x] 代理监听规则引擎
- [x] 异步消息处理
- [x] 情感分析和主题分析
- [x] 任务管理系统
- [ ] 数据分析仪表板
- [ ] AI模型集成
- [ ] 移动端适配 # AgentTeam
