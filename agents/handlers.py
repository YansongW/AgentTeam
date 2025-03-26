"""
代理响应处理器

定义各种类型响应的异步处理函数
"""

import logging
import json
import asyncio
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer

from .async_processor import message_processor
from groups.models import GroupMessage, Group
from .models import Agent, AgentListeningRule, AgentInteraction

logger = logging.getLogger(__name__)

# 获取公共的channel_layer
channel_layer = get_channel_layer()

async def auto_reply_handler(response, context):
    """
    处理自动回复类型的响应
    
    参数:
    - response: 规则引擎生成的响应数据
    - context: 上下文信息
    """
    try:
        # 记录自动回复
        logger.info(
            f"处理自动回复: {response.get('content', '')[:50]}...",
            extra={'response': response, 'context': context}
        )
        
        group_id = context.get('group_id')
        if not group_id:
            logger.warning("自动回复缺少群组ID")
            return
        
        # 创建消息内容
        agent_id = response.get('agent_id')
        content = response.get('content', '无内容')
        
        # 生成消息对象字典
        message_data = {
            'type': 'agent.message',
            'message': {
                'id': str(timezone.now().timestamp()),
                'message_type': 'agent_response',
                'sender': {
                    'id': agent_id,
                    'type': 'agent',
                    'name': response.get('agent_name', '代理')
                },
                'payload': {
                    'text': content,
                    'rule_id': response.get('rule_id'),
                    'rule_name': response.get('rule_name'),
                    'message_id': context.get('message_id'),
                    'confidence': response.get('confidence', 1.0)
                },
                'timestamp': timezone.now().isoformat(),
                'metadata': {
                    'response_type': 'auto_reply',
                    'rule_engine': 'v1.0'
                }
            }
        }
        
        # 发送到群组
        room_group_name = f"group_{group_id}"
        await channel_layer.group_send(room_group_name, message_data)
        
    except Exception as e:
        logger.error(f"处理自动回复响应时出错: {str(e)}", exc_info=True)

async def notification_handler(response, context):
    """
    处理通知类型的响应
    
    参数:
    - response: 规则引擎生成的响应数据
    - context: 上下文信息
    """
    try:
        # 记录通知
        logger.info(
            f"处理通知: {response.get('content', '')[:50]}...",
            extra={'response': response, 'context': context}
        )
        
        group_id = context.get('group_id')
        if not group_id:
            logger.warning("通知缺少群组ID")
            return
        
        # 创建通知内容
        agent_id = response.get('agent_id')
        content = response.get('content', '无内容')
        
        # 生成通知对象字典
        notification_data = {
            'type': 'agent.notification',
            'message': {
                'id': str(timezone.now().timestamp()),
                'message_type': 'notification',
                'sender': {
                    'id': agent_id,
                    'type': 'agent',
                    'name': response.get('agent_name', '代理')
                },
                'payload': {
                    'text': content,
                    'rule_id': response.get('rule_id'),
                    'severity': 'info',
                    'message_id': context.get('message_id')
                },
                'timestamp': timezone.now().isoformat(),
                'metadata': {
                    'response_type': 'notification',
                    'rule_engine': 'v1.0'
                }
            }
        }
        
        # 发送到群组
        room_group_name = f"group_{group_id}"
        await channel_layer.group_send(room_group_name, notification_data)
        
    except Exception as e:
        logger.error(f"处理通知响应时出错: {str(e)}", exc_info=True)

async def task_handler(response, context):
    """
    处理任务创建类型的响应
    
    参数:
    - response: 规则引擎生成的响应数据
    - context: 上下文信息
    """
    try:
        # 记录任务创建
        logger.info(
            f"处理任务创建: {response.get('task_title', '')[:50]}...",
            extra={'response': response, 'context': context}
        )
        
        group_id = context.get('group_id')
        if not group_id:
            logger.warning("任务创建缺少群组ID")
            return
        
        # 这里应该实现任务创建的实际逻辑
        # TODO: 集成任务管理系统API
        
        # 生成任务创建通知
        task_notification = {
            'type': 'agent.task_created',
            'message': {
                'id': str(timezone.now().timestamp()),
                'message_type': 'task_created',
                'sender': {
                    'id': response.get('agent_id'),
                    'type': 'agent',
                    'name': response.get('agent_name', '代理')
                },
                'payload': {
                    'task_title': response.get('task_title', '新任务'),
                    'task_description': response.get('task_description', ''),
                    'rule_id': response.get('rule_id'),
                    'message_id': context.get('message_id')
                },
                'timestamp': timezone.now().isoformat(),
                'metadata': {
                    'response_type': 'task',
                    'rule_engine': 'v1.0'
                }
            }
        }
        
        # 发送到群组
        room_group_name = f"group_{group_id}"
        await channel_layer.group_send(room_group_name, task_notification)
        
    except Exception as e:
        logger.error(f"处理任务创建响应时出错: {str(e)}", exc_info=True)

