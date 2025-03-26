from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction

from rest_framework import viewsets, permissions, status, filters, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from agents.models import Agent
from agents.permissions import IsAgentOwnerOrAdmin
from groups.permissions import IsGroupMember, IsGroupOwnerOrAdmin

from .models import (
    Task, TaskAssignment, TaskComment, 
    TaskTag, TaskTagAssignment, TaskDependency,
    TaskStatus, TaskPriority, TaskType
)
from .serializers import (
    TaskSerializer, TaskDetailSerializer, TaskMinimalSerializer,
    TaskCommentSerializer, TaskAssignmentSerializer,
    TaskTagSerializer, TaskTagAssignmentSerializer, TaskDependencySerializer,
    TaskStatusUpdateSerializer, TaskPriorityUpdateSerializer, TaskProgressUpdateSerializer,
    TaskBulkActionSerializer, BulkTaskUpdateSerializer
)

class StandardResultsSetPagination(PageNumberPagination):
    """标准分页器"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class TaskViewSet(viewsets.ModelViewSet):
    """任务管理视图集"""
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'task_type', 'creator', 'group', 'parent_task']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'priority', 'status', 'progress']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """根据用户权限过滤任务"""
        user = self.request.user
        if not user.is_authenticated:
            return Task.objects.none()
            
        # 获取任务关联数据及计数
        queryset = Task.objects.select_related(
            'creator', 'group', 'parent_task'
        ).prefetch_related(
            'assignments', 'tag_assignments', 'comments', 'subtasks'
        ).annotate(
            comments_count=Count('comments'),
            subtasks_count=Count('subtasks'),
            dependencies_count=Count('dependencies'),
            dependents_count=Count('dependents')
        )
        
        # 获取与用户相关的任务
        if not user.is_staff:
            # 用户创建的任务
            own_tasks = Q(creator=user)
            # 用户作为成员的群组任务
            from groups.models import GroupMember
            user_group_memberships = GroupMember.objects.filter(user=user)
            user_groups = [gm.group for gm in user_group_memberships]
            group_tasks = Q(group__in=user_groups) if user_groups else Q()
            # 分配给用户的任务
            assigned_tasks = Q(assignments__assigned_user=user)
            
            queryset = queryset.filter(own_tasks | group_tasks | assigned_tasks).distinct()
        
        # 其他过滤参数处理
        group_id = self.request.query_params.get('group_id')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
            
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority=priority_param)
            
        # 任务类型过滤
        task_type_param = self.request.query_params.get('task_type')
        if task_type_param:
            queryset = queryset.filter(task_type=task_type_param)
            
        # 截止日期过滤
        due_date_from = self.request.query_params.get('due_date_from')
        if due_date_from:
            queryset = queryset.filter(due_date__gte=due_date_from)
            
        due_date_to = self.request.query_params.get('due_date_to')
        if due_date_to:
            queryset = queryset.filter(due_date__lte=due_date_to)
            
        # 标签过滤
        tag_id = self.request.query_params.get('tag_id')
        if tag_id:
            queryset = queryset.filter(tag_assignments__tag_id=tag_id)
            
        # 分配对象过滤
        assigned_user_id = self.request.query_params.get('assigned_user_id')
        if assigned_user_id:
            queryset = queryset.filter(assignments__assigned_user_id=assigned_user_id)
            
        assigned_agent_id = self.request.query_params.get('assigned_agent_id')
        if assigned_agent_id:
            queryset = queryset.filter(assignments__assigned_agent_id=assigned_agent_id)
        
        return queryset
    
    def get_serializer_class(self):
        """根据操作选择合适的序列化器"""
        if self.action == 'retrieve':
            return TaskDetailSerializer
        elif self.action == 'list':
            if self.request.query_params.get('minimal') == 'true':
                return TaskMinimalSerializer
        elif self.action == 'update_status':
            return TaskStatusUpdateSerializer
        elif self.action == 'update_priority':
            return TaskPriorityUpdateSerializer
        elif self.action == 'update_progress':
            return TaskProgressUpdateSerializer
        elif self.action == 'bulk_action':
            return TaskBulkActionSerializer
        return TaskSerializer
    
    def get_permissions(self):
        """根据操作设置权限"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """创建任务时自动设置当前用户为创建者"""
        serializer.save(creator=self.request.user)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """更新任务状态"""
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TaskSerializer(task).data)
    
    @action(detail=True, methods=['patch'])
    def update_priority(self, request, pk=None):
        """更新任务优先级"""
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TaskSerializer(task).data)
    
    @action(detail=True, methods=['patch'])
    def update_progress(self, request, pk=None):
        """更新任务进度"""
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TaskSerializer(task).data)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """批量操作任务"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        task_ids = serializer.validated_data['task_ids']
        action = serializer.validated_data['action']
        value = serializer.validated_data.get('value', {})
        comment = serializer.validated_data.get('comment', '')
        
        # 获取用户有权限的任务
        tasks = self.get_queryset().filter(id__in=task_ids)
        
        if not tasks:
            return Response(
                {'detail': _('未找到符合条件的任务')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        with transaction.atomic():
            # 根据不同操作执行相应逻辑
            if action == 'update_status':
                new_status = value.get('status')
                for task in tasks:
                    # 使用之前定义的序列化器来保持一致的业务逻辑
                    status_serializer = TaskStatusUpdateSerializer(
                        task, 
                        data={'status': new_status, 'comment': comment},
                        context={'request': request}
                    )
                    if status_serializer.is_valid():
                        status_serializer.save()
            
            elif action == 'update_priority':
                new_priority = value.get('priority')
                for task in tasks:
                    priority_serializer = TaskPriorityUpdateSerializer(
                        task,
                        data={'priority': new_priority, 'comment': comment},
                        context={'request': request}
                    )
                    if priority_serializer.is_valid():
                        priority_serializer.save()
            
            elif action == 'add_tag':
                tag_id = value.get('tag_id')
                tag = get_object_or_404(TaskTag, id=tag_id)
                for task in tasks:
                    # 如果标签不存在则创建
                    if not TaskTagAssignment.objects.filter(task=task, tag=tag).exists():
                        TaskTagAssignment.objects.create(
                            task=task,
                            tag=tag,
                            assigned_by=request.user
                        )
            
            elif action == 'remove_tag':
                tag_id = value.get('tag_id')
                TaskTagAssignment.objects.filter(
                    task__in=tasks,
                    tag_id=tag_id
                ).delete()
            
            elif action == 'assign_user':
                user_id = value.get('user_id')
                user = get_object_or_404(User, id=user_id)
                for task in tasks:
                    # 检查是否已经分配
                    if not TaskAssignment.objects.filter(task=task, assigned_user=user).exists():
                        TaskAssignment.objects.create(
                            task=task,
                            assigned_user=user,
                            assigned_by=request.user,
                            is_primary=value.get('is_primary', False),
                            role=value.get('role', '')
                        )
            
            elif action == 'assign_agent':
                agent_id = value.get('agent_id')
                agent = get_object_or_404(Agent, id=agent_id)
                for task in tasks:
                    # 检查是否已经分配
                    if not TaskAssignment.objects.filter(task=task, assigned_agent=agent).exists():
                        TaskAssignment.objects.create(
                            task=task,
                            assigned_agent=agent,
                            assigned_by=request.user,
                            is_primary=value.get('is_primary', False),
                            role=value.get('role', '')
                        )
            
            elif action == 'unassign':
                # 获取要取消分配的用户或代理
                user_id = value.get('user_id')
                agent_id = value.get('agent_id')
                
                if user_id:
                    TaskAssignment.objects.filter(
                        task__in=tasks,
                        assigned_user_id=user_id
                    ).delete()
                    
                elif agent_id:
                    TaskAssignment.objects.filter(
                        task__in=tasks,
                        assigned_agent_id=agent_id
                    ).delete()
                    
                else:
                    # 取消所有分配
                    TaskAssignment.objects.filter(task__in=tasks).delete()
        
        return Response({'detail': _('批量操作成功'), 'affected_tasks': len(tasks)})
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """获取任务评论"""
        task = self.get_object()
        comments = task.comments.order_by('created_at')
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = TaskCommentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskCommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """添加任务评论"""
        task = self.get_object()
        serializer = TaskCommentSerializer(data={
            'task': task.id,
            'content': request.data.get('content', ''),
            'created_by_user': request.user.id,
            'is_system_comment': request.data.get('is_system_comment', False),
            'is_status_update': request.data.get('is_status_update', False),
            'metadata': request.data.get('metadata', {})
        })
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return Response(TaskCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """获取任务分配"""
        task = self.get_object()
        assignments = task.assignments.all()
        serializer = TaskAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """分配任务"""
        task = self.get_object()
        
        # 检查参数
        assigned_user_id = request.data.get('assigned_user_id')
        assigned_agent_id = request.data.get('assigned_agent_id')
        
        if (not assigned_user_id and not assigned_agent_id) or (assigned_user_id and assigned_agent_id):
            return Response(
                {'detail': _('必须指定用户或代理其中之一')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 准备数据
        assignment_data = {
            'task': task.id,
            'assigned_by': request.user.id,
            'is_primary': request.data.get('is_primary', False),
            'role': request.data.get('role', ''),
            'notes': request.data.get('notes', '')
        }
        
        if assigned_user_id:
            assignment_data['assigned_user'] = assigned_user_id
        else:
            assignment_data['assigned_agent'] = assigned_agent_id
        
        # 创建或更新分配
        serializer = TaskAssignmentSerializer(data=assignment_data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        
        return Response(TaskAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

class TaskCommentViewSet(viewsets.ModelViewSet):
    """任务评论视图集"""
    queryset = TaskComment.objects.all()
    serializer_class = TaskCommentSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'created_by_user', 'created_by_agent', 'is_system_comment', 'is_status_update']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def get_queryset(self):
        """根据用户权限过滤评论"""
        user = self.request.user
        if not user.is_authenticated:
            return TaskComment.objects.none()
            
        queryset = TaskComment.objects.select_related(
            'task', 'created_by_user', 'created_by_agent'
        )
        
        # 普通用户只能看到自己有权限的任务的评论
        if not user.is_staff:
            # 用户创建的任务评论
            own_task_comments = Q(task__creator=user)
            # 用户作为成员的群组任务评论
            group_task_comments = Q(task__group__members=user)
            # 分配给用户的任务评论
            assigned_task_comments = Q(task__assignments__assigned_user=user)
            
            queryset = queryset.filter(
                own_task_comments | group_task_comments | assigned_task_comments
            ).distinct()
        
        return queryset
    
    def perform_create(self, serializer):
        """创建评论时自动设置当前用户为创建者"""
        # 检查是否是系统评论
        is_system_comment = self.request.data.get('is_system_comment', False)
        if not is_system_comment:
            serializer.save(created_by_user=self.request.user)
        else:
            serializer.save()

class TaskTagViewSet(viewsets.ModelViewSet):
    """任务标签视图集"""
    queryset = TaskTag.objects.all()
    serializer_class = TaskTagSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        """管理员可以管理标签，普通用户只能查看"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

# 添加前端模板视图
class TaskListView(LoginRequiredMixin, TemplateView):
    """
    任务管理列表页面
    """
    template_name = 'tasks/task_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
