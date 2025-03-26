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
├── .env                         # 环境变量配置
├── create_test_data.py          # 测试数据创建脚本
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
│   │   ├── css/                 # CSS样式文件
│   │   └── js/                  # JavaScript文件
│   └── templates/               # HTML模板
│       ├── agent_management.html # 代理管理界面
│       ├── rule_management.html # 规则管理界面
│       └── agent_demo.html      # 代理演示界面
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
│       └── websocket_test.html  # WebSocket测试页面
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
│   ├── agents/                  # 代理相关静态资源
│   │   ├── css/                 # 代理CSS样式
│   │   └── js/                  # 代理JavaScript
│   ├── messaging/               # 消息相关静态资源
│   │   ├── css/                 # 消息CSS样式
│   │   └── js/                  # 消息JavaScript
│   └── images/                  # 图片资源
│
├── templates/                   # 全局HTML模板
│   ├── base.html                # 基础模板
│   ├── agents/                  # 代理相关模板
│   ├── groups/                  # 群组相关模板
│   ├── messaging/               # 消息相关模板
│   └── tasks/                   # 任务相关模板
│
├── staticfiles/                 # 收集的静态文件
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
| utils/ | 工具子包，包含情感分析、主题分析等工具 |
| templates/agent_management.html | 代理管理前端界面，提供创建和管理代理的用户界面 |
| templates/rule_management.html | 规则管理前端界面，用于配置代理的监听规则 |
| templates/agent_demo.html | 代理演示页面，展示如何使用@提及功能与代理交互 |
| static/agents/css/ | 代理相关的CSS样式文件 |
| static/agents/js/ | 代理相关的JavaScript文件，实现前端交互逻辑 |

### 2. messaging - 消息处理模块

消息处理模块负责所有消息的传递、存储和WebSocket通信。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Message、MessageDeliveryStatus等数据模型，用于存储和跟踪消息 |
| consumers.py | WebSocket消费者，处理实时消息通信，包含连接、接收、广播等功能 |
| routing.py | WebSocket路由配置，将WebSocket请求路由到相应的消费者 |
| validators.py | 消息验证器，确保消息格式正确，验证消息内容和元数据 |
| views.py | 实现消息相关的HTTP API，如发送消息、获取历史消息等功能 |
| templates/websocket_test.html | WebSocket测试页面，用于测试实时消息通信 |
| static/messaging/css/ | 消息相关的CSS样式文件 |
| static/messaging/js/ | 消息相关的JavaScript文件，实现前端消息处理逻辑 |

### 3. groups - 群组管理模块

群组管理模块负责用户群组的创建和管理，支持多人和多代理协作。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Group、GroupMember等数据模型，管理群组结构和成员关系 |
| views.py | 实现群组相关的API，包含创建、加入、退出群组等功能 |
| permissions.py | 群组权限控制，定义不同角色的权限和访问控制 |
| serializers.py | API序列化器，处理群组数据的序列化和反序列化 |
| admin.py | 管理界面配置，提供群组管理的后台界面 |
| static/ | 群组相关的静态资源，包括CSS和JavaScript文件 |

### 4. task_management - 任务管理模块

任务管理模块负责项目任务的创建、分配、跟踪和管理，支持用户和代理协作完成任务。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义Task、TaskAssignment、TaskComment、TaskTag等数据模型，管理任务及其关联数据 |
| views.py | 实现任务相关的API，包含创建、分配、状态更新、批量操作等功能 |
| serializers.py | API序列化器，处理任务数据的序列化和反序列化 |
| signals.py | 信号处理器，处理任务状态变更、任务分配等事件的通知 |
| admin.py | 管理界面配置，提供直观的任务管理UI |
| tests.py | 任务模块的单元测试代码 |
| static/ | 任务管理相关的静态资源，包括CSS和JavaScript文件 |
| templates/ | 任务管理相关的HTML模板，提供任务管理界面 |

### 5. users - 用户管理模块

用户管理模块负责用户的注册、身份验证、权限管理和个人资料管理。