async def action_handler(response, context):
    """
    处理执行动作类型的响应
    
    参数:
    - response: 规则引擎生成的响应数据
    - context: 上下文信息
    """
    try:
        # 记录动作执行
        logger.info(
            f"处理动作执行: {response.get('action_name', '')}",
            extra={'response': response, 'context': context}
        )
        
        # 获取动作参数
        action_name = response.get('action_name', '')
        action_params = response.get('action_params', {})
        
        # 根据不同的动作名称执行不同的操作
        if action_name == 'summarize_conversation':
            # 执行对话总结
            await execute_summarize_action(response, context)
        elif action_name == 'search_knowledge_base':
            # 搜索知识库
            await execute_search_action(response, context)
        else:
            logger.warning(f"未知的动作类型: {action_name}")
            
    except Exception as e:
        logger.error(f"处理动作响应时出错: {str(e)}", exc_info=True)

async def execute_summarize_action(response, context):
    """执行对话总结动作"""
    # 实际环境中，可能会调用AI接口生成摘要
    group_id = context.get('group_id')
    
    # 模拟总结过程
    await asyncio.sleep(2)
    
    # 发送总结结果
    summary_message = {
        'type': 'agent.action_result',
        'message': {
            'id': str(timezone.now().timestamp()),
            'message_type': 'action_result',
            'sender': {
                'id': response.get('agent_id'),
                'type': 'agent',
                'name': response.get('agent_name', '代理')
            },
            'payload': {
                'action_name': 'summarize_conversation',
                'text': "我已经总结了最近的对话: 这里是模拟的总结内容...",
                'message_id': context.get('message_id')
            },
            'timestamp': timezone.now().isoformat(),
            'metadata': {
                'response_type': 'action',
                'action': 'summarize_conversation',
                'rule_engine': 'v1.0'
            }
        }
    }
    
    # 发送到群组
    room_group_name = f"group_{group_id}"
    await channel_layer.group_send(room_group_name, summary_message)

async def execute_search_action(response, context):
    """执行知识库搜索动作"""
    # 实际环境中，可能会调用搜索API
    group_id = context.get('group_id')
    
    # 模拟搜索过程
    await asyncio.sleep(1)
    
    # 发送搜索结果
    search_message = {
        'type': 'agent.action_result',
        'message': {
            'id': str(timezone.now().timestamp()),
            'message_type': 'action_result',
            'sender': {
                'id': response.get('agent_id'),
                'type': 'agent',
                'name': response.get('agent_name', '代理')
            },
            'payload': {
                'action_name': 'search_knowledge_base',
                'text': "我在知识库中找到了以下相关信息: 这里是模拟的搜索结果...",
                'message_id': context.get('message_id')
            },
            'timestamp': timezone.now().isoformat(),
            'metadata': {
                'response_type': 'action',
                'action': 'search_knowledge_base',
                'rule_engine': 'v1.0'
            }
        }
    }
    
    # 发送到群组
    room_group_name = f"group_{group_id}"
    await channel_layer.group_send(room_group_name, search_message)

def register_handlers():
    """注册各种响应类型的处理函数"""
    message_processor.register_handler('auto_reply', auto_reply_handler)
    message_processor.register_handler('notification', notification_handler)
    message_processor.register_handler('task', task_handler)
    message_processor.register_handler('action', action_handler)
    message_processor.register_handler('custom', auto_reply_handler)  # 默认处理方式同auto_reply
    
    logger.info("已注册所有响应类型处理函数") 