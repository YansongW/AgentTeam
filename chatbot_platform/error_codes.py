"""
错误代码常量文件
定义所有应用使用的统一错误代码格式：APP_CATEGORY_CODE
"""

# 用户应用错误代码
class UserErrorCodes:
    # 认证相关错误 (1-99)
    AUTH_INVALID_CREDENTIALS = "USR_AUTH_001"  # 无效的用户名或密码
    AUTH_EXPIRED_TOKEN = "USR_AUTH_002"  # 令牌已过期
    AUTH_INVALID_TOKEN = "USR_AUTH_003"  # 无效的令牌
    AUTH_INSUFFICIENT_PERMISSIONS = "USR_AUTH_004"  # 权限不足
    AUTH_ACCOUNT_DISABLED = "USR_AUTH_005"  # 账户已禁用
    
    # 用户数据验证错误 (100-199)
    VAL_INVALID_EMAIL = "USR_VAL_100"  # 无效的邮箱格式
    VAL_WEAK_PASSWORD = "USR_VAL_101"  # 密码强度不足
    VAL_DUPLICATE_USERNAME = "USR_VAL_102"  # 用户名已存在
    VAL_DUPLICATE_EMAIL = "USR_VAL_103"  # 邮箱已存在
    
    # 数据库操作错误 (200-299)
    DB_CREATE_FAILED = "USR_DB_200"  # 创建用户失败
    DB_UPDATE_FAILED = "USR_DB_201"  # 更新用户信息失败
    DB_DELETE_FAILED = "USR_DB_202"  # 删除用户失败
    
    # API错误 (300-399)
    API_RATE_LIMIT = "USR_API_300"  # 请求频率超限
    API_MALFORMED_REQUEST = "USR_API_301"  # 请求格式不正确
    
    # 通用错误
    USER_NOT_FOUND = "USR_DB_404"  # 用户不存在


# 代理应用错误代码
class AgentErrorCodes:
    # 代理创建和管理错误 (1-99)
    AGENT_CREATE_FAILED = "AGT_MGT_001"  # 创建代理失败
    AGENT_UPDATE_FAILED = "AGT_MGT_002"  # 更新代理信息失败
    AGENT_DELETE_FAILED = "AGT_MGT_003"  # 删除代理失败
    AGENT_NOT_FOUND = "AGT_MGT_004"  # 代理不存在
    AGENT_DISABLED = "AGT_MGT_005"  # 代理已禁用
    NOT_VALIDATED = "AGT_MGT_006"  # 代理未验证
    DEPLOY_FAILED = "AGT_MGT_007"  # 部署失败
    VALIDATION_FAILED = "AGT_MGT_008"  # 验证失败
    MISSING_REQUIRED_FIELD = "AGT_MGT_009"  # 缺少必填字段
    RULE_TEST_FAILED = "AGT_MGT_010"  # 规则测试失败
    
    # 规则引擎错误 (100-199)
    RULE_CREATE_FAILED = "AGT_RUL_100"  # 创建规则失败
    RULE_UPDATE_FAILED = "AGT_RUL_101"  # 更新规则失败
    RULE_DELETE_FAILED = "AGT_RUL_102"  # 删除规则失败
    RULE_EXECUTION_FAILED = "AGT_RUL_103"  # 规则执行失败
    RULE_NOT_FOUND = "AGT_RUL_104"  # 规则不存在
    RULE_INVALID_CONDITION = "AGT_RUL_105"  # 无效的规则条件
    
    # AI服务错误 (200-299)
    AI_SERVICE_UNAVAILABLE = "AGT_AI_200"  # AI服务不可用
    AI_REQUEST_FAILED = "AGT_AI_201"  # AI请求失败
    AI_RESPONSE_INVALID = "AGT_AI_202"  # AI响应格式无效
    AI_CONTEXT_TOO_LARGE = "AGT_AI_203"  # 上下文过大
    AI_RATE_LIMIT = "AGT_AI_204"  # API调用频率超限
    AI_CONTENT_FILTERED = "AGT_AI_205"  # 内容被过滤


# 规则错误代码
class RuleErrorCodes:
    # 规则匹配错误 (1-99)
    INVALID_MESSAGE_FORMAT = "RUL_VAL_001"  # 无效的消息格式
    INVALID_RULE_FORMAT = "RUL_VAL_002"  # 无效的规则格式
    TYPE_MISMATCH = "RUL_VAL_003"  # 消息类型不匹配
    SENDER_TYPE_MISMATCH = "RUL_VAL_004"  # 发送者类型不匹配
    SENDER_MISMATCH = "RUL_VAL_005"  # 发送者不匹配
    KEYWORD_MISMATCH = "RUL_VAL_006"  # 关键词不匹配
    REGEX_MISMATCH = "RUL_VAL_007"  # 正则表达式不匹配
    INVALID_REGEX = "RUL_VAL_008"  # 无效的正则表达式
    TEST_FAILED = "RUL_VAL_009"  # 规则测试失败
    
    # 规则转换错误 (100-199)
    TRANSFORMATION_FAILED = "RUL_TRF_100"  # 转换失败
    INVALID_TEMPLATE = "RUL_TRF_101"  # 无效的模板
    INVALID_METADATA = "RUL_TRF_102"  # 无效的元数据


