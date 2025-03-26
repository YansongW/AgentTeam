# JSON消息格式规范

本文档定义了多代理协作平台中使用的JSON消息格式标准，用于WebSocket通信、群组消息传递和代理之间的信息交换。

## 基本消息结构

所有消息均采用以下基本结构：

```json
{
  "message_id": "uuid-string",        // 消息唯一ID
  "message_type": "string",           // 消息类型
  "sender": {                         // 发送者信息
    "id": "string",                   // 发送者ID
    "type": "user|agent|system",      // 发送者类型
    "name": "string"                  // 发送者名称
  },
  "timestamp": "iso-datetime-string", // 时间戳 (ISO 8601格式)
  "payload": {},                      // 消息内容 (根据消息类型有不同结构)
  "metadata": {}                      // 元数据 (可选)
}
```

## 消息类型 (message_type)

平台支持以下消息类型：

### 1. 连接控制消息
- `connect`: 建立WebSocket连接
- `connect_ack`: 连接确认
- `disconnect`: 断开连接
- `ping`: 心跳检测
- `pong`: 心跳响应

### 2. 群组消息
- `chat`: 普通聊天消息
- `system`: 系统通知
- `agent_response`: 代理响应
- `join`: 成员加入
- `leave`: 成员离开
- `typing`: 正在输入
- `read_receipt`: 已读回执

### 3. 媒体和富内容消息
- `image`: 图片消息
- `file`: 文件消息
- `voice`: 语音消息
- `rich_text`: 富文本消息
- `markdown`: Markdown格式消息

### 4. 任务和协作消息
- `task`: 任务分配
- `task_update`: 任务状态更新
- `poll`: 投票消息
- `decision`: 决策消息
- `handoff`: 交接消息

### 5. 控制和状态消息
- `error`: 错误消息
- `status`: 状态更新
- `settings`: 设置变更

## 详细消息格式

### 普通聊天消息 (chat)

```json
{
  "message_id": "msg123456",
  "message_type": "chat",
  "sender": {
    "id": "user123",
    "type": "user",
    "name": "张三"
  },
  "timestamp": "2023-11-01T12:34:56.789Z",
  "payload": {
    "text": "大家好，这是一条测试消息",
    "group_id": "group123",
    "reply_to": "msg123455",  // 可选，回复的消息ID
    "mentions": [             // 可选，提及的用户或代理
      {
        "id": "user124",
        "type": "user",
        "name": "李四"
      },
      {
        "id": "agent789",
        "type": "agent",
        "name": "助手Bot"
      }
    ]
  },
  "metadata": {
    "client_id": "web-chrome-v88",
    "is_edited": false,
    "tags": ["general"]
  }
}
```

### 代理响应消息 (agent_response)

```json
{
  "message_id": "msg123457",
  "message_type": "agent_response",
  "sender": {
    "id": "agent789",
    "type": "agent",
    "name": "助手Bot"
  },
  "timestamp": "2023-11-01T12:35:10.123Z",
  "payload": {
    "text": "您好，我是助手Bot，很高兴为您服务。",
    "group_id": "group123",
    "reply_to": "msg123456",  // 回复的消息ID
    "confidence": 0.95,       // 可选，置信度
    "thinking": "用户问候，应当友好回应", // 可选，思考过程
    "sources": []             // 可选，信息来源
  },
  "metadata": {
    "model": "gpt-4-turbo",
    "tokens_used": 32,
    "response_time_ms": 450
  }
}
```

### 系统消息 (system)

```json
{
  "message_id": "msg123458",
  "message_type": "system",
  "sender": {
    "id": "system",
    "type": "system",
    "name": "系统"
  },
  "timestamp": "2023-11-01T12:36:00.000Z",
  "payload": {
    "text": "李四加入了群组",
    "group_id": "group123",
    "event_type": "member_joined", // 系统事件类型
    "subject": {                   // 事件主体
      "id": "user124",
      "type": "user",
      "name": "李四"
    }
  },
  "metadata": {
    "importance": "normal"
  }
}
```

### 任务消息 (task)

