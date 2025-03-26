from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Agent, AgentSkill, AgentSkillAssignment, AgentInteraction

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """AI代理管理界面"""
    list_display = ('name', 'role', 'owner', 'status', 'is_public', 'created_at')
    list_filter = ('role', 'status', 'is_public', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'role', 'description', 'owner')}),
        (_('状态'), {'fields': ('status', 'is_public')}),
        (_('配置'), {
            'fields': ('skills', 'system_prompt', 'model_config', 'api_access'),
            'classes': ('collapse',)
        }),
        (_('时间信息'), {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(AgentSkill)
class AgentSkillAdmin(admin.ModelAdmin):
    """代理技能管理界面"""
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AgentSkillAssignment)
class AgentSkillAssignmentAdmin(admin.ModelAdmin):
    """代理技能分配管理界面"""
    list_display = ('agent', 'skill', 'enabled', 'created_at')
    list_filter = ('enabled', 'created_at')
    search_fields = ('agent__name', 'skill__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AgentInteraction)
class AgentInteractionAdmin(admin.ModelAdmin):
    """代理交互记录管理界面"""
    list_display = ('interaction_type', 'initiator', 'receiver', 'timestamp')
    list_filter = ('interaction_type', 'timestamp')
    search_fields = ('initiator__name', 'receiver__name')
    readonly_fields = ('timestamp',)