# 群组应用错误代码
class GroupErrorCodes:
    # 群组管理错误 (1-99)
    GROUP_CREATE_FAILED = "GRP_MGT_001"  # 创建群组失败
    GROUP_UPDATE_FAILED = "GRP_MGT_002"  # 更新群组信息失败
    GROUP_DELETE_FAILED = "GRP_MGT_003"  # 删除群组失败
    GROUP_NOT_FOUND = "GRP_MGT_004"  # 群组不存在
    
    # 成员管理错误 (100-199)
    MEMBER_ADD_FAILED = "GRP_MEM_100"  # 添加成员失败
    MEMBER_REMOVE_FAILED = "GRP_MEM_101"  # 移除成员失败
    MEMBER_UPDATE_FAILED = "GRP_MEM_102"  # 更新成员信息失败
    MEMBER_NOT_FOUND = "GRP_MEM_103"  # 成员不存在
    MEMBER_ALREADY_EXISTS = "GRP_MEM_104"  # 成员已存在
    MEMBER_INSUFFICIENT_PERMISSIONS = "GRP_MEM_105"  # 成员权限不足
    ADD_MEMBER_FAILED = "GRP_MEM_106"  # 添加成员失败
    REMOVE_MEMBER_FAILED = "GRP_MEM_107"  # 移除成员失败
    CANNOT_REMOVE_OWNER = "GRP_MEM_108"  # 不能移除群主
    MISSING_REQUIRED_FIELD = "GRP_MEM_109"  # 缺少必填字段
    
    # 权限错误 (200-299)
    PERMISSION_DENIED = "GRP_PRM_200"  # 权限被拒绝
    NOT_GROUP_MEMBER = "GRP_PRM_201"  # 不是群组成员
    NOT_GROUP_ADMIN = "GRP_PRM_202"  # 不是群组管理员
    NOT_GROUP_OWNER = "GRP_PRM_203"  # 不是群组所有者


# 消息应用错误代码
class MessageErrorCodes:
    # 消息发送错误 (1-99)
    SEND_FAILED = "MSG_SND_001"  # 消息发送失败
    RECIPIENT_NOT_FOUND = "MSG_SND_002"  # 接收者不存在
    CONTENT_TOO_LARGE = "MSG_SND_003"  # 消息内容过大
    RATE_LIMIT_EXCEEDED = "MSG_SND_004"  # 发送频率超限
    
    # 消息格式错误 (100-199)
    INVALID_FORMAT = "MSG_FMT_100"  # 无效的消息格式
    INVALID_CONTENT_TYPE = "MSG_FMT_101"  # 无效的内容类型
    MISSING_REQUIRED_FIELD = "MSG_FMT_102"  # 缺少必填字段
    INVALID_JSON = "MSG_FMT_103"  # 无效的JSON格式
    
    # WebSocket错误 (200-299)
    SOCKET_CONNECTION_FAILED = "MSG_WSK_200"  # WebSocket连接失败
    SOCKET_DISCONNECTED = "MSG_WSK_201"  # WebSocket连接断开
    SOCKET_MESSAGE_FAILED = "MSG_WSK_202"  # WebSocket消息发送失败
    SOCKET_AUTH_FAILED = "MSG_WSK_203"  # WebSocket认证失败


# 通用系统错误代码
class SystemErrorCodes:
    # 系统级错误 (1-99)
    INTERNAL_ERROR = "SYS_INT_001"  # 内部服务器错误
    SERVICE_UNAVAILABLE = "SYS_INT_002"  # 服务不可用
    TIMEOUT = "SYS_INT_003"  # 请求超时
    RATE_LIMIT = "SYS_INT_004"  # 系统请求频率超限
    
    # 数据库错误 (100-199)
    DB_CONNECTION_ERROR = "SYS_DB_100"  # 数据库连接错误
    DB_QUERY_FAILED = "SYS_DB_101"  # 数据库查询失败
    DB_INTEGRITY_ERROR = "SYS_DB_102"  # 数据库完整性错误
    
    # 外部服务错误 (200-299)
    EXTERNAL_API_ERROR = "SYS_EXT_200"  # 外部API调用错误
    EXTERNAL_SERVICE_UNAVAILABLE = "SYS_EXT_201"  # 外部服务不可用 