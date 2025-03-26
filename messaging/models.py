from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

class Message(models.Model):
    """
    消息模型，用于存储系统中的所有消息
    """
    
    class MessageType(models.TextChoices):
        CHAT = 'chat', _('聊天消息')
        SYSTEM = 'system', _('系统消息')
        AGENT_RESPONSE = 'agent_response', _('代理响应')
        JOIN = 'join', _('加入消息')
        LEAVE = 'leave', _('离开消息')
        IMAGE = 'image', _('图片消息')
        FILE = 'file', _('文件消息')
        VOICE = 'voice', _('语音消息')
        RICH_TEXT = 'rich_text', _('富文本消息')
        MARKDOWN = 'markdown', _('Markdown消息')
        TASK = 'task', _('任务消息')
        TASK_UPDATE = 'task_update', _('任务更新')
        POLL = 'poll', _('投票消息')
        DECISION = 'decision', _('决策消息')
        HANDOFF = 'handoff', _('交接消息')
        ERROR = 'error', _('错误消息')
        STATUS = 'status', _('状态更新')
        SETTINGS = 'settings', _('设置变更')
    
    class SenderType(models.TextChoices):
        USER = 'user', _('用户')
        AGENT = 'agent', _('代理')
        SYSTEM = 'system', _('系统')
    
    # 基本字段
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_type = models.CharField(_('消息类型'), max_length=20, choices=MessageType.choices)
    content = models.JSONField(_('消息内容'))
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    
    # 发送者信息
    sender_type = models.CharField(_('发送者类型'), max_length=10, choices=SenderType.choices)
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_ws_messages',
        verbose_name=_('发送用户')
    )
    sender_agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_ws_messages',
        verbose_name=_('发送代理')
    )
    
    # 接收者信息（可以是群组或用户）
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ws_messages',
        verbose_name=_('接收群组')
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_ws_messages',
        verbose_name=_('接收用户')
    )
    
    # 附加信息
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('父消息')
    )
    metadata = models.JSONField(_('元数据'), default=dict, blank=True)
    
    # 提及的用户和代理
    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='mentioned_in_ws_messages',
        verbose_name=_('提及用户'),
        blank=True
    )
    mentioned_agents = models.ManyToManyField(
        'agents.Agent',
        related_name='mentioned_in_ws_messages',
        verbose_name=_('提及代理'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('消息')
        verbose_name_plural = _('消息')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['group']),
            models.Index(fields=['sender_user']),
            models.Index(fields=['sender_agent']),
            models.Index(fields=['recipient_user']),
        ]
    
    def __str__(self):
        return f"{self.get_message_type_display()} - {self.id}"
    
    def get_sender_name(self):
        """获取发送者名称"""
        if self.sender_type == self.SenderType.USER and self.sender_user:
            return self.sender_user.username
        elif self.sender_type == self.SenderType.AGENT and self.sender_agent:
            return self.sender_agent.name
        return '系统'
    
    def to_json_message(self):
        """将数据库记录转换为符合JSON Schema的消息格式"""
        result = {
            "message_id": str(self.id),
            "message_type": self.message_type,
            "sender": {
                "id": str(self.sender_user.id if self.sender_user else 
                       (self.sender_agent.id if self.sender_agent else "system")),
                "type": self.sender_type,
                "name": self.get_sender_name()
            },
            "timestamp": self.created_at.isoformat(),
            "payload": self.content,
            "metadata": self.metadata or {}
        }
        
        return result
    
    @classmethod
    def from_json_message(cls, json_message, save=True):
        """从JSON消息创建消息对象"""
        from django.contrib.auth import get_user_model
        from agents.models import Agent
        
        User = get_user_model()
        
        # 解析发送者
        sender = json_message.get("sender", {})
        sender_type = sender.get("type")
        sender_id = sender.get("id")
        
        # 初始化发送者对象
        sender_user = None
        sender_agent = None
        
        if sender_type == cls.SenderType.USER:
            try:
                sender_user = User.objects.get(id=sender_id)
            except (User.DoesNotExist, ValueError):
                pass
        elif sender_type == cls.SenderType.AGENT:
            try:
                sender_agent = Agent.objects.get(id=sender_id)
            except (Agent.DoesNotExist, ValueError):
                pass
        
        # 创建消息对象
        message = cls(
            id=uuid.UUID(json_message.get("message_id")) if "message_id" in json_message else uuid.uuid4(),
            message_type=json_message.get("message_type"),
            content=json_message.get("payload", {}),
            sender_type=sender_type,
            sender_user=sender_user,
            sender_agent=sender_agent,
            metadata=json_message.get("metadata", {})
        )
        
        # 处理群组ID
        group_id = json_message.get("payload", {}).get("group_id")
        if group_id:
            from groups.models import Group
            try:
                message.group = Group.objects.get(id=group_id)
            except (Group.DoesNotExist, ValueError):
                pass
        
        # 处理回复消息
        reply_to = json_message.get("payload", {}).get("reply_to")
        if reply_to:
            try:
                message.parent_message = cls.objects.get(id=reply_to)
            except (cls.DoesNotExist, ValueError):
                pass
        
        # 保存消息
        if save:
            message.save()
            
            # 处理提及
            mentions = json_message.get("payload", {}).get("mentions", [])
            for mention in mentions:
                mention_type = mention.get("type")
                mention_id = mention.get("id")
                
                if mention_type == cls.SenderType.USER:
                    try:
                        user = User.objects.get(id=mention_id)
                        message.mentioned_users.add(user)
                    except (User.DoesNotExist, ValueError):
                        pass
                elif mention_type == cls.SenderType.AGENT:
                    try:
                        agent = Agent.objects.get(id=mention_id)
                        message.mentioned_agents.add(agent)
                    except (Agent.DoesNotExist, ValueError):
                        pass
                        
        return message


class MessageDeliveryStatus(models.Model):
    """
    消息传递状态模型，用于跟踪消息的发送、接收和阅读状态
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='delivery_statuses',
        verbose_name=_('消息')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_statuses',
        verbose_name=_('用户')
    )
    is_delivered = models.BooleanField(_('是否送达'), default=False)
    delivered_at = models.DateTimeField(_('送达时间'), null=True, blank=True)
    is_read = models.BooleanField(_('是否已读'), default=False)
    read_at = models.DateTimeField(_('阅读时间'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('消息传递状态')
        verbose_name_plural = _('消息传递状态')
        unique_together = [['message', 'user']]
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        status = "已读" if self.is_read else ("已送达" if self.is_delivered else "未送达")
        return f"{self.message} - {self.user.username} - {status}"
