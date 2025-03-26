from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Task, TaskAssignment, TaskDependency, TaskComment

@receiver(post_save, sender=Task)
def handle_task_status_change(sender, instance, created, **kwargs):
    """处理任务状态变更"""
    if not created:
        # 获取原始任务状态
        original_task = Task.objects.get(pk=instance.pk)
        if original_task.status != instance.status:
            # 创建状态变更系统评论
            TaskComment.objects.create(
                task=instance,
                content=f'任务状态从 {original_task.get_status_display()} 变更为 {instance.get_status_display()}',
                is_system_comment=True
            )
            
            # 更新相关时间戳
            if instance.status == 'in_progress':
                instance.started_at = timezone.now()
            elif instance.status == 'completed':
                instance.completed_at = timezone.now()
            instance.save()

@receiver(post_save, sender=TaskAssignment)
def handle_task_assignment(sender, instance, created, **kwargs):
    """处理任务分配"""
    if created:
        # 创建分配系统评论
        assignee = instance.assigned_user or instance.assigned_agent
        assignee_name = assignee.username if instance.assigned_user else assignee.name
        
        TaskComment.objects.create(
            task=instance.task,
            content=f'任务分配给 {assignee_name}',
            is_system_comment=True
        )

@receiver(post_delete, sender=TaskAssignment)
def handle_task_unassignment(sender, instance, **kwargs):
    """处理任务取消分配"""
    # 创建取消分配系统评论
    assignee = instance.assigned_user or instance.assigned_agent
    assignee_name = assignee.username if instance.assigned_user else assignee.name
    
    TaskComment.objects.create(
        task=instance.task,
        content=f'取消分配给 {assignee_name}',
        is_system_comment=True
    )

@receiver(post_save, sender=TaskDependency)
def handle_task_dependency(sender, instance, created, **kwargs):
    """处理任务依赖关系"""
    if created:
        # 创建依赖关系系统评论
        TaskComment.objects.create(
            task=instance.task,
            content=f'添加了对任务 "{instance.dependent_task.title}" 的依赖',
            is_system_comment=True
        )

@receiver(post_delete, sender=TaskDependency)
def handle_task_dependency_removal(sender, instance, **kwargs):
    """处理任务依赖关系移除"""
    # 创建依赖关系移除系统评论
    TaskComment.objects.create(
        task=instance.task,
        content=f'移除了对任务 "{instance.dependent_task.title}" 的依赖',
        is_system_comment=True
    ) 