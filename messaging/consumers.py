import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import datetime
import logging
import asyncio
from django.contrib.auth import get_user_model

from .validators import validate_message, create_message
from .models import Message, MessageDeliveryStatus
from .serializers import MessageSerializer
from agents.services import RuleEngine  # 导入规则引擎
from agents.models import Agent  # 导入Agent模型
from chatbot_platform.error_utils import format_websocket_error  # 导入错误处理工具
from chatbot_platform.error_codes import MessageErrorCodes  # 导入消息错误代码
from agents.async_processor import message_processor  # 导入异步消息处理器

logger = logging.getLogger(__name__)
User = get_user_model()

class MessageConsumer(AsyncWebsocketConsumer):
    """
    WebSocket消费者，处理实时消息
    """
    
    async def connect(self):
        """
        处理WebSocket连接请求
        """
        self.user = self.scope["user"]
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        
        # 测试阶段允许匿名用户连接
        is_test_mode = True  # 在生产环境中设置为False
        
        # 检查用户身份
        if self.user.is_anonymous and not is_test_mode:
            # 在实际应用中，拒绝匿名用户
            logger.warning(
                f"拒绝匿名用户WebSocket连接: {self.room_name}", 
                extra={'data': {'room': self.room_name}}
            )
            await self.close()
            return
            
        # 记录连接信息
        if self.user.is_anonymous:
            logger.info(
                f"匿名用户连接到房间: {self.room_name}", 
                extra={'data': {'room': self.room_name}}
            )
        else:
            logger.info(
                f"用户 {self.user.username} 连接到房间: {self.room_name}",
                extra={'data': {'room': self.room_name, 'user_id': self.user.id, 'username': self.user.username}}
            )
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # 接受WebSocket连接
        await self.accept()
        
        # 发送连接确认消息
        connect_ack = create_message(
            message_type="connect_ack",
            sender={
                "id": "system",
                "type": "system",
                "name": "系统"
            },
            payload={
                "session_id": str(uuid.uuid4()),
                "server_info": {
                    "version": "1.0.0",
                    "features": ["typing_indicators", "read_receipts"]
                },
                "user_info": {
                    "id": str(self.user.id) if not self.user.is_anonymous else "anonymous",
                    "name": self.user.username if not self.user.is_anonymous else "访客",
                    "permissions": ["read", "write"]
                }
            },
            metadata={
                "protocol_version": "1.0"
            }
        )
        
        await self.send(text_data=json.dumps(connect_ack))
        
        # 发送历史消息（最近10条）
        history_messages = await self.get_history_messages(self.room_name, 10)
        for message in history_messages:
            await self.send(text_data=json.dumps(message.to_json_message()))
    
    async def disconnect(self, close_code):
        """
        处理WebSocket连接断开
        """
        # 记录断开连接信息
        user_info = f"用户 {self.user.username}" if not self.user.is_anonymous else "匿名用户"
        logger.info(
            f"{user_info} 断开房间: {self.room_name} 连接, 代码: {close_code}",
            extra={'data': {'room': self.room_name, 'code': close_code}}
        )
        
        # 离开房间组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        接收WebSocket消息
        """
        try:
            # 解析消息
            text_data_json = json.loads(text_data)
            
            # 验证消息格式
            is_valid, error = validate_message(text_data_json)
            if not is_valid:
                await self.send_error(MessageErrorCodes.INVALID_FORMAT, error)
                return
            
            # 处理不同类型的消息
            message_type = text_data_json.get("message_type")
            
            if message_type == "ping":
                # 心跳检测，回复pong
                await self.send(text_data=json.dumps({
                    "message_id": str(uuid.uuid4()),
                    "message_type": "pong",
                    "sender": {
                        "id": "system",
                        "type": "system",
                        "name": "系统"
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {},
                    "metadata": {}
                }))
                return
            
            elif message_type == "typing":
                # 转发输入状态消息
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "broadcast_message",
                        "message": text_data_json
                    }
                )
                return
                
            elif message_type == "read_receipt":
                # 处理已读回执
                await self.process_read_receipt(text_data_json)
                return
            
            # 处理普通消息（chat、image、file等）
            # 1. 验证发送者是否是当前用户
            sender = text_data_json.get("sender", {})
            
            # 测试模式下允许匿名用户发送消息
            is_test_mode = True  # 在生产环境中设置为False
            
            if sender.get("type") == "user":
                # 验证发送者ID
                if not is_test_mode and str(sender.get("id")) != str(self.user.id):
                    await self.send_error(
                        MessageErrorCodes.INVALID_FORMAT, 
                        "消息发送者ID与当前用户不匹配"
                    )
                    return
                    
            # 2. 保存消息到数据库
            message = await self.save_message(text_data_json)
            
            # 3. 广播消息到房间所有成员
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_message",
                    "message": message.to_json_message()
                }
            )
            
            # 4. 如果是群组消息，处理代理响应
            await self.process_agent_responses(message)
            
        except json.JSONDecodeError:
            await self.send_error(MessageErrorCodes.INVALID_JSON, "无效的JSON格式")
        except Exception as e:
            logger.error(
                f"处理WebSocket消息时发生错误: {str(e)}", 
                exc_info=True,
                extra={'data': {'exception': str(e)}}
            )
            await self.send_error(MessageErrorCodes.SEND_FAILED, f"内部错误: {str(e)}")
    
    async def broadcast_message(self, event):
        """
        广播消息到WebSocket
        """
        message = event["message"]
        
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps(message))
    
    async def send_error(self, code, text):
        """
        发送错误消息
        """
        # 使用统一的错误格式
        error_message = format_websocket_error(
            error_code=code,
            message=text
        )
        
        # 添加其他必要字段
        error_message.update({
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sender": {
                "id": "system",
                "type": "system",
                "name": "系统"
            },
            "payload": {
                "text": text,
                "severity": "error"
            },
            "metadata": {}
        })
        
        # 记录错误日志
        logger.error(
            f"WebSocket错误: [{code}] {text}",
            extra={'data': {'error_code': code, 'error_message': text, 'room': self.room_name}}
        )
        
        await self.send(text_data=json.dumps(error_message))
    
    @database_sync_to_async
    def save_message(self, message_data):
        """
        保存消息到数据库
        """
        # 测试模式判断
        is_test_mode = True
        
        try:
            # 创建消息对象
            message = Message.from_json_message(message_data)
            
            # 测试模式下，如果sender_user为空（匿名用户），跳过创建传递状态记录
            if is_test_mode and self.user.is_anonymous:
                return message
                
            # 创建消息传递状态记录
            if message.group:
                # 是群组消息，为所有群组成员创建状态记录
                for member in message.group.get_human_members():
                    if member.user.id != self.user.id:  # 不给发送者自己创建记录
                        MessageDeliveryStatus.objects.create(
                            message=message,
                            user=member.user,
                            is_delivered=True,
                            delivered_at=timezone.now()
                        )
            elif message.recipient_user:
                # 是私聊消息，为接收者创建状态记录
                MessageDeliveryStatus.objects.create(
                    message=message,
                    user=message.recipient_user,
                    is_delivered=True,
                    delivered_at=timezone.now()
                )
            
            return message
        except Exception as e:
            logger.error(f"保存消息到数据库失败: {str(e)}")
            # 在测试模式下，尝试创建一个没有数据库记录的消息对象
            if is_test_mode:
                return Message()
            raise
    
    @database_sync_to_async
    def get_history_messages(self, room_name, limit=10):
        """
        获取历史消息
        """
        # 判断room_name是否为群组ID
        from groups.models import Group
        try:
            group = Group.objects.get(id=room_name)
            # 是群组，获取群组消息
            return list(Message.objects.filter(
                group=group
            ).order_by('-created_at')[:limit])
        except (Group.DoesNotExist, ValueError):
            # 不是群组，尝试作为私聊处理（user1_user2格式）
            try:
                user_ids = room_name.split('_')
                if len(user_ids) == 2:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user1 = User.objects.get(id=user_ids[0])
                    user2 = User.objects.get(id=user_ids[1])
                    
                    # 获取两个用户之间的消息
                    return list(Message.objects.filter(
                        (models.Q(sender_user=user1) & models.Q(recipient_user=user2)) |
                        (models.Q(sender_user=user2) & models.Q(recipient_user=user1))
                    ).order_by('-created_at')[:limit])
                    
            except:
                pass
        
        # 默认返回空列表
        return []
    
    @database_sync_to_async
    def process_read_receipt(self, read_receipt):
        """
        处理已读回执
        """
        try:
            message_ids = read_receipt.get("payload", {}).get("message_ids", [])
            if not message_ids:
                return
                
            # 更新消息状态为已读
            statuses = MessageDeliveryStatus.objects.filter(
                message__id__in=message_ids,
                user=self.user
            )
            
            for status in statuses:
                if not status.is_read:
                    status.is_read = True
                    status.read_at = timezone.now()
                    status.save()
                    
        except Exception as e:
            logger.error(f"处理已读回执时发生错误: {str(e)}")
    
    async def process_agent_responses(self, message):
        """
        处理代理响应，如果消息中@了代理，则触发代理响应
        同时使用规则引擎处理消息和异步处理器
        """
        # 1. 检查是否是群组消息
        if not message.group:
            return
            
        # 2. 将消息转换为规则引擎可处理的格式
        message_for_rule = {
            'id': str(message.id),
            'content': message.content.get('text', ''),
            'message_type': message.message_type,
            'sender': str(message.sender_user.id) if message.sender_user else None,
            'group_id': str(message.group.id) if message.group else None,
            'mentions': [str(agent.id) for agent in message.mentioned_agents.all()],
            'timestamp': message.timestamp.isoformat()
        }
        
        # 3. 定义上下文
        context = {
            'group_id': str(message.group.id) if message.group else None,
            'is_group_message': bool(message.group),
            'message_id': str(message.id),
            'room_group_name': self.room_group_name,
            'channel_layer': self.channel_layer
        }
        
        # 4. 使用异步消息处理器处理消息
        await database_sync_to_async(message_processor.add_message)(
            message=message_for_rule, 
            context=context, 
            callback=self.handle_agent_responses_callback
        )
        
        # 5. 检查是否提及了代理（旧的处理方式，保留做后向兼容）
        if not message.mentioned_agents.exists():
            return
        
        # 6. 为每个被提及的代理创建响应任务
        mentioned_agents = message.mentioned_agents.all()
        for agent in mentioned_agents:
            # 异步处理，避免阻塞WebSocket
            asyncio.create_task(self.generate_agent_response(message, agent))

    @database_sync_to_async
    def handle_agent_responses_callback(self, responses):
        """
        处理代理响应的回调函数
        
        参数:
        - responses: 规则引擎生成的响应列表
        """
        if not responses:
            return
        
        logger.info(f"收到 {len(responses)} 个代理响应")
        
        # 这里可以做额外的处理，例如记录响应到数据库等
        # 注意：实际的响应发送由异步处理器完成

    async def process_rule_engine_responses(self, message, context):
        """
        使用规则引擎处理消息并发送响应
        
        参数:
        - message: 消息数据
        - context: 上下文信息
        """
        try:
            # 调用规则引擎处理消息
            responses = await database_sync_to_async(RuleEngine.process_message)(message, context)
            
            if not responses:
                return
                
            # 为每个响应创建并发送消息
            for response in responses:
                # 获取响应的代理
                agent_id = response.get('agent_id')
                if not agent_id:
                    continue
                    
                # 异步获取代理对象
                agent = await database_sync_to_async(lambda: Agent.objects.get(id=agent_id))()
                
                # 创建响应消息
                response_message = create_message(
                    message_type="agent_response",
                    sender={
                        "id": str(agent.id),
                        "type": "agent",
                        "name": agent.name
                    },
                    payload={
                        "text": response.get('content', '无响应内容'),
                        "group_id": context.get('group_id'),
                        "reply_to": context.get('message_id'),
                        "confidence": response.get('confidence', 0.9),
                        "rule_id": response.get('rule_id')
                    },
                    metadata={
                        "rule_engine": "v1.0",
                        "rule_name": response.get('rule_name', '未知规则')
                    }
                )
                
                # 保存到数据库
                await database_sync_to_async(
                    lambda: Message.from_json_message(response_message)
                )()
                
                # 广播响应消息
                await self.channel_layer.group_send(
                    context.get('room_group_name', self.room_group_name),
                    {
                        "type": "broadcast_message",
                        "message": response_message
                    }
                )
                
        except Exception as e:
            logger.error(f"规则引擎处理消息时发生错误: {str(e)}", exc_info=True)
            
            # 发送错误消息
            error_message = create_message(
                message_type="error",
                sender={
                    "id": "system",
                    "type": "system",
                    "name": "系统"
                },
                payload={
                    "code": "rule_engine_error",
                    "text": f"规则引擎处理失败: {str(e)}",
                    "severity": "error"
                }
            )
            
            await self.channel_layer.group_send(
                context.get('room_group_name', self.room_group_name),
                {
                    "type": "broadcast_message",
                    "message": error_message
                }
            )
    
    async def generate_agent_response(self, message, agent):
        """
        生成代理响应
        """
        # 等待一段时间，模拟代理思考
        await asyncio.sleep(1)
        
        try:
            # 获取消息文本内容
            message_text = message.content.get('text', '')
            
            # 先发送一个"正在思考"的消息
            thinking_message = create_message(
                message_type="agent_response",
                sender={
                    "id": str(agent.id),
                    "type": "agent",
                    "name": agent.name
                },
                payload={
                    "text": f"[正在思考...]",
                    "group_id": str(message.group.id),
                    "reply_to": str(message.id),
                    "confidence": 0.95,
                    "is_thinking": True
                },
                metadata={
                    "model": "default",
                    "response_type": "thinking"
                }
            )
            
            # 广播思考消息
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_message",
                    "message": thinking_message
                }
            )
            
            # 异步获取代理系统提示
            system_prompt = await database_sync_to_async(lambda: agent.system_prompt or f"你是{agent.name}，一个AI助手。")()
            
            # 为了演示，这里使用简单逻辑生成响应
            # 实际项目中应当调用AI模型API
            response_text = await self.get_agent_response(agent, message_text, system_prompt)
            
            # 创建最终响应消息
            response_message = create_message(
                message_type="agent_response",
                sender={
                    "id": str(agent.id),
                    "type": "agent",
                    "name": agent.name
                },
                payload={
                    "text": response_text,
                    "group_id": str(message.group.id),
                    "reply_to": str(message.id),
                    "confidence": 0.95,
                    "is_thinking": False
                },
                metadata={
                    "model": agent.model_config.get('model', 'default') if isinstance(agent.model_config, dict) else 'default',
                    "response_time_ms": 1000,
                    "response_type": "final"
                }
            )
            
            # 保存到数据库
            agent_message = await database_sync_to_async(
                lambda: Message.from_json_message(response_message)
            )()
            
            # 广播响应消息
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_message",
                    "message": response_message
                }
            )
            
        except Exception as e:
            logger.error(f"生成代理响应时发生错误: {str(e)}")
            
            # 发送错误消息
            error_message = create_message(
                message_type="error",
                sender={
                    "id": "system",
                    "type": "system",
                    "name": "系统"
                },
                payload={
                    "code": "agent_error",
                    "text": f"代理 {agent.name} 响应失败: {str(e)}",
                    "severity": "error",
                    "details": f"请求ID: {str(message.id)}"
                }
            )
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "broadcast_message",
                    "message": error_message
                }
            )
    
    async def get_agent_response(self, agent, user_message, system_prompt):
        """
        获取代理响应内容
        这里是示例实现，实际项目中应该调用AI API
        """
        # 简单示例响应，实际项目中应该调用LLM API
        import random
        
        # 根据代理角色生成不同风格的回复
        role_responses = {
            'product_manager': [
                f"从产品角度看，我认为{user_message.split()[-3:] if len(user_message.split()) > 3 else user_message}值得我们关注。",
                "我们应该从用户需求出发，思考如何优化这个功能。",
                "这个问题需要我们进一步调研市场情况。"
            ],
            'frontend_dev': [
                "这个UI组件可以使用React实现，我可以帮你写代码。",
                "前端实现上，我们需要考虑响应式设计和兼容性问题。",
                "这个交互效果需要JavaScript和CSS动画配合实现。"
            ],
            'backend_dev': [
                "后端架构上，我建议使用微服务设计。",
                "这个功能可以通过RESTful API实现，我来设计接口。",
                "数据库选型上，考虑到性能需求，我推荐使用PostgreSQL。"
            ],
            'custom': [
                f"我理解你的问题是关于\"{user_message[:20]}...\"，让我来回答。",
                "我会尽力帮助你解决这个问题。",
                "这是个有趣的问题，让我思考一下。"
            ]
        }
        
        # 获取代理角色，如果不存在则使用custom
        role = agent.role if hasattr(agent, 'role') and agent.role in role_responses else 'custom'
        
        # 随机选择一个响应
        return random.choice(role_responses[role])

    async def agent_message(self, event):
        """
        处理代理消息事件
        
        参数:
        - event: 事件数据，包含代理响应消息
        """
        try:
            message = event.get('message', {})
            
            # 记录代理响应消息
            logger.info(
                f"接收到代理响应: {message.get('content', '')[:50]}...",
                extra={'data': {'message': message}}
            )
            
            # 发送消息到WebSocket客户端
            await self.send(text_data=json.dumps(message))
            
        except Exception as e:
            logger.error(f"处理代理消息时发生错误: {str(e)}", exc_info=True)
            
    async def agent_notification(self, event):
        """
        处理代理通知事件
        
        参数:
        - event: 事件数据，包含通知消息
        """
        try:
            message = event.get('message', {})
            
            # 记录通知消息
            logger.info(
                f"接收到代理通知: {message.get('payload', {}).get('text', '')[:50]}...",
                extra={'data': {'message': message}}
            )
            
            # 发送消息到WebSocket客户端
            await self.send(text_data=json.dumps(message))
            
        except Exception as e:
            logger.error(f"处理代理通知时发生错误: {str(e)}", exc_info=True)
            
    async def agent_task_created(self, event):
        """
        处理代理任务创建事件
        
        参数:
        - event: 事件数据，包含任务创建信息
        """
        try:
            message = event.get('message', {})
            
            # 记录任务创建消息
            logger.info(
                f"接收到任务创建: {message.get('payload', {}).get('task_title', '')}",
                extra={'data': {'message': message}}
            )
            
            # 发送消息到WebSocket客户端
            await self.send(text_data=json.dumps(message))
            
        except Exception as e:
            logger.error(f"处理任务创建时发生错误: {str(e)}", exc_info=True)
            
    async def agent_action_result(self, event):
        """
        处理代理动作结果事件
        
        参数:
        - event: 事件数据，包含动作执行结果
        """
        try:
            message = event.get('message', {})
            
            # 记录动作结果消息
            logger.info(
                f"接收到动作结果: {message.get('payload', {}).get('action_name', '')}",
                extra={'data': {'message': message}}
            )
            
            # 发送消息到WebSocket客户端
            await self.send(text_data=json.dumps(message))
            
        except Exception as e:
            logger.error(f"处理动作结果时发生错误: {str(e)}", exc_info=True) 