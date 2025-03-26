# 消息系统设计与实现

本文档简要介绍了多代理协作平台中的消息系统设计与实现。

## 设计目标

消息系统的主要目标：

1. 提供标准化的消息交换格式
2. 支持实时通信和离线消息传递
3. 实现群组消息和私人消息功能
4. 支持消息追踪、已读状态和消息历史
5. 便于AI代理与用户之间的互动

## 核心组件

### 1. 消息格式Schema

我们定义了标准的JSON消息格式，包括以下核心字段：

- `message_id`: 消息唯一ID
- `message_type`: 消息类型（聊天、系统通知、代理响应等）
- `sender`: 发送者信息（ID、类型、名称）
- `timestamp`: 时间戳
- `payload`: 消息内容（根据消息类型有不同结构）
- `metadata`: 元数据（可选）

详细的Schema定义请参考：[message_schema.md](message_schema.md)

### 2. 数据模型

我们设计了两个核心数据模型：

- `Message`: 存储消息的主要内容、发送方、接收方等信息
- `MessageDeliveryStatus`: 跟踪消息的送达和已读状态

### 3. API端点

提供了以下主要API端点：

- `GET /api/messaging/messages/`: 获取消息列表
- `POST /api/messaging/messages/`: 创建新消息
- `GET /api/messaging/messages/{id}/`: 获取特定消息详情
- `GET /api/messaging/messages/my_messages/`: 获取与当前用户相关的所有消息
- `POST /api/messaging/messages/send_to_group/`: 发送消息到群组
- `POST /api/messaging/messages/send_to_user/`: 发送消息给用户
- `POST /api/messaging/message-statuses/mark_as_read/`: 标记消息为已读
- `GET /api/messaging/message-statuses/unread_count/`: 获取未读消息数

### 4. 消息验证

实现了基于JSON Schema的消息验证机制，确保消息格式符合规范，包括：

- 通用消息格式验证
- 特定消息类型的验证（聊天消息、系统消息、代理响应等）

## 技术实现

主要技术和工具：

1. Django和Django REST framework提供API框架
2. JSON Schema用于消息格式验证
3. PostgreSQL数据库存储消息
4. WebSocket (计划实现)提供实时消息推送

## 使用示例

### 发送消息到群组

```json
// POST /api/messaging/messages/send_to_group/
{
  "group_id": "123",
  "content": {
    "text": "大家好，这是一条测试消息",
    "mentions": [
      {
        "id": "456",
        "type": "user",
        "name": "张三"
      }
    ]
  },
  "message_type": "chat"
}
```

### 标记消息为已读

```json
// POST /api/messaging/message-statuses/mark_as_read/
{
  "message_ids": ["msg-uuid-1", "msg-uuid-2", "msg-uuid-3"]
}
```

## 后续计划

1. 实现基于WebSocket的实时消息通道
2. 集成消息搜索功能
3. 支持更多消息类型和富媒体内容
4. 优化消息传递性能和可靠性 