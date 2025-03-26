from django.shortcuts import render, redirect
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import logging
from datetime import timedelta
from django.utils import timezone
from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import GroupErrorCodes, UserErrorCodes
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Group, GroupMember, GroupMessage, GroupRule
from .serializers import (
    GroupSerializer, GroupCreateSerializer, GroupMemberSerializer,
    GroupMessageSerializer, GroupRuleSerializer
)
from .permissions import (
    IsGroupOwnerOrAdmin, IsGroupMember, IsMessageSender, CanJoinPublicGroup
)
from agents.models import Agent

logger = logging.getLogger(__name__)


class GroupViewSet(viewsets.ModelViewSet):
    """
    群组的API视图集
    提供群组的列表、详情、创建、更新、删除等功能
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """
        获取查询集，根据请求参数过滤
        """
        queryset = Group.objects.all()
        
        # 筛选当前用户拥有的群组
        is_owner = self.request.query_params.get('is_owner', None)
        if is_owner == 'true':
            queryset = queryset.filter(owner=self.request.user)
        
        # 筛选当前用户参与的群组
        is_member = self.request.query_params.get('is_member', None)
        if is_member == 'true':
            queryset = queryset.filter(members__user=self.request.user)
        
        # 筛选公开的群组
        is_public = self.request.query_params.get('is_public', None)
        if is_public == 'true':
            queryset = queryset.filter(is_public=True)
        
        # 排除当前用户已加入的群组
        not_member = self.request.query_params.get('not_member', None)
        if not_member == 'true':
            user_groups = GroupMember.objects.filter(user=self.request.user).values_list('group', flat=True)
            queryset = queryset.exclude(id__in=user_groups)
        
        return queryset
        
    def get_serializer_class(self):
        """根据操作选择不同的序列化器"""
        if self.action == 'create':
            return GroupCreateSerializer
        return GroupSerializer
        
    def get_permissions(self):
        """根据不同操作设置不同权限"""
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsGroupOwnerOrAdmin]
        elif self.action in ['join']:
            self.permission_classes = [IsAuthenticated, CanJoinPublicGroup]
        elif self.action in ['leave', 'members', 'messages', 'add_agent']:
            self.permission_classes = [IsAuthenticated, IsGroupMember]
        return super().get_permissions()
        
    @action(detail=False, methods=['get'])
    def my_groups(self, request):
        """获取当前用户的群组"""
        user = request.user
        queryset = Group.objects.filter(
            Q(owner=user) |
            Q(members__user=user, members__is_active=True)
        ).distinct()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def public_groups(self, request):
        """获取公开群组"""
        queryset = Group.objects.filter(is_public=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        加入群组的API端点
        """
        group = self.get_object()
        
        # 检查用户是否已经是群组成员
        if GroupMember.objects.filter(group=group, user=request.user).exists():
            return Response({"detail": "您已经是该群组的成员"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查群组是否是私有的
        if not group.is_public:
            return Response({"detail": "您无法加入私有群组"}, status=status.HTTP_403_FORBIDDEN)
        
        # 添加用户为群组成员
        GroupMember.objects.create(
            group=group,
            user=request.user,
            role='member'
        )
        
        return Response({"detail": "成功加入群组"}, status=status.HTTP_200_OK)
        
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        离开群组的API端点
        """
        group = self.get_object()
        
        # 检查用户是否是群组成员
        try:
            member = GroupMember.objects.get(group=group, user=request.user)
        except GroupMember.DoesNotExist:
            return Response({"detail": "您不是该群组的成员"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查用户是否是群主
        if member.role == 'owner':
            return Response({"detail": "群主无法离开群组，请先转让群主身份"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 删除群组成员关系
        member.delete()
        
        return Response({"detail": "已成功离开群组"}, status=status.HTTP_200_OK)
        
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取群组成员列表"""
        group = self.get_object()
        queryset = group.members.filter(is_active=True)
        
        # 支持按角色筛选
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
            
        # 支持按类型筛选
        member_type = request.query_params.get('type')
        if member_type:
            queryset = queryset.filter(member_type=member_type)
            
        serializer = GroupMemberSerializer(queryset, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def add_agent(self, request, pk=None):
        """添加AI代理到群组"""
        group = self.get_object()
        agent_id = request.data.get('agent_id')
        
        if not agent_id:
            return Response(
                {"error": "缺少必要参数agent_id"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 检查代理是否存在且属于当前用户
        try:
            agent = Agent.objects.get(
                Q(id=agent_id),
                Q(owner=request.user) | Q(is_public=True)
            )
        except Agent.DoesNotExist:
            return Response(
                {"error": "找不到指定的代理或您没有使用此代理的权限"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # 检查代理是否已在群组
        if GroupMember.objects.filter(group=group, agent=agent, is_active=True).exists():
            return Response(
                {"error": "该代理已经是群组成员"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 添加代理到群组
        member = GroupMember.objects.create(
            group=group,
            agent=agent,
            member_type=GroupMember.MemberType.AGENT,
            role=GroupMember.Role.MEMBER
        )
        
        # 创建系统消息
        GroupMessage.objects.create(
            group=group,
            sender_type=GroupMessage.SenderType.SYSTEM,
            message_type=GroupMessage.MessageType.SYSTEM,
            content={"text": f"代理 {agent.name} 被添加到群组"}
        )
        
        serializer = GroupMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """添加成员到群组"""
        try:
            group = self.get_object()
            user_id = request.data.get('user_id')
            
            if not user_id:
                return ErrorUtils.format_error_response(
                    error_code=GroupErrorCodes.MISSING_REQUIRED_FIELD,
                    message="需要提供user_id参数",
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            
            from users.models import User
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return ErrorUtils.format_error_response(
                    error_code=UserErrorCodes.USER_NOT_FOUND,
                    message="找不到指定的用户",
                    http_status=status.HTTP_404_NOT_FOUND
                )
            
            # 检查用户是否已经是成员
            if GroupMember.objects.filter(group=group, user=user).exists():
                return ErrorUtils.format_error_response(
                    error_code=GroupErrorCodes.MEMBER_ALREADY_EXISTS,
                    message="该用户已经是群组成员",
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            
            # 添加用户到群组
            member = GroupMember.objects.create(
                group=group,
                user=user,
                role='member'
            )
            
            serializer = GroupMemberSerializer(member)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"添加群组成员失败: {str(e)}", exc_info=True)
            return ErrorUtils.handle_exception(
                request,
                e,
                GroupErrorCodes.ADD_MEMBER_FAILED,
                "添加群组成员失败，请稍后再试"
            )
        
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """从群组中移除成员"""
        try:
            group = self.get_object()
            user_id = request.data.get('user_id')
            
            if not user_id:
                return ErrorUtils.format_error_response(
                    error_code=GroupErrorCodes.MISSING_REQUIRED_FIELD,
                    message="需要提供user_id参数",
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            
            from users.models import User
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return ErrorUtils.format_error_response(
                    error_code=UserErrorCodes.USER_NOT_FOUND,
                    message="找不到指定的用户",
                    http_status=status.HTTP_404_NOT_FOUND
                )
            
            # 检查用户是否是成员
            try:
                member = GroupMember.objects.get(group=group, user=user)
            except GroupMember.DoesNotExist:
                return ErrorUtils.format_error_response(
                    error_code=GroupErrorCodes.MEMBER_NOT_FOUND,
                    message="该用户不是群组成员",
                    http_status=status.HTTP_404_NOT_FOUND
                )
            
            # 不能移除群主
            if member.role == 'owner':
                return ErrorUtils.format_error_response(
                    error_code=GroupErrorCodes.CANNOT_REMOVE_OWNER,
                    message="不能移除群主",
                    http_status=status.HTTP_403_FORBIDDEN
                )
            
            # 移除成员
            member.delete()
            return Response({"detail": "成员已移除"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"移除群组成员失败: {str(e)}", exc_info=True)
            return ErrorUtils.handle_exception(
                request,
                e,
                GroupErrorCodes.REMOVE_MEMBER_FAILED,
                "移除群组成员失败，请稍后再试"
            )
        
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """获取群组消息列表"""
        group = self.get_object()
        
        # 支持时间范围筛选
        hours = int(request.query_params.get('hours', 24))
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        # 支持消息数量限制
        limit = int(request.query_params.get('limit', 50))
        
        # 支持消息类型筛选
        message_type = request.query_params.get('type')
        
        # 查询消息
        queryset = group.messages.filter(timestamp__gte=time_threshold)
        if message_type:
            queryset = queryset.filter(message_type=message_type)
            
        queryset = queryset.order_by('-timestamp')[:limit]
        
        serializer = GroupMessageSerializer(queryset, many=True)
        
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'message_count': len(serializer.data),
            'messages': serializer.data
        })
        
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """发送消息到群组"""
        group = self.get_object()
        user = request.user
        
        # 获取必要参数
        content = request.data.get('content')
        message_type = request.data.get('message_type', GroupMessage.MessageType.TEXT)
        parent_message_id = request.data.get('parent_message_id')
        
        if not content:
            return Response(
                {"error": "消息内容不能为空"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 构建消息数据
        message_data = {
            'group': group.id,
            'sender_user': user.id,
            'sender_type': GroupMessage.SenderType.HUMAN,
            'content': content,
            'message_type': message_type
        }
        
        # 如果是回复消息，添加父消息ID
        if parent_message_id:
            try:
                parent_message = GroupMessage.objects.get(id=parent_message_id, group=group)
                message_data['parent_message'] = parent_message.id
            except GroupMessage.DoesNotExist:
                return Response(
                    {"error": "找不到指定的父消息"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # 创建消息
        serializer = GroupMessageSerializer(data=message_data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            
            # 检查是否需要触发代理响应
            self._trigger_agent_responses(message)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def _trigger_agent_responses(self, message):
        """触发代理响应（处理@提及的代理）"""
        try:
            # 获取提及的代理
            mentioned_agents = message.mentioned_agents.all()
            
            # 如果没有明确提及代理，检查消息内容是否包含@agent:格式
            if not mentioned_agents:
                pass  # 已在创建消息时处理
                
            # 对每个被提及的代理创建响应任务
            for agent in mentioned_agents:
                # 检查代理是否在群组中
                if not GroupMember.objects.filter(
                    group=message.group,
                    agent=agent,
                    is_active=True
                ).exists():
                    continue
                    
                # 调用代理API生成响应（异步任务）
                self._generate_agent_response.delay(
                    message.id,
                    agent.id,
                    message.content.get('text', '')
                )
        except Exception as e:
            logger.error(f"触发代理响应时发生错误: {str(e)}")
            
    def _generate_agent_response(self, message_id, agent_id, message_text):
        """生成代理响应（应该作为异步任务运行）"""
        try:
            # 获取原始消息和代理
            message = GroupMessage.objects.get(id=message_id)
            agent = Agent.objects.get(id=agent_id)
            
            # 检查代理是否可用
            if not agent.is_available():
                # 创建系统消息表示代理不可用
                GroupMessage.objects.create(
                    group=message.group,
                    sender_type=GroupMessage.SenderType.SYSTEM,
                    message_type=GroupMessage.MessageType.SYSTEM,
                    content={"text": f"代理 {agent.name} 当前不可用，无法响应"}
                )
                return
                
            # 获取最近的群组消息作为上下文
            recent_messages = message.group.messages.filter(
                timestamp__lt=message.timestamp
            ).order_by('-timestamp')[:10]
            
            # 构建上下文
            context = {
                'group_name': message.group.name,
                'recent_messages': [
                    {
                        'sender': msg.get_sender_name() if hasattr(msg, 'get_sender_name') else 'Unknown',
                        'text': msg.content.get('text', ''),
                        'timestamp': msg.timestamp
                    }
                    for msg in reversed(list(recent_messages))
                ]
            }
            
            # 调用Agent API生成响应
            from agents.views import AgentViewSet
            agent_view = AgentViewSet()
            response_text = agent_view._generate_ai_response(agent, message_text, context)
            
            # 创建代理响应消息
            GroupMessage.objects.create(
                group=message.group,
                sender_agent=agent,
                sender_type=GroupMessage.SenderType.AGENT,
                message_type=GroupMessage.MessageType.TEXT,
                content={"text": response_text},
                parent_message=message
            )
            
        except Exception as e:
            logger.error(f"生成代理响应时发生错误: {str(e)}")

    def perform_create(self, serializer):
        """
        创建群组时设置当前用户为群主
        """
        group = serializer.save(owner=self.request.user)
        
        # 自动将群主添加为群组成员
        GroupMember.objects.create(
            group=group,
            user=self.request.user,
            role='owner'
        )
        
        # 如果请求中包含代理列表，则添加这些代理到群组
        agents = self.request.data.get('agents', [])
        if agents:
            for agent_id in agents:
                GroupMember.objects.create(
                    group=group,
                    agent_id=agent_id,
                    role='member'
                )


class GroupMemberViewSet(viewsets.ModelViewSet):
    """
    群组成员的API视图集
    提供成员的列表、详情、创建、更新、删除等功能
    """
    serializer_class = GroupMemberSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['joined_at', 'role']
    ordering = ['joined_at']
    
    def get_queryset(self):
        """获取群组成员列表"""
        user = self.request.user
        
        # 管理员可以看到所有群组成员
        if user.is_staff:
            return GroupMember.objects.all()
            
        # 普通用户只能看到自己所在群组的成员
        return GroupMember.objects.filter(
            Q(group__owner=user) |  # 自己创建的群组的成员
            Q(group__members__user=user, group__members__is_active=True)  # 自己加入的群组的成员
        ).distinct()
        
    def get_permissions(self):
        """根据不同操作设置不同权限"""
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsGroupOwnerOrAdmin]
        return super().get_permissions()
        
    def perform_create(self, serializer):
        """创建成员时的额外处理"""
        # 添加验证逻辑确保当前用户有权限添加成员
        group = serializer.validated_data['group']
        user = self.request.user
        
        # 检查用户是否是群组所有者或管理员
        is_owner = group.owner == user
        is_admin = GroupMember.objects.filter(
            group=group, user=user, role=GroupMember.Role.ADMIN, is_active=True
        ).exists()
        
        if not (is_owner or is_admin or user.is_staff):
            raise PermissionError("您没有权限添加成员到此群组")
            
        serializer.save()


class GroupMessageViewSet(viewsets.ModelViewSet):
    """
    群组消息的API视图集
    提供消息的列表、详情、创建、更新、删除等功能
    """
    serializer_class = GroupMessageSerializer
    permission_classes = [IsAuthenticated, IsGroupMember]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """获取群组消息列表"""
        user = self.request.user
        
        # 管理员可以看到所有消息
        if user.is_staff:
            return GroupMessage.objects.all()
            
        # 普通用户只能看到自己所在群组的消息
        user_groups = Group.objects.filter(
            Q(owner=user) |
            Q(members__user=user, members__is_active=True)
        )
        
        return GroupMessage.objects.filter(group__in=user_groups)
        
    def get_permissions(self):
        """根据不同操作设置不同权限"""
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsMessageSender]
        return super().get_permissions()
        
    def perform_create(self, serializer):
        """创建消息时的额外处理"""
        # 设置发送者为当前用户
        serializer.save(sender_user=self.request.user, sender_type=GroupMessage.SenderType.HUMAN)


class GroupRuleViewSet(viewsets.ModelViewSet):
    """
    群组规则的API视图集
    提供规则的列表、详情、创建、更新、删除等功能
    """
    serializer_class = GroupRuleSerializer
    permission_classes = [IsAuthenticated, IsGroupOwnerOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['priority', 'created_at']
    ordering = ['-priority', 'created_at']
    
    def get_queryset(self):
        """获取群组规则列表"""
        user = self.request.user
        
        # 管理员可以看到所有规则
        if user.is_staff:
            return GroupRule.objects.all()
            
        # 普通用户只能看到自己创建的群组的规则和自己管理的群组的规则
        return GroupRule.objects.filter(
            Q(group__owner=user) |
            Q(group__members__user=user, group__members__role=GroupMember.Role.ADMIN, group__members__is_active=True)
        ).distinct()

# 添加群组管理页面的视图函数
def group_management(request):
    """
    群组管理页面视图
    """
    return render(request, 'groups/group_management.html', {})

# 群聊页面视图
@login_required
def group_chat_view(request, group_id):
    """
    显示群聊界面
    """
    try:
        group = Group.objects.get(id=group_id)
        # 检查用户是否是群组成员
        if not GroupMember.objects.filter(group=group, user=request.user).exists():
            messages.error(request, "您不是该群组的成员")
            return redirect('group_management')
            
        return render(request, 'groups/chat_interface.html', {
            'group': group,
        })
    except Group.DoesNotExist:
        messages.error(request, "群组不存在")
        return redirect('group_management')