| 文件/目录 | 功能描述 |
|---------|---------|
| models.py | 定义User、Profile等数据模型，管理用户数据和个人资料 |
| views.py | 实现用户相关的API，包含注册、登录、个人资料管理等功能 |
| serializers.py | API序列化器，处理用户数据的序列化和反序列化 |
| permissions.py | 用户权限控制，定义不同用户的权限和访问控制 |
| utils.py | 用户相关的工具函数，如密码重置、邮件通知等 |
| tests.py | 用户模块的单元测试代码 |

## 前端界面

平台提供了直观的用户界面，帮助用户管理和使用AI代理。主要界面包括：

1. **代理管理界面** - 创建、编辑和管理AI代理，配置代理属性和行为
2. **规则管理界面** - 设置代理的监听规则和响应行为
3. **代理演示界面** - 展示如何使用@提及功能与代理交互
4. **WebSocket测试界面** - 测试实时消息通信功能
5. **任务管理界面** - 创建、分配和追踪任务

所有前端界面采用响应式设计，确保在不同设备上都能提供良好的用户体验。界面使用Bootstrap框架构建，结合现代CSS技术和JavaScript库，实现了丰富的交互功能和视觉效果。

## 开发环境设置

1. 克隆项目仓库
   ```
   git clone https://github.com/YansongW/AgentTeam.git
   cd AgentTeam
   ```

2. 创建并激活虚拟环境
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 安装依赖
   ```
   pip install -r requirements.txt
   ```

4. 环境变量配置
   ```
   cp .env.example .env
   # 编辑.env文件，填写必要的配置
   ```

5. 数据库迁移
   ```
   python manage.py migrate
   ```

6. 创建超级用户
   ```
   python manage.py createsuperuser
   ```

7. 收集静态文件
   ```
   python manage.py collectstatic
   ```

8. 启动开发服务器
   ```
   python manage.py runserver
   ```

## 贡献指南

欢迎为项目贡献代码、报告问题或提交功能请求。请参阅`开发规范.md`了解更多关于代码风格和贡献流程的信息。

## 当前开发状态

本项目正处于活跃开发阶段，主要模块已经完成基础功能实现：

- ✅ 用户管理系统（注册、登录、权限控制）
- ✅ 代理创建和配置功能
- ✅ 代理监听规则管理
- ✅ 实时消息传递系统
- ✅ 群组创建和管理
- ✅ 基本的任务管理功能
- ✅ 前端基础界面和交互
- 🔄 代理智能行为优化
- 🔄 任务管理高级功能
- 🔄 移动端适配优化
- 📅 权限系统完善（计划中）
- 📅 高级报表和分析（计划中）
- 📅 代理市场功能（计划中）

## 技术栈

### 后端技术
- **框架**: Django (Python)
- **API**: Django REST Framework
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **WebSocket**: Django Channels
- **异步处理**: 自定义异步消息处理器
- **NLP工具**: 情感分析、主题分析
- **认证**: JWT (JSON Web Tokens)

### 前端技术
- **框架**: Bootstrap 5
- **JavaScript**: 原生JS + 部分功能使用jQuery
- **WebSocket客户端**: JavaScript WebSocket API
- **CSS**: 自定义样式 + Bootstrap组件
- **响应式设计**: 支持桌面和移动设备

### 开发工具
- **版本控制**: Git
- **测试**: Django TestCase
- **文档**: Markdown
- **环境管理**: Python venv

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

### 代理管理界面交互流程

```
 用户
  |
  | 访问代理管理页面
  v
+---------------------+
| 加载页面            |
| (agent_management.html)
+---------------------+
  |
  | 页面加载完成
  v
+---------------------+
| 初始化数据加载      |
| (loadAgents)        |
+---------------------+
  |
  | API请求
  v
+---------------------+
| 后端API响应         |
| (AgentViewSet)      |
+---------------------+
  |
  | 渲染代理列表
  v
+---------------------+
| 创建/编辑/删除代理  |
| (前端JS事件处理)    |
+---------------------+
  |
  | 表单提交/API请求
  v
+---------------------+
| 后端处理            |
| (数据验证与存储)    |
+---------------------+
  |
  | 响应结果
  v
+---------------------+
| 前端更新UI          |
| (显示结果/错误提示) |
+---------------------+
  |
  v
 用户
```
