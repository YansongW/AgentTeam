from django.contrib import admin
from .models import Group, GroupMember, GroupMessage, GroupRule

class GroupMemberInline(admin.TabularInline):
    """群组成员内联管理"""
    model = GroupMember
    extra = 1
    fields = ('user', 'agent', 'member_type', 'role', 'is_active')
    
class GroupMessageInline(admin.TabularInline):
    """群组消息内联管理"""
    model = GroupMessage
    extra = 0
    fields = ('sender_user', 'sender_agent', 'sender_type', 'message_type', 'content', 'timestamp')
    readonly_fields = ('timestamp',)
    max_num = 10
    can_delete = False
    
class GroupRuleInline(admin.TabularInline):
    """群组规则内联管理"""
    model = GroupRule
    extra = 0
    fields = ('name', 'rule_type', 'is_active', 'priority')
    

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """群组管理"""
    list_display = ('name', 'owner', 'is_public', 'created_at', 'updated_at', 'get_member_count')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [GroupMemberInline, GroupRuleInline, GroupMessageInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'description')
        }),
        ('状态', {
            'fields': ('is_public', 'created_at', 'updated_at')
        }),
        ('配置', {
            'fields': ('avatar', 'group_settings')
        }),
    )
    
    def get_member_count(self, obj):
        """获取成员数量"""
        return obj.get_member_count()
    get_member_count.short_description = '成员数量'
    

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    """群组成员管理"""
    list_display = ('get_display_name', 'group', 'member_type', 'role', 'is_active', 'joined_at')
    list_filter = ('group', 'member_type', 'role', 'is_active', 'joined_at')
    search_fields = ('group__name', 'user__username', 'agent__name')
    readonly_fields = ('joined_at',)
    fieldsets = (
        (None, {
            'fields': ('group', 'member_type')
        }),
        ('成员', {
            'fields': ('user', 'agent', 'role')
        }),
        ('状态', {
            'fields': ('is_active', 'joined_at', 'member_settings')
        }),
    )
    
    def get_display_name(self, obj):
        """获取显示名称"""
        if obj.member_type == GroupMember.MemberType.HUMAN and obj.user:
            return obj.user.username
        elif obj.member_type == GroupMember.MemberType.AGENT and obj.agent:
            return obj.agent.name
        return '未知成员'
    get_display_name.short_description = '成员名称'
    

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    """群组消息管理"""
    list_display = ('id', 'group', 'get_sender_name', 'message_type', 'timestamp')
    list_filter = ('group', 'sender_type', 'message_type', 'timestamp')
    search_fields = ('group__name', 'sender_user__username', 'sender_agent__name', 'content')
    readonly_fields = ('timestamp',)
    fieldsets = (
        (None, {
            'fields': ('group', 'sender_type', 'message_type')
        }),
        ('发送者', {
            'fields': ('sender_user', 'sender_agent')
        }),
        ('消息内容', {
            'fields': ('content', 'parent_message', 'timestamp')
        }),
        ('提及', {
            'fields': ('mentioned_users', 'mentioned_agents')
        }),
        ('其他', {
            'fields': ('metadata',)
        }),
    )
    
    def get_sender_name(self, obj):
        """获取发送者名称"""
        if obj.sender_type == GroupMessage.SenderType.HUMAN and obj.sender_user:
            return obj.sender_user.username
        elif obj.sender_type == GroupMessage.SenderType.AGENT and obj.sender_agent:
            return obj.sender_agent.name
        return '系统'
    get_sender_name.short_description = '发送者'
    

@admin.register(GroupRule)
class GroupRuleAdmin(admin.ModelAdmin):
    """群组规则管理"""
    list_display = ('name', 'group', 'rule_type', 'priority', 'is_active', 'created_at')
    list_filter = ('group', 'rule_type', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'group__name')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('target_agents',)
    fieldsets = (
        (None, {
            'fields': ('name', 'group', 'description')
        }),
        ('规则配置', {
            'fields': ('rule_type', 'target_agents', 'priority', 'is_active')
        }),
        ('条件和动作', {
            'fields': ('condition', 'action')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at')
        }),
    )
