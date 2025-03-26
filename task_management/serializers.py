from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from agents.models import Agent
from agents.serializers import AgentMinimalSerializer
from groups.models import Group
from groups.serializers import GroupMinimalSerializer
from users.serializers import UserMinimalSerializer

from .models import (
    Task, TaskAssignment, TaskComment, 
    TaskTag, TaskTagAssignment, TaskDependency,
    TaskStatus, TaskPriority, TaskType
)

User = get_user_model()

class TaskTagSerializer(serializers.ModelSerializer):
    """任务标签序列化器"""
    
    class Meta:
        model = TaskTag
        fields = ['id', 'name', 'color', 'description']

class TaskTagMinimalSerializer(serializers.ModelSerializer):
    """精简的任务标签序列化器"""
    
    class Meta:
        model = TaskTag
        fields = ['id', 'name', 'color']

class TaskCommentSerializer(serializers.ModelSerializer):
    """任务评论序列化器"""
    created_by_user_detail = UserMinimalSerializer(source='created_by_user', read_only=True)
    created_by_agent_detail = AgentMinimalSerializer(source='created_by_agent', read_only=True)
    
    class Meta:
        model = TaskComment
        fields = [
            'id', 'task', 'content', 'created_at', 
            'created_by_user', 'created_by_agent',
            'created_by_user_detail', 'created_by_agent_detail',
            'is_system_comment', 'is_status_update', 'metadata'
        ]
        read_only_fields = ['created_at']
    
    def validate(self, data):
        """验证创建者不能同时为用户和代理"""
        created_by_user = data.get('created_by_user', None)
        created_by_agent = data.get('created_by_agent', None)
        is_system_comment = data.get('is_system_comment', False)
        
        if not is_system_comment:
            if (created_by_user is None and created_by_agent is None) or \
               (created_by_user is not None and created_by_agent is not None):
                raise serializers.ValidationError(_('必须指定用户或代理其中之一作为评论创建者'))
        
        return data

