# 错误处理和日志记录规范

本文档描述了多代理协作平台中的错误处理和日志记录规范。

## 错误代码体系

我们采用了统一的错误代码格式：`APP_CATEGORY_CODE`，其中：

- **APP**: 应用标识，指明错误来源的应用
  - USR: 用户应用
  - AGT: 代理应用
  - GRP: 群组应用
  - MSG: 消息应用
  - SYS: 系统级错误

- **CATEGORY**: 错误类别
  - AUTH: 认证相关错误
  - VAL: 验证错误
  - DB: 数据库错误
  - API: API调用错误
  - MGT: 管理错误
  - RUL: 规则错误
  - AI: AI服务错误
  - MEM: 成员错误
  - PRM: 权限错误
  - SND: 发送错误
  - FMT: 格式错误
  - WSK: WebSocket错误
  - INT: 内部错误
  - EXT: 外部服务错误

- **CODE**: 错误代码（数字）
  - 按功能模块分段，如认证错误使用001-099，数据验证错误100-199等

## 错误处理中间件

系统实现了两个核心中间件：

1. **ErrorHandlingMiddleware**: 捕获并处理请求过程中的所有异常，统一错误响应格式
2. **RequestLoggingMiddleware**: 记录所有API请求和响应的日志

这两个中间件确保了API请求的错误被正确捕获、记录和返回。

## 日志级别定义

系统使用以下日志级别：

- **DEBUG**: 开发调试信息，仅在开发环境使用
- **INFO**: 正常操作记录，如用户登录、创建群组等操作
- **WARNING**: 潜在问题警告，如权限不足的访问尝试
- **ERROR**: 影响功能但非致命的错误，如API调用失败
- **CRITICAL**: 致命错误，影响系统运行，如数据库连接失败

## 日志格式

系统支持两种主要的日志格式：

1. **文本格式**: 用于控制台和一般日志文件
   ```
   ERROR 2023-03-15 12:34:56 users.views 用户登录失败: 无效的凭据
   ```

2. **JSON格式**: 用于结构化日志，便于日志分析
   ```json
   {
     "time": "2023-03-15 12:34:56",
     "level": "ERROR",
     "module": "users.views",
     "message": "用户登录失败: 无效的凭据",
     "data": {
       "error_code": "USR_AUTH_001",
       "user_id": null,
       "ip": "192.168.1.1"
     }
   }
   ```

## 使用方法

### API错误处理

在视图中处理错误：

```python
from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import UserErrorCodes

def api_view(request):
    try:
        # 业务逻辑
        user = authenticate(username=username, password=password)
        if not user:
            return ErrorUtils.format_error_response(
                error_code=UserErrorCodes.AUTH_INVALID_CREDENTIALS,
                message="用户名或密码错误",
                http_status=status.HTTP_401_UNAUTHORIZED
            )
    except Exception as e:
        return ErrorUtils.handle_exception(
            request, 
            e, 
            UserErrorCodes.AUTH_INVALID_CREDENTIALS,
            "登录失败，请稍后再试"
        )
```

### 日志记录

记录错误日志：

```python
from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import GroupErrorCodes

try:
    # 业务逻辑
    group.add_member(user)
except Exception as e:
    ErrorUtils.log_error(
        error_code=GroupErrorCodes.MEMBER_ADD_FAILED,
        message=f"添加成员到群组失败: {str(e)}",
        exception=e,
        level='error',
        extra_data={
            'group_id': group.id,
            'user_id': user.id
        }
    )
```

### WebSocket错误

在WebSocket消费者中处理错误：

```python
from chatbot_platform.error_utils import format_websocket_error
from chatbot_platform.error_codes import MessageErrorCodes

async def receive(self, text_data):
    try:
        # 业务逻辑
    except json.JSONDecodeError:
        await self.send_error(MessageErrorCodes.INVALID_JSON, "无效的JSON格式")
    except Exception as e:
        await self.send_error(MessageErrorCodes.SEND_FAILED, f"内部错误: {str(e)}")
```

## 错误响应格式

### HTTP API错误

```json
{
  "error": {
    "code": "USR_AUTH_001",
    "message": "用户名或密码错误",
    "details": {
      "field": "password",
      "reason": "密码不匹配"
    }
  }
}
```

### WebSocket错误

```json
{
  "message_type": "error",
  "error": {
    "code": "MSG_FMT_100",
    "message": "无效的消息格式"
  },
  "sender": {
    "id": "system",
    "type": "system",
    "name": "系统"
  },
  "timestamp": "2023-03-15T12:34:56.789Z"
}
```

## 日志文件位置

系统的日志文件保存在以下位置：

- 一般日志: `logs/app.log`
- 错误日志: `logs/errors.log`
- 结构化日志: `logs/structured.log`

## 错误通知

当发生关键错误时，系统将通过以下方式发送通知：

1. 管理员邮件通知（针对ERROR和CRITICAL级别的错误）
2. 日志文件记录（所有错误）
3. 可选的外部监控系统集成（待实现） 