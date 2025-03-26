from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
import re
import logging

logger = logging.getLogger(__name__)

class Agent(models.Model):
    """
    AI代理模型，定义代理的角色、技能和权限
    
    字段说明:
    - name: 代理名称，如"前端开发员A"
    - role: 代理角色，如"前端开发"、"产品经理"等
    - description: 代理的详细描述，包括功能和用途
    - owner: 代理的创建者/所有者
    - created_at: 代理创建时间
    - updated_at: 代理更新时间
    - status: 代理当前状态（在线、离线等）
    - is_public: 是否公开，公开代理可被其他用户查看使用
    - skills: 代理的技能，JSON格式存储特殊技能和配置
    - system_prompt: 系统提示词，定义代理的个性和行为方式
    - model_config: 使用的AI模型配置信息
    - api_access: 代理可访问的API权限
    """
    
    class Status(models.TextChoices):
        ONLINE = 'online', _('在线')
        OFFLINE = 'offline', _('离线')
        BUSY = 'busy', _('忙碌')
        DISABLED = 'disabled', _('已禁用')
    
    class Role(models.TextChoices):
        PRODUCT_MANAGER = 'product_manager', _('产品经理')
        FRONTEND_DEV = 'frontend_dev', _('前端开发')
        BACKEND_DEV = 'backend_dev', _('后端开发')
        UX_DESIGNER = 'ux_designer', _('用户体验设计师')
        QA_TESTER = 'qa_tester', _('测试工程师')
        DATA_ANALYST = 'data_analyst', _('数据分析师')
        VIRTUAL_FRIEND = 'virtual_friend', _('虚拟朋友')
        ASSISTANT = 'assistant', _('助手')
        CUSTOM = 'custom', _('自定义')
    
    name = models.CharField(_('代理名称'), max_length=100)
    role = models.CharField(
        _('代理角色'),
        max_length=50,
        choices=Role.choices,
        default=Role.ASSISTANT
    )
    description = models.TextField(_('代理描述'), blank=True, null=True)
    
    # 关系字段
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_agents',
        verbose_name=_('所有者')
    )
    
    # 状态字段
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    status = models.CharField(
        _('状态'),
        max_length=20,
        choices=Status.choices,
        default=Status.OFFLINE
    )
    is_public = models.BooleanField(_('是否公开'), default=False)
    
    # 配置字段
    skills = models.JSONField(_('技能配置'), default=dict, blank=True)
    system_prompt = models.TextField(_('系统提示'), blank=True, null=True)
    model_config = models.JSONField(_('模型配置'), default=dict, blank=True)
    api_access = models.JSONField(_('API权限'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('AI代理')
        verbose_name_plural = _('AI代理')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"
    
    def is_available(self):
        """检查代理是否可用"""
        return self.status in [self.Status.ONLINE, self.Status.BUSY]
    
    def set_status(self, status):
        """设置代理状态"""
        if status in self.Status.values:
            self.status = status
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False

    def get_recent_interactions(self, user=None, hours=24, limit=10):
        """
        获取当前代理最近的交互记录
        
        参数:
        - user: 用户对象，如果提供则只获取与该用户相关的交互
        - hours: 最近多少小时内的交互，默认24小时
        - limit: 最多返回多少条记录，默认10条
        
        返回:
        - 交互记录QuerySet
        """
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        query = Q(
            Q(initiator=self) | Q(receiver=self),
            timestamp__gte=time_threshold
        )
        
        # 如果指定了用户，则只获取该用户相关的交互
        if user:
            user_agents = Agent.objects.filter(owner=user)
            query &= Q(initiator__in=user_agents) | Q(receiver__in=user_agents)
            
        interactions = AgentInteraction.objects.filter(query).order_by('-timestamp')[:limit]
        return interactions

    def get_conversation_history(self, user=None, hours=24, limit=10):
        """
        获取格式化的对话历史，适合传递给AI模型
        
        参数:
        - user: 用户对象，如果提供则只获取与该用户相关的对话
        - hours: 最近多少小时内的对话，默认24小时
        - limit: 最多返回多少条记录，默认10条
        
        返回:
        - 格式化的对话历史列表，可直接用于上下文
        """
        interactions = self.get_recent_interactions(user, hours, limit)
        conversation_history = []
        
        for interaction in interactions:
            if interaction.interaction_type == AgentInteraction.InteractionType.MESSAGE:
                content = interaction.content
                if 'user_message' in content and 'agent_response' in content:
                    conversation_history.append({
                        'user': content['user_message'],
                        'assistant': content['agent_response']
                    })
        
        return conversation_history


class AgentSkill(models.Model):
    """
    代理技能模型，定义代理可以拥有的特定技能
    
    字段说明:
    - name: 技能名称
    - description: 技能描述
    - configuration: 技能配置，JSON格式
    """
    name = models.CharField(_('技能名称'), max_length=100)
    description = models.TextField(_('技能描述'), blank=True, null=True)
    configuration = models.JSONField(_('配置'), default=dict, blank=True)
    
    # 关系字段
    agents = models.ManyToManyField(
        Agent,
        through='AgentSkillAssignment',
        related_name='skill_set',
        verbose_name=_('拥有此技能的代理')
    )
    
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('代理技能')
        verbose_name_plural = _('代理技能')
    
    def __str__(self):
        return self.name


class AgentSkillAssignment(models.Model):
    """
    代理技能分配关系表，记录代理拥有的技能及其特定配置
    """
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='skill_assignments',
        verbose_name=_('代理')
    )
    skill = models.ForeignKey(
        AgentSkill,
        on_delete=models.CASCADE,
        related_name='agent_assignments',
        verbose_name=_('技能')
    )
    
    # 代理特定的技能配置覆盖
    custom_configuration = models.JSONField(_('自定义配置'), default=dict, blank=True)
    enabled = models.BooleanField(_('启用状态'), default=True)
    
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('代理技能分配')
        verbose_name_plural = _('代理技能分配')
        unique_together = ('agent', 'skill')
    
    def __str__(self):
        return f"{self.agent.name} - {self.skill.name}"


class AgentInteraction(models.Model):
    """
    代理交互记录，记录代理之间的通信和任务执行情况
    
    字段说明:
    - initiator: 发起交互的代理
    - receiver: 接收交互的代理
    - content: 交互内容
    - interaction_type: 交互类型（消息、命令、响应等）
    """
    
    class InteractionType(models.TextChoices):
        MESSAGE = 'message', _('消息')
        COMMAND = 'command', _('命令')
        RESPONSE = 'response', _('响应')
        TASK_ASSIGNMENT = 'task_assignment', _('任务分配')
        STATUS_UPDATE = 'status_update', _('状态更新')
    
    initiator = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='initiated_interactions',
        verbose_name=_('发起者')
    )
    receiver = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='received_interactions',
        verbose_name=_('接收者')
    )
    content = models.JSONField(_('交互内容'))
    interaction_type = models.CharField(
        _('交互类型'),
        max_length=20,
        choices=InteractionType.choices,
        default=InteractionType.MESSAGE
    )
    
    timestamp = models.DateTimeField(_('时间戳'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('代理交互')
        verbose_name_plural = _('代理交互')
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.interaction_type}: {self.initiator.name} → {self.receiver.name}"

    @classmethod
    def get_user_agent_conversations(cls, user, agent_id=None, hours=24, limit=20):
        """
        获取用户与特定代理或所有代理的对话历史
        
        参数:
        - user: 用户对象
        - agent_id: 代理ID，如果不提供则获取与所有代理的对话
        - hours: 最近多少小时内的对话，默认24小时
        - limit: 最多返回多少条记录，默认20条
        
        返回:
        - 按代理分组的对话历史字典
        """
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        # 获取用户拥有的代理
        user_agents = Agent.objects.filter(owner=user)
        
        # 构建查询条件
        query = Q(
            Q(initiator__in=user_agents) | Q(receiver__in=user_agents),
            timestamp__gte=time_threshold,
            interaction_type=cls.InteractionType.MESSAGE
        )
        
        # 如果指定了代理ID，则只获取与该代理的对话
        if agent_id:
            agent = Agent.objects.get(id=agent_id)
            query &= Q(initiator=agent) | Q(receiver=agent)
            
        # 获取交互记录
        interactions = cls.objects.filter(query).order_by('-timestamp')[:limit]
        
        # 按代理分组
        conversations = {}
        for interaction in interactions:
            # 确定是哪个代理
            if interaction.initiator in user_agents:
                agent = interaction.receiver
            else:
                agent = interaction.initiator
                
            # 初始化该代理的对话列表
            if agent.id not in conversations:
                conversations[agent.id] = {
                    'agent_name': agent.name,
                    'agent_role': agent.get_role_display(),
                    'messages': []
                }
                
            # 添加消息
            content = interaction.content
            if 'user_message' in content and 'agent_response' in content:
                conversations[agent.id]['messages'].append({
                    'user': content['user_message'],
                    'assistant': content['agent_response'],
                    'timestamp': interaction.timestamp
                })
                
        return conversations


class AgentListeningRule(models.Model):
    """
    代理监听规则模型，定义代理监听消息的规则
    
    字段说明:
    - name: 规则名称
    - description: 规则描述
    - agent: 拥有此规则的代理
    - is_active: 规则是否激活
    - priority: 规则优先级，数字越小优先级越高
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    
    class TriggerType(models.TextChoices):
        KEYWORD = 'keyword', _('关键词匹配')
        REGEX = 'regex', _('正则表达式')
        MENTION = 'mention', _('提及代理')
        ALL_MESSAGES = 'all_messages', _('所有消息')
        SENTIMENT = 'sentiment', _('情绪分析')
        CONTEXT_AWARE = 'context_aware', _('上下文感知')
        CUSTOM = 'custom', _('自定义条件')
    
    class ResponseType(models.TextChoices):
        AUTO_REPLY = 'auto_reply', _('自动回复')
        NOTIFICATION = 'notification', _('通知')
        TASK = 'task', _('创建任务')
        ACTION = 'action', _('执行动作')
        CUSTOM = 'custom', _('自定义响应')
    
    name = models.CharField(_('规则名称'), max_length=100)
    description = models.TextField(_('规则描述'), blank=True, null=True)
    
    # 关系字段
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='listening_rules',
        verbose_name=_('代理')
    )
    
    # 规则配置
    is_active = models.BooleanField(_('是否激活'), default=True)
    priority = models.IntegerField(_('优先级'), default=10)
    
    # 触发条件
    trigger_type = models.CharField(
        _('触发类型'),
        max_length=20,
        choices=TriggerType.choices,
        default=TriggerType.KEYWORD
    )
    trigger_condition = models.JSONField(
        _('触发条件'), 
        help_text=_('根据触发类型定义的具体条件，例如关键词列表或正则表达式')
    )
    
    # 监听范围
    listen_in_groups = models.BooleanField(_('在群组中监听'), default=True)
    listen_in_direct = models.BooleanField(_('在直接消息中监听'), default=True)
    allowed_groups = models.JSONField(
        _('允许的群组'), 
        default=list,
        blank=True,
        help_text=_('可以监听的群组ID列表，空表示所有群组')
    )
    
    # 响应行为
    response_type = models.CharField(
        _('响应类型'),
        max_length=20,
        choices=ResponseType.choices,
        default=ResponseType.AUTO_REPLY
    )
    response_content = models.JSONField(
        _('响应内容'),
        help_text=_('根据响应类型定义的具体行为')
    )
    
    # 冷却时间（秒）
    cooldown_period = models.IntegerField(
        _('冷却时间'), 
        default=0,
        help_text=_('规则触发后的冷却时间（秒），0表示无冷却')
    )
    last_triggered = models.DateTimeField(_('最近触发时间'), null=True, blank=True)
    
    # 统计信息
    trigger_count = models.IntegerField(_('触发次数'), default=0)
    
    # 时间字段
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('代理监听规则')
        verbose_name_plural = _('代理监听规则')
        ordering = ['priority', '-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.agent.name})"
    
    def is_on_cooldown(self):
        """检查规则是否处于冷却期"""
        if not self.cooldown_period or not self.last_triggered:
            return False
        
        cooldown_ends_at = self.last_triggered + timedelta(seconds=self.cooldown_period)
        return timezone.now() < cooldown_ends_at
    
    def can_trigger(self):
        """检查规则是否可以触发"""
        return self.is_active and not self.is_on_cooldown()
    
    def match_message(self, message):
        """
        检查消息是否匹配规则条件
        
        参数:
        - message: 消息对象，包含消息内容、发送者、接收者等信息
        
        返回:
        - 布尔值，表示是否匹配
        """
        if not self.can_trigger():
            return False
            
        # 根据不同的触发类型进行匹配
        if self.trigger_type == self.TriggerType.KEYWORD:
            return self._match_keyword(message)
        elif self.trigger_type == self.TriggerType.REGEX:
            return self._match_regex(message)
        elif self.trigger_type == self.TriggerType.MENTION:
            return self._match_mention(message)
        elif self.trigger_type == self.TriggerType.ALL_MESSAGES:
            return True
        elif self.trigger_type == self.TriggerType.SENTIMENT:
            return self._match_sentiment(message)
        elif self.trigger_type == self.TriggerType.CONTEXT_AWARE:
            return self._match_context_aware(message)
        elif self.trigger_type == self.TriggerType.CUSTOM:
            return self._match_custom(message)
        
        return False
    
    def _match_keyword(self, message):
        """关键词匹配"""
        if 'keywords' not in self.trigger_condition:
            return False
            
        message_content = message.get('content', '').lower()
        keywords = [k.lower() for k in self.trigger_condition['keywords']]
        
        for keyword in keywords:
            if keyword in message_content:
                return True
        return False
    
    def _match_regex(self, message):
        """正则表达式匹配"""
        if 'pattern' not in self.trigger_condition:
            return False
            
        message_content = message.get('content', '')
        pattern = self.trigger_condition['pattern']
        
        try:
            return bool(re.search(pattern, message_content))
        except:
            return False
    
    def _match_mention(self, message):
        """提及代理匹配"""
        message_content = message.get('content', '').lower()
        agent_name = self.agent.name.lower()
        
        # 检查是否明确提到了代理名称
        if f"@{agent_name}" in message_content:
            return True
            
        # 检查mentions字段（如果消息格式包含此字段）
        mentions = message.get('mentions', [])
        if str(self.agent.id) in mentions or self.agent.name in mentions:
            return True
            
        return False
    
    def _match_sentiment(self, message):
        """情绪分析匹配"""
        if 'target_sentiment' not in self.trigger_condition:
            return False
            
        message_content = message.get('content', '')
        
        # 使用简单的情绪词典进行匹配
        target_sentiment = self.trigger_condition['target_sentiment']
        sentiment_threshold = self.trigger_condition.get('threshold', 0.5)
        
        # 计算情绪得分（实际环境中应使用NLP服务）
        from agents.utils.sentiment_analyzer import analyze_sentiment
        sentiment_score = analyze_sentiment(message_content)
        
        if target_sentiment == 'positive':
            return sentiment_score >= sentiment_threshold
        elif target_sentiment == 'negative':
            return sentiment_score <= -sentiment_threshold
        elif target_sentiment == 'neutral':
            return abs(sentiment_score) < sentiment_threshold
        
        return False
        
    def _match_context_aware(self, message):
        """上下文感知匹配"""
        if 'context_rules' not in self.trigger_condition:
            return False
            
        context_rules = self.trigger_condition['context_rules']
        message_content = message.get('content', '').lower()
        context_messages = message.get('context_messages', [])
        
        # 获取配置参数
        context_size = self.trigger_condition.get('context_size', 5)  # 默认考虑最近5条消息
        time_window = self.trigger_condition.get('time_window', 300)  # 默认5分钟时间窗口
        match_threshold = self.trigger_condition.get('match_threshold', 0.7)  # 默认匹配阈值
        
        # 确保上下文消息在时间窗口内
        current_time = timezone.now()
        valid_context = []
        
        for ctx_msg in context_messages[-context_size:]:
            msg_time = timezone.datetime.fromisoformat(ctx_msg.get('timestamp', ''))
            if (current_time - msg_time).total_seconds() <= time_window:
                valid_context.append(ctx_msg)
        
        # 如果没有有效的上下文消息，返回False
        if not valid_context:
            return False
        
        # 合并所有上下文消息内容
        context_content = ' '.join([
            msg.get('content', '').lower()
            for msg in valid_context
        ])
        
        # 评估每个上下文规则
        matched_rules = 0
        total_rules = len(context_rules)
        
        for rule in context_rules:
            rule_type = rule.get('type', 'keyword')
            rule_value = rule.get('value', '')
            rule_weight = rule.get('weight', 1.0)
            
            if rule_type == 'keyword':
                # 关键词匹配
                if rule_value.lower() in context_content:
                    matched_rules += rule_weight
            elif rule_type == 'regex':
                # 正则表达式匹配
                try:
                    if re.search(rule_value, context_content):
                        matched_rules += rule_weight
                except re.error:
                    logger.error(f"无效的正则表达式: {rule_value}")
            elif rule_type == 'sentiment':
                # 情感倾向匹配（需要情感分析服务）
                from .utils.sentiment_analyzer import analyze_sentiment
                sentiment_score = analyze_sentiment(context_content)
                if rule_value == 'positive' and sentiment_score > 0.3:
                    matched_rules += rule_weight
                elif rule_value == 'negative' and sentiment_score < -0.3:
                    matched_rules += rule_weight
                elif rule_value == 'neutral' and abs(sentiment_score) <= 0.3:
                    matched_rules += rule_weight
            elif rule_type == 'topic':
                # 主题相关性匹配（需要主题分析服务）
                from .utils.topic_analyzer import analyze_topic_similarity
                topic_similarity = analyze_topic_similarity(context_content, rule_value)
                if topic_similarity >= 0.5:  # 可配置的阈值
                    matched_rules += rule_weight
        
        # 计算最终匹配分数
        match_score = matched_rules / total_rules if total_rules > 0 else 0
        
        # 记录匹配结果
        logger.debug(f"上下文匹配分数: {match_score:.2f}, 阈值: {match_threshold}")
        
        return match_score >= match_threshold
    
    def _match_custom(self, message):
        """自定义条件匹配"""
        # 在实际应用中，可以实现自定义的匹配逻辑
        # 例如调用外部服务或使用更复杂的规则
        return False
    
    def execute_response(self, message):
        """
        执行规则定义的响应行为
        
        参数:
        - message: 消息对象，包含消息内容、发送者、接收者等信息
        
        返回:
        - 响应结果
        """
        # 更新统计信息
        self.trigger_count += 1
        self.last_triggered = timezone.now()
        self.save(update_fields=['trigger_count', 'last_triggered', 'updated_at'])
        
        # 根据不同的响应类型执行不同的行为
        if self.response_type == self.ResponseType.AUTO_REPLY:
            return self._execute_auto_reply(message)
        elif self.response_type == self.ResponseType.NOTIFICATION:
            return self._execute_notification(message)
        elif self.response_type == self.ResponseType.TASK:
            return self._execute_task(message)
        elif self.response_type == self.ResponseType.ACTION:
            return self._execute_action(message)
        elif self.response_type == self.ResponseType.CUSTOM:
            return self._execute_custom(message)
        
        return None
    
    def _execute_auto_reply(self, message):
        """自动回复"""
        if 'reply_template' not in self.response_content:
            return None
            
        template = self.response_content['reply_template']
        
        # 简单的模板替换
        reply = template.replace('{agent_name}', self.agent.name)
        
        if '{user}' in template and 'sender' in message:
            reply = reply.replace('{user}', message.get('sender', '用户'))
            
        return {
            'type': 'auto_reply',
            'content': reply,
            'agent_id': str(self.agent.id),  # 确保ID是字符串
            'agent_name': self.agent.name,
            'rule_id': str(self.id),  # 添加规则ID
            'rule_name': self.name,   # 添加规则名称
            'confidence': 1.0,        # 添加置信度
            'message_id': message.get('id'),
            'timestamp': timezone.now().isoformat()
        }
    
    def _execute_notification(self, message):
        """发送通知"""
        return {
            'type': 'notification',
            'content': self.response_content.get('notification_text', '收到新消息'),
            'agent_id': str(self.agent.id),  # 确保ID是字符串
            'agent_name': self.agent.name,
            'rule_id': str(self.id),  # 添加规则ID
            'rule_name': self.name,   # 添加规则名称
            'confidence': 1.0,        # 添加置信度
            'message_id': message.get('id'),
            'timestamp': timezone.now().isoformat()
        }
    
    def _execute_task(self, message):
        """创建任务"""
        # 实际应用中，这里可以创建一个任务记录
        return {
            'type': 'task',
            'task_title': self.response_content.get('task_title', '新任务'),
            'task_description': self.response_content.get('task_description', ''),
            'agent_id': str(self.agent.id),  # 确保ID是字符串
            'agent_name': self.agent.name,
            'rule_id': str(self.id),  # 添加规则ID
            'rule_name': self.name,   # 添加规则名称
            'confidence': 1.0,        # 添加置信度
            'message_id': message.get('id'),
            'timestamp': timezone.now().isoformat()
        }
    
    def _execute_action(self, message):
        """执行动作"""
        # 在实际应用中，可以执行特定的动作
        return {
            'type': 'action',
            'action_name': self.response_content.get('action_name', ''),
            'action_params': self.response_content.get('action_params', {}),
            'agent_id': str(self.agent.id),  # 确保ID是字符串
            'agent_name': self.agent.name,
            'rule_id': str(self.id),  # 添加规则ID
            'rule_name': self.name,   # 添加规则名称
            'confidence': 1.0,        # 添加置信度
            'message_id': message.get('id'),
            'timestamp': timezone.now().isoformat()
        }
    
    def _execute_custom(self, message):
        """自定义响应"""
        # 在实际应用中，可以实现自定义的响应逻辑
        return {
            'type': 'custom',
            'content': self.response_content.get('custom_response', ''),
            'agent_id': str(self.agent.id),  # 确保ID是字符串
            'agent_name': self.agent.name,
            'rule_id': str(self.id),  # 添加规则ID
            'rule_name': self.name,   # 添加规则名称
            'confidence': 1.0,        # 添加置信度
            'message_id': message.get('id'),
            'timestamp': timezone.now().isoformat()
        }