```json
{
  "message_id": "msg123459",
  "message_type": "task",
  "sender": {
    "id": "user123",
    "type": "user",
    "name": "张三"
  },
  "timestamp": "2023-11-01T13:00:00.000Z",
  "payload": {
    "text": "请分析这份数据并生成报告",
    "group_id": "group123",
    "task_id": "task789",
    "task_type": "data_analysis",
    "assignees": [
      {
        "id": "agent789",
        "type": "agent",
        "name": "助手Bot"
      }
    ],
    "due_date": "2023-11-02T18:00:00.000Z",
    "priority": "high",
    "attachments": [
      {
        "id": "file123",
        "name": "data.csv",
        "type": "csv",
        "size": 1024,
        "url": "https://example.com/files/data.csv"
      }
    ]
  },
  "metadata": {
    "workflow_id": "workflow456",
    "tags": ["analysis", "report"]
  }
}
```

### 富文本消息 (rich_text)

```json
{
  "message_id": "msg123460",
  "message_type": "rich_text",
  "sender": {
    "id": "agent789",
    "type": "agent",
    "name": "助手Bot"
  },
  "timestamp": "2023-11-01T13:10:00.000Z",
  "payload": {
    "text": "以下是报告概要",
    "group_id": "group123",
    "html_content": "<div><h1>数据分析报告</h1><p>根据您提供的数据，我们发现...</p><ul><li>发现1</li><li>发现2</li></ul></div>",
    "reply_to": "msg123459"  // 回复的任务消息ID
  },
  "metadata": {
    "render_mode": "html",
    "version": "1.0"
  }
}
```

### 错误消息 (error)

```json
{
  "message_id": "msg123461",
  "message_type": "error",
  "sender": {
    "id": "system",
    "type": "system",
    "name": "系统"
  },
  "timestamp": "2023-11-01T13:15:00.000Z",
  "payload": {
    "code": "auth_failed",
    "text": "授权失败，请重新登录",
    "severity": "error",
    "details": "Token expired"
  },
  "metadata": {
    "client_id": "web-chrome-v88",
    "request_id": "req12345"
  }
}
```

## WebSocket事件

WebSocket连接应在建立后首先发送`connect`消息，服务器以`connect_ack`消息响应：

### 连接消息 (connect)

```json
{
  "message_id": "conn123456",
  "message_type": "connect",
  "sender": {
    "id": "user123",
    "type": "user",
    "name": "张三"
  },
  "timestamp": "2023-11-01T13:30:00.000Z",
  "payload": {
    "client_info": {
      "platform": "web",
      "browser": "chrome",
      "version": "88.0"
    },
    "auth_token": "jwt_token_here"
  },
  "metadata": {
    "protocol_version": "1.0"
  }
}
```

### 连接确认消息 (connect_ack)

```json
{
  "message_id": "ack123456",
  "message_type": "connect_ack",
  "sender": {
    "id": "system",
    "type": "system",
    "name": "系统"
  },
  "timestamp": "2023-11-01T13:30:01.000Z",
  "payload": {
    "session_id": "session789",
    "server_info": {
      "version": "1.0.0",
      "features": ["typing_indicators", "read_receipts"]
    },
    "user_info": {
      "id": "user123",
      "name": "张三",
      "permissions": ["read", "write", "create_group"]
    }
  },
  "metadata": {
    "protocol_version": "1.0"
  }
}
```

## 特殊字段

### 消息内容格式

根据不同的消息类型，`payload.text`可能有不同的格式要求：

- 普通文本：纯文本字符串
- Markdown：按Markdown语法格式化的文本
- HTML：安全的HTML内容

### 提及语法

在消息文本中，可以使用以下语法提及用户或代理：

- `@用户名`：提及用户
- `@agent:代理名`：提及代理

系统会自动将这些提及转换为`mentions`数组中的对象。

### 消息状态

对于需要跟踪状态的消息（如任务），可以包含以下字段：

- `status`：当前状态（如"pending"、"in_progress"、"completed"）
- `progress`：进度（0-100的数值）
- `update_history`：状态更新历史

## 安全考虑

- 所有敏感信息（如授权令牌）仅应在建立连接时传输
- 客户端和服务器应实现消息验证机制，确保消息来源和完整性
- 所有HTML内容应经过安全过滤，防止XSS攻击
- 文件URL应使用临时令牌，且具有访问限制和过期时间 