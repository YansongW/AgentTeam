# 错误处理系统更新文档

## 1. 系统概述

我们实现了一个统一的错误处理系统，包括以下核心组件：

- **错误代码常量**：定义了所有应用的错误代码
- **错误处理工具类**：提供了错误记录和响应格式化功能
- **中间件集成**：添加了请求日志和错误处理中间件
- **信号处理器**：添加了每个应用的信号处理器，用于记录重要操作
- **规则引擎**：实现了代理监听规则测试功能和相关API端点

## 2. 错误代码结构

错误代码遵循统一的格式：`APP_CATEGORY_CODE`，例如：

- `USR_AUTH_001`: 用户应用 > 认证类别 > 错误代码001
- `GRP_MEM_105`: 群组应用 > 成员管理类别 > 错误代码105
- `MSG_WSK_203`: 消息应用 > WebSocket类别 > 错误代码203

## 3. 应用程序集成

每个应用都通过以下方式集成到错误处理系统：

1. **AppConfig.ready() 方法**：每个应用在初始化时注册错误代码
2. **信号处理器**：记录重要的数据操作事件（创建、更新、删除）
3. **视图更新**：所有API视图使用统一的错误响应格式
4. **中间件**：应用统一的请求日志和错误捕获

## 4. 错误处理流程

```
客户端请求 → RequestLoggingMiddleware → 应用视图 → 
                                     ↓
                               [出现异常]
                                     ↓
ErrorHandlingMiddleware → ErrorUtils.handle_exception → 格式化错误响应 → 客户端
```

## 5. 日志系统

日志系统配置支持以下格式：

- **结构化JSON日志**：适用于机器处理和分析
- **标准文本日志**：适用于人工查看
- **错误专用日志**：所有错误事件单独记录

日志级别：
- DEBUG: 详细调试信息
- INFO: 一般操作信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误信息

## 6. 规则引擎

实现了代理监听规则功能：

- **规则匹配**：根据消息内容、类型、发送者等条件匹配规则
- **规则转换**：对匹配的消息应用内容、类型、元数据转换
- **规则测试API**：提供API端点测试规则匹配和转换效果

## 7. 使用说明

### 在视图中使用错误处理

```python
# 返回错误响应
return ErrorUtils.format_error_response(
    error_code=UserErrorCodes.USER_NOT_FOUND,
    message="找不到指定的用户",
    http_status=status.HTTP_404_NOT_FOUND
)

# 异常处理
try:
    # 业务逻辑
except Exception as e:
    return ErrorUtils.handle_exception(
        request,
        e,
        GroupErrorCodes.OPERATION_FAILED,
        "操作失败，请稍后再试"
    )
```

### 在WebSocket消费者中使用

```python
# 发送错误消息
await self.send_error(
    message_id=message_id,
    error_code=MessageErrorCodes.INVALID_FORMAT,
    error_message="消息格式无效"
)
```

## 8. 下一步计划

1. **客户端集成**：更新前端应用统一处理错误响应
2. **告警集成**：与监控系统集成，对严重错误发送告警
3. **错误分析工具**：开发错误模式分析工具
4. **错误码文档**：生成完整的错误码文档供开发和测试使用 