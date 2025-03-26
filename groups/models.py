from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from agents.models import Agent

class Group(models.Model):
    """
    群组模型，用于组织多个代理和用户进行群聊和协作
    
    字段说明:
    - name: 群组名称
    - description: 群组描述
    - owner: 群组创建者/所有者
    - is_public: 是否是公开群组
    - created_at: 创建时间
    - updated_at: 更新时间
    - avatar: 群组头像
    - settings: 群组设置，如消息通知规则、加入规则等
    """
    
    name = models.CharField(_('群组名称'), max_length=100)
    description = models.TextField(_('群组描述'), blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_groups',
        verbose_name=_('所有者')
    )
    is_public = models.BooleanField(_('是否公开'), default=False)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    avatar = models.ImageField(_('群组头像'), upload_to='group_avatars/', blank=True, null=True)
    group_settings = models.JSONField(_('群组设置'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('群组')
        verbose_name_plural = _('群组')
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def get_member_count(self):
        """获取群组成员数量"""
        return self.members.count()
    
    def get_active_agents(self):
        """获取群组中的活跃代理"""
        return Agent.objects.filter(
            id__in=self.members.filter(
                member_type=GroupMember.MemberType.AGENT,
                is_active=True
            ).values_list('agent_id', flat=True)
        )
    
    def get_human_members(self):
        """获取群组中的人类成员"""
        return self.members.filter(
            member_type=GroupMember.MemberType.HUMAN,
            is_active=True
        )


class GroupMember(models.Model):
    """
    群组成员关系模型，用于管理用户和代理与群组的关系
    
    字段说明:
    - group: 所属群组
    - user: 用户成员（如果是人类）
    - agent: 代理成员（如果是AI代理）
    - member_type: 成员类型（人类或AI代理）
    - role: 成员角色（普通成员、管理员等）
    - joined_at: 加入时间
    - is_active: 是否活跃
    - settings: 成员个人设置，如通知偏好等
    """
    
    class MemberType(models.TextChoices):
        HUMAN = 'human', _('人类')
        AGENT = 'agent', _('AI代理')
    
    class Role(models.TextChoices):
        MEMBER = 'member', _('成员')
        ADMIN = 'admin', _('管理员')
        OBSERVER = 'observer', _('观察者')
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_('群组')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name=_('用户'),
        null=True,
        blank=True
    )
    agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name=_('代理'),
        null=True,
        blank=True
    )
    member_type = models.CharField(
        _('成员类型'),
        max_length=10,
        choices=MemberType.choices,
        default=MemberType.HUMAN
    )
    role = models.CharField(
        _('角色'),
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_at = models.DateTimeField(_('加入时间'), auto_now_add=True)
    is_active = models.BooleanField(_('是否活跃'), default=True)
    member_settings = models.JSONField(_('成员设置'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('群组成员')
        verbose_name_plural = _('群组成员')
        unique_together = [['group', 'user'], ['group', 'agent']]
        ordering = ['joined_at']
    
    def __str__(self):
        if self.member_type == self.MemberType.HUMAN:
            return f"{self.group.name} - {self.user.username} ({self.get_role_display()})"
        else:
            return f"{self.group.name} - {self.agent.name} ({self.get_role_display()})"
    
    def clean(self):
        """验证数据一致性"""
        from django.core.exceptions import ValidationError
        
        if self.member_type == self.MemberType.HUMAN and not self.user:
            raise ValidationError(_('人类成员必须关联一个用户账号'))
        elif self.member_type == self.MemberType.AGENT and not self.agent:
            raise ValidationError(_('代理成员必须关联一个代理'))
        
        if self.member_type == self.MemberType.HUMAN and self.agent:
            raise ValidationError(_('人类成员不应关联代理'))
        elif self.member_type == self.MemberType.AGENT and self.user:
            raise ValidationError(_('代理成员不应关联用户账号'))


class GroupMessage(models.Model):
    """
    群组消息模型，记录群组内的所有消息
    
    字段说明:
    - group: 所属群组
    - sender_user: 发送消息的用户（如果是人类）
    - sender_agent: 发送消息的代理（如果是AI代理）
    - sender_type: 发送者类型（人类或AI代理）
    - content: 消息内容
    - message_type: 消息类型
    - timestamp: 发送时间
    - mentioned_users: 提及到的用户
    - mentioned_agents: 提及到的代理
    - parent_message: 回复的消息
    - metadata: 元数据，如附件信息等
    """
    
    class SenderType(models.TextChoices):
        HUMAN = 'human', _('人类')
        AGENT = 'agent', _('AI代理')
        SYSTEM = 'system', _('系统')
    
    class MessageType(models.TextChoices):
        TEXT = 'text', _('文本')
        IMAGE = 'image', _('图片')
        FILE = 'file', _('文件')
        TASK = 'task', _('任务')
        SYSTEM = 'system', _('系统消息')
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('群组')
    )
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sent_group_messages',
        verbose_name=_('发送用户'),
        null=True,
        blank=True
    )
    sender_agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.SET_NULL,
        related_name='sent_group_messages',
        verbose_name=_('发送代理'),
        null=True,
        blank=True
    )
    sender_type = models.CharField(
        _('发送者类型'),
        max_length=10,
        choices=SenderType.choices,
        default=SenderType.HUMAN
    )
    content = models.JSONField(_('消息内容'))
    message_type = models.CharField(
        _('消息类型'),
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    timestamp = models.DateTimeField(_('发送时间'), auto_now_add=True)
    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='mentioned_in_messages',
        verbose_name=_('提及用户'),
        blank=True
    )
    mentioned_agents = models.ManyToManyField(
        'agents.Agent',
        related_name='mentioned_in_messages',
        verbose_name=_('提及代理'),
        blank=True
    )
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='replies',
        verbose_name=_('回复消息'),
        null=True,
        blank=True
    )
    metadata = models.JSONField(_('元数据'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('群组消息')
        verbose_name_plural = _('群组消息')
        ordering = ['timestamp']
    
    def __str__(self):
        if self.sender_type == self.SenderType.HUMAN and self.sender_user:
            sender = self.sender_user.username
        elif self.sender_type == self.SenderType.AGENT and self.sender_agent:
            sender = self.sender_agent.name
        else:
            sender = '系统'
        
        content_text = str(self.content)
        if len(content_text) > 30:
            content_text = content_text[:27] + '...'
            
        return f"{self.group.name} - {sender}: {content_text}"
    
    def clean(self):
        """验证数据一致性"""
        from django.core.exceptions import ValidationError
        
        if self.sender_type == self.SenderType.HUMAN and not self.sender_user:
            raise ValidationError(_('人类发送者必须关联一个用户账号'))
        elif self.sender_type == self.SenderType.AGENT and not self.sender_agent:
            raise ValidationError(_('代理发送者必须关联一个代理'))
            
        if self.sender_type == self.SenderType.SYSTEM:
            if self.sender_user or self.sender_agent:
                raise ValidationError(_('系统消息不应关联用户或代理'))


class GroupRule(models.Model):
    """
    群组规则模型，定义代理在群组中的行为规则
    
    字段说明:
    - group: 所属群组
    - name: 规则名称
    - description: 规则描述
    - rule_type: 规则类型（触发条件、回应规则等）
    - target_agents: 规则适用的代理
    - condition: 触发条件
    - action: 执行动作
    - priority: 优先级
    - is_active: 是否激活
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    
    class RuleType(models.TextChoices):
        TRIGGER = 'trigger', _('触发条件')
        RESPONSE = 'response', _('回应规则')
        SCHEDULE = 'schedule', _('定时任务')
        SYSTEM = 'system', _('系统规则')
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name=_('群组')
    )
    name = models.CharField(_('规则名称'), max_length=100)
    description = models.TextField(_('规则描述'), blank=True, null=True)
    rule_type = models.CharField(
        _('规则类型'),
        max_length=20,
        choices=RuleType.choices,
        default=RuleType.TRIGGER
    )
    target_agents = models.ManyToManyField(
        'agents.Agent',
        related_name='group_rules',
        verbose_name=_('目标代理'),
        blank=True
    )
    condition = models.JSONField(_('触发条件'))
    action = models.JSONField(_('执行动作'))
    priority = models.IntegerField(_('优先级'), default=0)
    is_active = models.BooleanField(_('是否激活'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('群组规则')
        verbose_name_plural = _('群组规则')
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"{self.group.name} - {self.name}"
