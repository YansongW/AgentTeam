from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

from agents.models import Agent
from groups.models import Group

User = get_user_model()

class TaskPriority(models.TextChoices):
    """任务优先级枚举"""
    LOW = 'low', _('低')
    MEDIUM = 'medium', _('中')
    HIGH = 'high', _('高')
    URGENT = 'urgent', _('紧急')

class TaskStatus(models.TextChoices):
    """任务状态枚举"""
    PENDING = 'pending', _('待处理')
    IN_PROGRESS = 'in_progress', _('进行中')
    REVIEW = 'review', _('审核中')
    COMPLETED = 'completed', _('已完成')
    BLOCKED = 'blocked', _('已阻塞')
    CANCELED = 'canceled', _('已取消')

class TaskType(models.TextChoices):
    """任务类型枚举"""
    DEVELOPMENT = 'development', _('开发')
    DESIGN = 'design', _('设计')
    RESEARCH = 'research', _('研究')
    WRITING = 'writing', _('写作')
    ANALYSIS = 'analysis', _('分析')
    PLANNING = 'planning', _('规划')
    TESTING = 'testing', _('测试')
    OTHER = 'other', _('其他')

class Task(models.Model):
    """
    任务模型
    
    表示一个可分配给用户或代理的任务
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('标题'), max_length=200)
    description = models.TextField(_('描述'), blank=True)
    status = models.CharField(
        _('状态'),
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING
    )
    priority = models.CharField(
        _('优先级'),
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM
    )
    task_type = models.CharField(
        _('任务类型'),
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.OTHER
    )
    
    # 日期相关
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    due_date = models.DateTimeField(_('截止日期'), null=True, blank=True)
    started_at = models.DateTimeField(_('开始时间'), null=True, blank=True)
    completed_at = models.DateTimeField(_('完成时间'), null=True, blank=True)
    
    # 关联
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        verbose_name=_('创建者')
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('关联群组'),
        null=True,
        blank=True
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='subtasks',
        verbose_name=_('父任务'),
        null=True,
        blank=True
    )
    
    # 进度和统计
    progress = models.IntegerField(_('进度百分比'), default=0)
    estimated_hours = models.FloatField(_('预计耗时(小时)'), null=True, blank=True)
    actual_hours = models.FloatField(_('实际耗时(小时)'), null=True, blank=True)
    
    # 其他属性
    is_recurring = models.BooleanField(_('是否重复任务'), default=False)
    recurrence_pattern = models.JSONField(_('重复模式'), null=True, blank=True)
    metadata = models.JSONField(_('元数据'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('任务')
        verbose_name_plural = _('任务')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """重写保存方法，自动更新相关字段"""
        # 如果进度为100%，自动设置状态为已完成
        if self.progress == 100 and self.status != TaskStatus.COMPLETED:
            self.status = TaskStatus.COMPLETED
        
        # 状态变更时更新相应时间字段
        if self.pk:
            try:
                old_instance = Task.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    if self.status == TaskStatus.IN_PROGRESS and not self.started_at:
                        self.started_at = timezone.now()
                    elif self.status == TaskStatus.COMPLETED and not self.completed_at:
                        self.completed_at = timezone.now()
            except Task.DoesNotExist:
                # 如果是新对象，设置初始时间
                if self.status == TaskStatus.IN_PROGRESS and not self.started_at:
                    self.started_at = timezone.now()
                elif self.status == TaskStatus.COMPLETED and not self.completed_at:
                    self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)

class TaskAssignment(models.Model):
    """
    任务分配模型
    
    表示任务分配给用户或代理
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('任务')
    )
    assigned_at = models.DateTimeField(_('分配时间'), auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_tasks',
        verbose_name=_('分配者')
    )
    
    # 可以分配给用户或代理（二选一）
    assigned_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_assignments',
        verbose_name=_('分配用户'),
        null=True,
        blank=True
    )
    assigned_agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='agent_assignments',
        verbose_name=_('分配代理'),
        null=True,
        blank=True
    )
    
    # 分配相关属性
    is_primary = models.BooleanField(_('是否主要负责人'), default=False)
    role = models.CharField(_('角色'), max_length=100, blank=True)
    notes = models.TextField(_('备注'), blank=True)
    
    class Meta:
        verbose_name = _('任务分配')
        verbose_name_plural = _('任务分配')
        unique_together = [
            ['task', 'assigned_user'],
            ['task', 'assigned_agent']
        ]
    
    def clean(self):
        """验证分配合法性"""
        from django.core.exceptions import ValidationError
        
        # 确保用户和代理不能同时为空或同时有值
        if (self.assigned_user is None and self.assigned_agent is None) or \
           (self.assigned_user is not None and self.assigned_agent is not None):
            raise ValidationError(_('必须指定用户或代理其中之一'))
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        assignee = self.assigned_user.username if self.assigned_user else self.assigned_agent.name
        return f"{self.task.title} - {assignee}"

