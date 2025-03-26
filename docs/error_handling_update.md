# 错误处理系统更新

## 已完成的更新

我们已经成功实现了统一的错误处理系统，主要包括以下组件：

1. **错误代码常量**：在 `chatbot_platform/error_codes.py` 中定义了系统级错误代码
2. **错误处理工具类**：在 `chatbot_platform/error_utils.py` 中实现了 `ErrorUtils` 类，提供了格式化错误响应和处理异常的功能
3. **中间件集成**：添加了 `RequestLoggingMiddleware` 和 `ErrorHandlingMiddleware` 到 Django 配置
4. **WebSocket 错误处理**：更新了 WebSocket 消费者使用新的错误处理工具
5. **应用视图错误处理**：更新了 `messaging`、`groups` 和 `agents` 应用的主要视图使用新的错误处理
6. **规则测试工具**：实现了代理监听规则测试功能和相关API端点

## 新的错误处理流程

1. 所有返回给客户端的错误都使用统一的格式，包含：
   - `error_code`：遵循 `APP_CATEGORY_CODE` 格式的唯一错误代码
   - `message`：用户友好的错误信息
   - `details`：（可选）进一步的错误详情
   - `request_id`：用于追踪请求的唯一标识符

2. 所有接口层面的异常都通过 `ErrorHandlingMiddleware` 自动捕获并处理
   - 未捕获的异常会被记录并转换为标准错误响应
   - 特定异常类型会映射到特定的错误代码和HTTP状态码

3. 所有API请求和响应都通过 `RequestLoggingMiddleware` 记录
   - 日志中包含请求方法、路径、状态码和处理时间
   - 对于错误响应，会记录更详细的信息以便调试

## 代理规则测试功能

实现了用于测试代理监听规则的功能，包括：

1. `test_rule_match` 函数：测试消息是否匹配规则，返回详细的匹配结果
2. `apply_rule_transformations` 函数：应用规则定义的转换操作到消息
3. `/api/agent-rules/{id}/test_rule/` API端点：提供在线测试规则功能

## 如何使用新的错误处理系统

在视图函数或方法中：

```python
# 返回格式化的错误响应
return ErrorUtils.format_error_response(
    error_code=UserErrorCodes.USER_NOT_FOUND,
    message="找不到指定的用户",
    http_status=status.HTTP_404_NOT_FOUND
)

# 处理异常
try:
    # 业务逻辑
except Exception as e:
    logger.error(f"操作失败: {str(e)}", exc_info=True)
    return ErrorUtils.handle_exception(
        request,
        e,
        GroupErrorCodes.OPERATION_FAILED,
        "操作失败，请稍后再试"
    )
```

在WebSocket消费者中：

```python
# 发送错误消息
await self.send_error(
    message_id=message_id,
    error_code=MessageErrorCodes.INVALID_FORMAT,
    error_message="消息格式无效"
)
```

## 下一步工作

1. **扩展错误代码**：随着应用功能的增加，持续扩展错误代码集
2. **监控告警集成**：将严重错误与监控系统集成
3. **客户端错误处理**：更新前端应用以统一处理错误响应
4. **错误分析工具**：开发用于分析错误模式和趋势的工具 