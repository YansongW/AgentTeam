from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Message, MessageDeliveryStatus
from agents.serializers import AgentSerializer

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """用户基本信息序列化器"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'avatar')
        read_only_fields = ('email',)


class MessageSerializer(serializers.ModelSerializer):
    """消息序列化器"""
    sender_user_details = UserBasicSerializer(source='sender_user', read_only=True)
    sender_agent_details = AgentSerializer(source='sender_agent', read_only=True)
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = (
            'id', 'message_type', 'content', 'created_at', 
            'sender_type', 'sender_user', 'sender_agent', 
            'group', 'recipient_user', 'parent_message',
            'metadata', 'sender_user_details', 'sender_agent_details',
            'sender_name'
        )
        read_only_fields = ('created_at',)
    
    def get_sender_name(self, obj):
        """获取发送者名称"""
        return obj.get_sender_name()
    
    def to_representation(self, instance):
        """自定义输出表示"""
        data = super().to_representation(instance)
        
        # 添加 mentioned_users 和 mentioned_agents
        data['mentioned_users'] = UserBasicSerializer(
            instance.mentioned_users.all(),
            many=True
        ).data
        
        data['mentioned_agents'] = AgentSerializer(
            instance.mentioned_agents.all(),
            many=True
        ).data
        
        # 转换为符合消息Schema的格式
        json_message = {
            "message_id": str(data['id']),
            "message_type": data['message_type'],
            "sender": {
                "id": str(data['sender_user'] if data['sender_type'] == 'user' 
                       else (data['sender_agent'] if data['sender_type'] == 'agent' else "system")),
                "type": data['sender_type'],
                "name": data['sender_name']
            },
            "timestamp": data['created_at'],
            "payload": data['content'],
            "metadata": data['metadata'] or {}
        }
        
        return json_message


class MessageDeliveryStatusSerializer(serializers.ModelSerializer):
    """消息传递状态序列化器"""
    user_details = UserBasicSerializer(source='user', read_only=True)
    message_details = MessageSerializer(source='message', read_only=True)
    
    class Meta:
        model = MessageDeliveryStatus
        fields = (
            'id', 'message', 'user', 'is_delivered', 'delivered_at', 
            'is_read', 'read_at', 'user_details', 'message_details'
        )
        read_only_fields = ('delivered_at', 'read_at')
    
    def update(self, instance, validated_data):
        """更新已读状态"""
        from django.utils import timezone
        
        if 'is_delivered' in validated_data and validated_data['is_delivered'] and not instance.is_delivered:
            instance.is_delivered = True
            instance.delivered_at = timezone.now()
            
        if 'is_read' in validated_data and validated_data['is_read'] and not instance.is_read:
            instance.is_read = True
            instance.read_at = timezone.now()
            
        instance.save()
        return instance 