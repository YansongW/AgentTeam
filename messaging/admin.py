from django.contrib import admin
from .models import Message, MessageDeliveryStatus

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """消息管理界面"""
    list_display = ('id', 'message_type', 'get_sender_name', 'get_recipient', 'created_at')
    list_filter = ('message_type', 'sender_type', 'created_at')
    search_fields = ('content', 'sender_user__username', 'sender_agent__name')
    readonly_fields = ('created_at',)
    
    def get_recipient(self, obj):
        """获取接收者名称"""
        if obj.group:
            return f"群组: {obj.group.name}"
        elif obj.recipient_user:
            return f"用户: {obj.recipient_user.username}"
        return "未指定"
    get_recipient.short_description = '接收者'
    
    def get_sender_name(self, obj):
        """获取发送者名称"""
        return obj.get_sender_name()
    get_sender_name.short_description = '发送者'


@admin.register(MessageDeliveryStatus)
class MessageDeliveryStatusAdmin(admin.ModelAdmin):
    """消息传递状态管理界面"""
    list_display = ('message', 'user', 'is_delivered', 'delivered_at', 'is_read', 'read_at')
    list_filter = ('is_delivered', 'is_read', 'delivered_at', 'read_at')
    search_fields = ('message__content', 'user__username')
    readonly_fields = ('delivered_at', 'read_at')
