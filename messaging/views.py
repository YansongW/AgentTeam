from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging
import json
from datetime import timedelta

from .models import Message, MessageDeliveryStatus
from .serializers import MessageSerializer, MessageDeliveryStatusSerializer
from .validators import validate_message, create_message
from groups.permissions import IsGroupMember
from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import MessageErrorCodes, GroupErrorCodes

logger = logging.getLogger(__name__)

# 添加WebSocket测试页面视图
def websocket_test(request):
    """
    渲染WebSocket测试页面
    """
    return render(request, 'messaging/websocket_test.html')

class MessageViewSet(viewsets.ModelViewSet):
    """
    消息的API视图集
    提供消息的列表、详情、创建、更新、删除等功能
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """获取消息列表"""
        user = self.request.user
        
        # 管理员可以看到所有消息
        if user.is_staff:
            return Message.objects.all()
            
        # 获取用户可以看到的消息（发给自己的、发给自己所在群组的、自己发送的）
        return Message.objects.filter(
            Q(recipient_user=user) |  # 直接发给用户的消息
            Q(group__members__user=user, group__members__is_active=True) |  # 发给用户所在群组的消息
            Q(sender_user=user)  # 用户自己发送的消息
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        """创建新消息"""
        data = request.data
        
        # 校验消息格式
        is_valid, error = validate_message(data)
        if not is_valid:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        
        # 使用模型类的方法创建消息
        try:
            message = Message.from_json_message(data)
            serializer = self.get_serializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"创建消息失败: {str(e)}")
            return Response(
                {"error": f"创建消息失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        """获取与当前用户相关的所有消息"""
        user = request.user
        
        # 支持时间范围筛选
        hours = int(request.query_params.get('hours', 24))
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        # 支持消息数量限制
        limit = int(request.query_params.get('limit', 50))
        
        # 支持消息类型筛选
        message_type = request.query_params.get('type')
        
        # 查询消息
        queryset = self.get_queryset().filter(created_at__gte=time_threshold)
        if message_type:
            queryset = queryset.filter(message_type=message_type)
            
        queryset = queryset.order_by('-created_at')[:limit]
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message_count': len(serializer.data),
            'messages': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def send_to_group(self, request):
        """发送消息到群组"""
        user = request.user
        group_id = request.data.get('group_id')
        content = request.data.get('content')
        message_type = request.data.get('message_type', 'chat')
        
        if not group_id or not content:
            return ErrorUtils.format_error_response(
                error_code=MessageErrorCodes.MISSING_REQUIRED_FIELD,
                message="缺少必要参数group_id或content",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        from groups.models import Group
        
        # 检查群组是否存在
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return ErrorUtils.format_error_response(
                error_code=GroupErrorCodes.GROUP_NOT_FOUND,
                message="找不到指定的群组",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查用户是否是群组成员
        if not IsGroupMember().has_object_permission(request, self, group):
            return ErrorUtils.format_error_response(
                error_code=GroupErrorCodes.NOT_GROUP_MEMBER,
                message="您不是该群组的成员，无权发送消息",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        # 创建符合Schema的消息对象
        try:
            message_data = create_message(
                message_type=message_type,
                sender={
                    "id": str(user.id),
                    "type": "user",
                    "name": user.username
                },
                payload={
                    "text": content.get('text', ''),
                    "group_id": str(group_id),
                    "mentions": content.get('mentions', [])
                },
                metadata=request.data.get('metadata', {})
            )
            
            # 保存到数据库
            message = Message.from_json_message(message_data)
            
            # 创建消息传递状态记录（标记为已送达，但未读）
            for member in group.get_human_members():
                if member.user.id != user.id:  # 不给发送者自己创建记录
                    MessageDeliveryStatus.objects.create(
                        message=message,
                        user=member.user,
                        is_delivered=True,
                        delivered_at=timezone.now()
                    )
            
            serializer = self.get_serializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # 使用新的错误处理工具
            logger.error(f"发送消息到群组失败: {str(e)}", exc_info=True)
            return ErrorUtils.handle_exception(
                request, 
                e, 
                MessageErrorCodes.SEND_FAILED,
                "发送消息失败，请稍后再试"
            )
    
    @action(detail=False, methods=['post'])
    def send_to_user(self, request):
        """发送消息给用户"""
        user = request.user
        recipient_id = request.data.get('recipient_id')
        content = request.data.get('content')
        message_type = request.data.get('message_type', 'chat')
        
        if not recipient_id or not content:
            return Response(
                {"error": "缺少必要参数recipient_id或content"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # 检查接收用户是否存在
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response(
                {"error": "找不到指定的用户"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 创建符合Schema的消息对象
        try:
            message_data = create_message(
                message_type=message_type,
                sender={
                    "id": str(user.id),
                    "type": "user",
                    "name": user.username
                },
                payload={
                    "text": content.get('text', ''),
                    "mentions": content.get('mentions', [])
                },
                metadata=request.data.get('metadata', {})
            )
            
            # 保存到数据库
            message = Message.from_json_message(message_data)
            message.recipient_user = recipient
            message.save()
            
            # 创建消息传递状态记录（标记为已送达，但未读）
            MessageDeliveryStatus.objects.create(
                message=message,
                user=recipient,
                is_delivered=True,
                delivered_at=timezone.now()
            )
            
            serializer = self.get_serializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"发送消息给用户失败: {str(e)}")
            return Response(
                {"error": f"发送消息失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        将消息标记为已读
        """
        message = self.get_object()
        status_obj, created = MessageDeliveryStatus.objects.get_or_create(
            message=message,
            recipient=request.user,
            defaults={'status': 'read'}
        )
        
        if not created:
            status_obj.status = 'read'
            status_obj.save()
        
        return Response({'status': 'message marked as read'})

class MessageDeliveryStatusViewSet(viewsets.ModelViewSet):
    """
    消息传递状态的API视图集
    提供消息状态的列表、详情、更新等功能
    """
    serializer_class = MessageDeliveryStatusSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取消息状态列表"""
        user = self.request.user
        
        # 管理员可以看到所有消息状态
        if user.is_staff:
            return MessageDeliveryStatus.objects.all()
            
        # 普通用户只能看到与自己相关的消息状态
        return MessageDeliveryStatus.objects.filter(user=user)
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """标记消息为已读"""
        user = request.user
        message_ids = request.data.get('message_ids', [])
        
        if not message_ids:
            return Response(
                {"error": "缺少必要参数message_ids"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 获取当前用户的指定消息的传递状态记录
            statuses = MessageDeliveryStatus.objects.filter(
                message__id__in=message_ids,
                user=user
            )
            
            # 更新为已读
            for status in statuses:
                if not status.is_read:
                    status.is_read = True
                    status.read_at = timezone.now()
                    status.save()
            
            return Response({
                "message": f"已成功标记 {statuses.count()} 条消息为已读"
            })
            
        except Exception as e:
            logger.error(f"标记消息为已读失败: {str(e)}")
            return Response(
                {"error": f"标记消息为已读失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """获取未读消息数量"""
        user = request.user
        
        try:
            # 获取未读消息数量
            count = MessageDeliveryStatus.objects.filter(
                user=user,
                is_delivered=True,
                is_read=False
            ).count()
            
            return Response({
                "unread_count": count
            })
            
        except Exception as e:
            logger.error(f"获取未读消息数量失败: {str(e)}")
            return Response(
                {"error": f"获取未读消息数量失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def my_statuses(self, request):
        """
        获取当前用户的所有消息状态
        """
        statuses = self.get_queryset().order_by('-updated_at')
        serializer = self.get_serializer(statuses, many=True)
        return Response(serializer.data)
