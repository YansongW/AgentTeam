import json
import uuid
from datetime import datetime
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger(__name__)

# 基本消息Schema
BASE_MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message_type", "sender", "timestamp", "payload"],
    "properties": {
        "message_id": {"type": "string", "format": "uuid"},
        "message_type": {"type": "string"},
        "sender": {
            "type": "object",
            "required": ["id", "type", "name"],
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["user", "agent", "system"]},
                "name": {"type": "string"}
            }
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "payload": {"type": "object"},
        "metadata": {"type": "object"}
    }
}

# 聊天消息Schema
CHAT_MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message_type", "sender", "timestamp", "payload"],
    "properties": {
        "message_id": {"type": "string", "format": "uuid"},
        "message_type": {"type": "string", "enum": ["chat"]},
        "sender": {
            "type": "object",
            "required": ["id", "type", "name"],
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["user", "agent"]},
                "name": {"type": "string"}
            }
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "payload": {
            "type": "object",
            "required": ["text", "group_id"],
            "properties": {
                "text": {"type": "string"},
                "group_id": {"type": "string"},
                "reply_to": {"type": "string"},
                "mentions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "type", "name"],
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string", "enum": ["user", "agent"]},
                            "name": {"type": "string"}
                        }
                    }
                }
            }
        },
        "metadata": {"type": "object"}
    }
}

# 代理响应消息Schema
AGENT_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["message_type", "sender", "timestamp", "payload"],
    "properties": {
        "message_id": {"type": "string", "format": "uuid"},
        "message_type": {"type": "string", "enum": ["agent_response"]},
        "sender": {
            "type": "object",
            "required": ["id", "type", "name"],
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["agent"]},
                "name": {"type": "string"}
            }
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "payload": {
            "type": "object",
            "required": ["text", "group_id", "reply_to"],
            "properties": {
                "text": {"type": "string"},
                "group_id": {"type": "string"},
                "reply_to": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "thinking": {"type": "string"},
                "sources": {"type": "array"}
            }
        },
        "metadata": {"type": "object"}
    }
}

# 系统消息Schema
SYSTEM_MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message_type", "sender", "timestamp", "payload"],
    "properties": {
        "message_id": {"type": "string", "format": "uuid"},
        "message_type": {"type": "string", "enum": ["system"]},
        "sender": {
            "type": "object",
            "required": ["id", "type", "name"],
            "properties": {
                "id": {"type": "string", "enum": ["system"]},
                "type": {"type": "string", "enum": ["system"]},
                "name": {"type": "string", "enum": ["系统"]}
            }
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "payload": {
            "type": "object",
            "required": ["text", "group_id", "event_type"],
            "properties": {
                "text": {"type": "string"},
                "group_id": {"type": "string"},
                "event_type": {"type": "string"},
                "subject": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                        "name": {"type": "string"}
                    }
                }
            }
        },
        "metadata": {"type": "object"}
    }
}

# 连接消息Schema
CONNECT_MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message_type", "sender", "timestamp", "payload"],
    "properties": {
        "message_id": {"type": "string", "format": "uuid"},
        "message_type": {"type": "string", "enum": ["connect"]},
        "sender": {
            "type": "object",
            "required": ["id", "type", "name"],
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["user"]},
                "name": {"type": "string"}
            }
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "payload": {
            "type": "object",
            "required": ["client_info", "auth_token"],
            "properties": {
                "client_info": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string"},
                        "browser": {"type": "string"},
                        "version": {"type": "string"}
                    }
                },
                "auth_token": {"type": "string"}
            }
        },
        "metadata": {"type": "object"}
    }
}

# 消息类型到Schema的映射
MESSAGE_SCHEMAS = {
    "chat": CHAT_MESSAGE_SCHEMA,
    "agent_response": AGENT_RESPONSE_SCHEMA,
    "system": SYSTEM_MESSAGE_SCHEMA,
    "connect": CONNECT_MESSAGE_SCHEMA,
    # 其他消息类型可以添加到这里
}

def validate_message(message_data, message_type=None):
    """
    验证消息是否符合指定类型的Schema
    
    Args:
        message_data: 要验证的消息数据（字典或JSON字符串）
        message_type: 消息类型（可选，如果不提供则从message_data中获取）
        
    Returns:
        (bool, str): 包含验证结果和错误信息的元组
    """
    # 如果输入是JSON字符串，转换为字典
    if isinstance(message_data, str):
        try:
            message_data = json.loads(message_data)
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {str(e)}"
    
    # 确定消息类型
    if not message_type:
        message_type = message_data.get("message_type")
        
    if not message_type:
        return False, "消息缺少message_type字段"
    
    # 选择正确的Schema
    schema = MESSAGE_SCHEMAS.get(message_type, BASE_MESSAGE_SCHEMA)
    
    try:
        validate(instance=message_data, schema=schema)
        return True, ""
    except ValidationError as e:
        error_message = f"消息验证失败: {e.message}"
        logger.error(error_message)
        return False, error_message

def generate_message_id():
    """生成唯一的消息ID"""
    return str(uuid.uuid4())

def create_message(message_type, sender, payload, metadata=None):
    """
    创建一个新的消息对象
    
    Args:
        message_type: 消息类型
        sender: 发送者信息字典，包含id、type和name
        payload: 消息内容字典
        metadata: 元数据字典（可选）
        
    Returns:
        dict: 符合Schema的消息字典
    """
    message = {
        "message_id": generate_message_id(),
        "message_type": message_type,
        "sender": sender,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
        "metadata": metadata or {}
    }
    
    # 验证消息
    is_valid, error = validate_message(message)
    if not is_valid:
        logger.error(f"创建的消息无效: {error}")
        raise ValueError(f"创建的消息无效: {error}")
    
    return message 