class TaskComment(models.Model):
    """
    任务评论模型
    
    表示对任务的评论或更新
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('任务')
    )
    content = models.TextField(_('内容'))
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    
    # 可以由用户或代理创建（二选一）
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_comments',
        verbose_name=_('创建用户'),
        null=True,
        blank=True
    )
    created_by_agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='task_comments',
        verbose_name=_('创建代理'),
        null=True,
        blank=True
    )
    
    # 评论类型
    is_system_comment = models.BooleanField(_('是否系统评论'), default=False)
    is_status_update = models.BooleanField(_('是否状态更新'), default=False)
    metadata = models.JSONField(_('元数据'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('任务评论')
        verbose_name_plural = _('任务评论')
        ordering = ['created_at']
    
    def clean(self):
        """验证合法性"""
        from django.core.exceptions import ValidationError
        
        # 如果不是系统评论，确保用户和代理不能同时为空或同时有值
        if not self.is_system_comment:
            if (self.created_by_user is None and self.created_by_agent is None) or \
               (self.created_by_user is not None and self.created_by_agent is not None):
                raise ValidationError(_('必须指定用户或代理其中之一作为评论创建者'))
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"评论: {self.task.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class TaskTag(models.Model):
    """
    任务标签模型
    """
    name = models.CharField(_('名称'), max_length=50, unique=True)
    color = models.CharField(_('颜色'), max_length=20, default='blue')
    description = models.CharField(_('描述'), max_length=200, blank=True)
    
    class Meta:
        verbose_name = _('任务标签')
        verbose_name_plural = _('任务标签')
    
    def __str__(self):
        return self.name

class TaskTagAssignment(models.Model):
    """
    任务标签分配
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='tag_assignments',
        verbose_name=_('任务')
    )
    tag = models.ForeignKey(
        TaskTag,
        on_delete=models.CASCADE,
        related_name='task_assignments',
        verbose_name=_('标签')
    )
    assigned_at = models.DateTimeField(_('分配时间'), auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tag_assignments',
        verbose_name=_('分配者'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('任务标签分配')
        verbose_name_plural = _('任务标签分配')
        unique_together = ['task', 'tag']
    
    def __str__(self):
        return f"{self.task.title} - {self.tag.name}"

class TaskDependency(models.Model):
    """
    任务依赖关系
    
    表示一个任务依赖于另一个任务的完成
    """
    dependent_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='dependencies',
        verbose_name=_('依赖任务')
    )
    prerequisite_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='dependents',
        verbose_name=_('前置任务')
    )
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_dependencies',
        verbose_name=_('创建者')
    )
    notes = models.TextField(_('备注'), blank=True)
    
    class Meta:
        verbose_name = _('任务依赖')
        verbose_name_plural = _('任务依赖')
        unique_together = ['dependent_task', 'prerequisite_task']
    
    def __str__(self):
        return f"{self.dependent_task.title} 依赖于 {self.prerequisite_task.title}"