class TaskDependencySerializer(serializers.ModelSerializer):
    """任务依赖关系序列化器"""
    dependent_task_title = serializers.CharField(source='dependent_task.title', read_only=True)
    prerequisite_task_title = serializers.CharField(source='prerequisite_task.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TaskDependency
        fields = [
            'id', 'dependent_task', 'prerequisite_task',
            'dependent_task_title', 'prerequisite_task_title',
            'created_at', 'created_by', 'created_by_name', 'notes'
        ]
        read_only_fields = ['created_at']
    
    def validate(self, data):
        """验证依赖关系的合法性"""
        dependent_task = data.get('dependent_task')
        prerequisite_task = data.get('prerequisite_task')
        
        if dependent_task == prerequisite_task:
            raise serializers.ValidationError(_('任务不能依赖自身'))
        
        # 检查是否会形成循环依赖
        if dependent_task and prerequisite_task:
            # 检查是否已存在反向依赖
            if TaskDependency.objects.filter(
                dependent_task=prerequisite_task,
                prerequisite_task=dependent_task
            ).exists():
                raise serializers.ValidationError(_('不能创建循环依赖'))
            
            # 检查是否会形成间接循环依赖（复杂情况需要更完善的算法）
            # 这里只是简单检查直接依赖
        
        return data

class TaskAssignmentSerializer(serializers.ModelSerializer):
    """任务分配序列化器"""
    assigned_user_detail = UserMinimalSerializer(source='assigned_user', read_only=True)
    assigned_agent_detail = AgentMinimalSerializer(source='assigned_agent', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskAssignment
        fields = [
            'id', 'task', 'task_title', 'assigned_at', 
            'assigned_by', 'assigned_by_name',
            'assigned_user', 'assigned_agent',
            'assigned_user_detail', 'assigned_agent_detail',
            'is_primary', 'role', 'notes'
        ]
        read_only_fields = ['assigned_at']
    
    def validate(self, data):
        """验证分配合法性"""
        assigned_user = data.get('assigned_user', None)
        assigned_agent = data.get('assigned_agent', None)
        
        if (assigned_user is None and assigned_agent is None) or \
           (assigned_user is not None and assigned_agent is not None):
            raise serializers.ValidationError(_('必须指定用户或代理其中之一'))
        
        return data

class TaskTagAssignmentSerializer(serializers.ModelSerializer):
    """任务标签分配序列化器"""
    tag_detail = TaskTagMinimalSerializer(source='tag', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = TaskTagAssignment
        fields = [
            'id', 'task', 'task_title', 'tag', 'tag_detail',
            'assigned_at', 'assigned_by', 'assigned_by_name'
        ]
        read_only_fields = ['assigned_at']

class TaskMinimalSerializer(serializers.ModelSerializer):
    """精简的任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'status', 'status_display',
            'priority', 'priority_display', 'progress', 'due_date'
        ]

class TaskSerializer(serializers.ModelSerializer):
    """任务序列化器"""
    creator_detail = UserMinimalSerializer(source='creator', read_only=True)
    group_detail = GroupMinimalSerializer(source='group', read_only=True)
    parent_task_detail = TaskMinimalSerializer(source='parent_task', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    
    # 关联数据
    tags = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)
    subtasks_count = serializers.IntegerField(read_only=True)
    dependencies_count = serializers.IntegerField(read_only=True)
    dependents_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'priority', 'priority_display', 'task_type', 'task_type_display',
            'created_at', 'updated_at', 'due_date', 'started_at', 'completed_at',
            'creator', 'creator_detail', 'group', 'group_detail',
            'parent_task', 'parent_task_detail',
            'progress', 'estimated_hours', 'actual_hours',
            'is_recurring', 'recurrence_pattern', 'metadata',
            'tags', 'assignments',
            'comments_count', 'subtasks_count', 'dependencies_count', 'dependents_count'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'comments_count', 'subtasks_count', 'dependencies_count', 'dependents_count',
            'creator'
        ]
    
    def get_tags(self, obj):
        """获取任务标签"""
        tag_assignments = obj.tag_assignments.select_related('tag').all()
        return [
            {
                'id': ta.tag.id,
                'name': ta.tag.name,
                'color': ta.tag.color
            }
            for ta in tag_assignments
        ]
    
    def get_assignments(self, obj):
        """获取任务分配信息"""
        assignments = []
        for assignment in obj.assignments.all():
            if assignment.assigned_user:
                assignee = {
                    'type': 'user',
                    'id': assignment.assigned_user.id,
                    'name': assignment.assigned_user.username,
                    'is_primary': assignment.is_primary
                }
            else:
                assignee = {
                    'type': 'agent',
                    'id': assignment.assigned_agent.id,
                    'name': assignment.assigned_agent.name,
                    'is_primary': assignment.is_primary
                }
            assignments.append(assignee)
        return assignments
    
    def to_representation(self, instance):
        """添加统计信息"""
        ret = super().to_representation(instance)
        if not hasattr(instance, 'comments_count'):
            ret['comments_count'] = instance.comments.count()
        if not hasattr(instance, 'subtasks_count'):
            ret['subtasks_count'] = instance.subtasks.count()
        if not hasattr(instance, 'dependencies_count'):
            ret['dependencies_count'] = instance.dependencies.count()
        if not hasattr(instance, 'dependents_count'):
            ret['dependents_count'] = instance.dependents.count()
        return ret

class TaskDetailSerializer(TaskSerializer):
    """详细任务序列化器"""
    comments = TaskCommentSerializer(many=True, read_only=True)
    assignments_detail = TaskAssignmentSerializer(source='assignments', many=True, read_only=True)
    tags_detail = TaskTagAssignmentSerializer(source='tag_assignments', many=True, read_only=True)
    dependencies_detail = TaskDependencySerializer(source='dependencies', many=True, read_only=True)
    subtasks = TaskMinimalSerializer(many=True, read_only=True)
    
    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + [
            'comments', 'assignments_detail', 'tags_detail', 
            'dependencies_detail', 'subtasks'
        ]

class TaskStatusUpdateSerializer(serializers.Serializer):
    """任务状态更新序列化器"""
    status = serializers.ChoiceField(choices=TaskStatus.choices)
    comment = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get('status')
        comment_text = validated_data.get('comment', '')
        
        # 更新状态
        instance.status = new_status
        instance.save()
        
        # 创建系统评论记录状态变更
        if old_status != new_status:
            from_status = dict(TaskStatus.choices)[old_status]
            to_status = dict(TaskStatus.choices)[new_status]
            
            content = f"任务状态从\"{from_status}\"变更为\"{to_status}\""
            if comment_text:
                content += f"\n\n备注: {comment_text}"
            
            user = self.context.get('request').user
            TaskComment.objects.create(
                task=instance,
                content=content,
                created_by_user=user,
                is_status_update=True,
                metadata={
                    'from_status': old_status,
                    'to_status': new_status
                }
            )
        
        return instance

class TaskPriorityUpdateSerializer(serializers.Serializer):
    """任务优先级更新序列化器"""
    priority = serializers.ChoiceField(choices=TaskPriority.choices)
    comment = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        old_priority = instance.priority
        new_priority = validated_data.get('priority')
        comment_text = validated_data.get('comment', '')
        
        # 更新优先级
        instance.priority = new_priority
        instance.save()
        
        # 创建系统评论记录优先级变更
        if old_priority != new_priority:
            from_priority = dict(TaskPriority.choices)[old_priority]
            to_priority = dict(TaskPriority.choices)[new_priority]
            
            content = f"任务优先级从\"{from_priority}\"变更为\"{to_priority}\""
            if comment_text:
                content += f"\n\n备注: {comment_text}"
            
            user = self.context.get('request').user
            TaskComment.objects.create(
                task=instance,
                content=content,
                created_by_user=user,
                is_system_comment=True,
                metadata={
                    'from_priority': old_priority,
                    'to_priority': new_priority
                }
            )
        
        return instance

class TaskProgressUpdateSerializer(serializers.Serializer):
    """任务进度更新序列化器"""
    progress = serializers.IntegerField(min_value=0, max_value=100)
    comment = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        old_progress = instance.progress
        new_progress = validated_data.get('progress')
        comment_text = validated_data.get('comment', '')
        
        # 更新进度
        instance.progress = new_progress
        
        # 如果进度为100%，并且状态不是已完成，则自动变更为已完成
        if new_progress == 100 and instance.status != TaskStatus.COMPLETED:
            instance.status = TaskStatus.COMPLETED
        
        instance.save()
        
        # 创建系统评论记录进度变更
        if old_progress != new_progress:
            content = f"任务进度从 {old_progress}% 更新为 {new_progress}%"
            if comment_text:
                content += f"\n\n备注: {comment_text}"
            
            user = self.context.get('request').user
            TaskComment.objects.create(
                task=instance,
                content=content,
                created_by_user=user,
                is_system_comment=True,
                metadata={
                    'from_progress': old_progress,
                    'to_progress': new_progress
                }
            )
        
        return instance

class TaskBulkActionSerializer(serializers.Serializer):
    """批量任务操作序列化器"""
    task_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(choices=[
        'update_status', 'update_priority', 'add_tag', 'remove_tag',
        'assign_user', 'assign_agent', 'unassign'
    ])
    value = serializers.JSONField(required=False)  # 操作参数，根据action不同而不同
    comment = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """根据不同action验证value字段"""
        action = data.get('action')
        value = data.get('value', {})
        
        if action == 'update_status':
            if 'status' not in value:
                raise serializers.ValidationError({'value': _('必须提供status字段')})
            if value['status'] not in dict(TaskStatus.choices):
                raise serializers.ValidationError({'value': _('无效的任务状态')})
                
        elif action == 'update_priority':
            if 'priority' not in value:
                raise serializers.ValidationError({'value': _('必须提供priority字段')})
            if value['priority'] not in dict(TaskPriority.choices):
                raise serializers.ValidationError({'value': _('无效的任务优先级')})
                
        elif action == 'add_tag' or action == 'remove_tag':
            if 'tag_id' not in value:
                raise serializers.ValidationError({'value': _('必须提供tag_id字段')})
            try:
                TaskTag.objects.get(id=value['tag_id'])
            except TaskTag.DoesNotExist:
                raise serializers.ValidationError({'value': _('指定的标签不存在')})
                
        elif action == 'assign_user':
            if 'user_id' not in value:
                raise serializers.ValidationError({'value': _('必须提供user_id字段')})
            try:
                User.objects.get(id=value['user_id'])
            except User.DoesNotExist:
                raise serializers.ValidationError({'value': _('指定的用户不存在')})
                
        elif action == 'assign_agent':
            if 'agent_id' not in value:
                raise serializers.ValidationError({'value': _('必须提供agent_id字段')})
            try:
                Agent.objects.get(id=value['agent_id'])
            except Agent.DoesNotExist:
                raise serializers.ValidationError({'value': _('指定的代理不存在')})
        
        return data

class BulkTaskUpdateSerializer(serializers.Serializer):
    """用于批量更新任务的序列化器"""
    task_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    progress = serializers.IntegerField(min_value=0, max_value=100, required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """验证至少有一个字段需要更新"""
        update_fields = ['status', 'priority', 'due_date', 'progress']
        has_update = any(field in data for field in update_fields)
        
        if not has_update:
            raise serializers.ValidationError(_('至少需要提供一个要更新的字段'))
            
        return data 