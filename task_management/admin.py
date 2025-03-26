from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import (
    Task, TaskAssignment, TaskComment, 
    TaskTag, TaskTagAssignment, TaskDependency
)

class TaskAssignmentInline(admin.TabularInline):
    """任务分配内联管理"""
    model = TaskAssignment
    extra = 0
    fields = ('assigned_user', 'assigned_agent', 'is_primary', 'role', 'assigned_at', 'assigned_by')
    readonly_fields = ('assigned_at',)

class TaskTagAssignmentInline(admin.TabularInline):
    """任务标签分配内联管理"""
    model = TaskTagAssignment
    extra = 0
    fields = ('tag', 'assigned_at', 'assigned_by')
    readonly_fields = ('assigned_at',)

class TaskCommentInline(admin.TabularInline):
    """任务评论内联管理"""
    model = TaskComment
    extra = 0
    fields = ('content', 'created_by_user', 'created_by_agent', 'is_system_comment', 'created_at')
    readonly_fields = ('created_at',)

class TaskDependencyInline(admin.TabularInline):
    """前置任务依赖内联管理"""
    model = TaskDependency
    fk_name = 'dependent_task'
    extra = 0
    fields = ('prerequisite_task', 'created_at', 'created_by', 'notes')
    readonly_fields = ('created_at',)

class DependentTaskInline(admin.TabularInline):
    """依赖任务内联管理"""
    model = TaskDependency
    fk_name = 'prerequisite_task'
    extra = 0
    fields = ('dependent_task', 'created_at', 'created_by', 'notes')
    readonly_fields = ('created_at',)

class SubtaskInline(admin.TabularInline):
    """子任务内联管理"""
    model = Task
    fk_name = 'parent_task'
    extra = 0
    fields = ('title', 'status', 'priority', 'due_date', 'progress')
    readonly_fields = ('progress',)
    show_change_link = True

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """任务管理"""
    list_display = ('title', 'task_type', 'colored_status', 'priority', 'creator', 
                   'group', 'due_date', 'progress_bar', 'created_at')
    list_filter = ('status', 'priority', 'task_type', 'group', 'creator')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')
    
    fieldsets = (
        (_('基本信息'), {
            'fields': ('title', 'description', 'status', 'priority', 'task_type')
        }),
        (_('日期信息'), {
            'fields': ('created_at', 'updated_at', 'due_date', 'started_at', 'completed_at')
        }),
        (_('关联信息'), {
            'fields': ('creator', 'group', 'parent_task')
        }),
        (_('进度信息'), {
            'fields': ('progress', 'estimated_hours', 'actual_hours')
        }),
        (_('高级设置'), {
            'classes': ('collapse',),
            'fields': ('is_recurring', 'recurrence_pattern', 'metadata')
        }),
    )
    
    inlines = [
        TaskAssignmentInline,
        TaskTagAssignmentInline,
        TaskCommentInline,
        TaskDependencyInline,
        DependentTaskInline,
        SubtaskInline,
    ]
    
    def progress_bar(self, obj):
        """显示进度条"""
        return format_html(
            '<div style="width:100px;background-color:#ddd">'
            '<div style="width:{}px;background-color:{};height:10px"></div>'
            '</div> {}%',
            obj.progress if obj.progress <= 100 else 100,
            self._get_progress_color(obj.progress),
            obj.progress
        )
    progress_bar.short_description = _('进度')
    
    def colored_status(self, obj):
        """显示彩色状态"""
        colors = {
            'pending': '#6c757d',      # 灰色
            'in_progress': '#007bff',  # 蓝色
            'review': '#ffc107',       # 黄色
            'completed': '#28a745',    # 绿色
            'blocked': '#dc3545',      # 红色
            'canceled': '#6c757d',     # 灰色
        }
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    colored_status.short_description = _('状态')
    
    def _get_progress_color(self, progress):
        """根据进度返回颜色"""
        if progress < 30:
            return '#dc3545'  # 红色
        elif progress < 70:
            return '#ffc107'  # 黄色
        else:
            return '#28a745'  # 绿色

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    """任务分配管理"""
    list_display = ('task', 'assignee_display', 'is_primary', 'role', 'assigned_at', 'assigned_by')
    list_filter = ('is_primary', 'assigned_at', 'assigned_by')
    search_fields = ('task__title', 'assigned_user__username', 'assigned_agent__name', 'role')
    date_hierarchy = 'assigned_at'
    
    def assignee_display(self, obj):
        """显示被分配者"""
        if obj.assigned_user:
            return f"用户: {obj.assigned_user.username}"
        elif obj.assigned_agent:
            return f"代理: {obj.assigned_agent.name}"
        return "未分配"
    assignee_display.short_description = _('被分配者')

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """任务评论管理"""
    list_display = ('task', 'content_preview', 'creator_display', 
                   'is_system_comment', 'is_status_update', 'created_at')
    list_filter = ('is_system_comment', 'is_status_update', 'created_at')
    search_fields = ('task__title', 'content', 'created_by_user__username', 'created_by_agent__name')
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        """显示内容预览"""
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    content_preview.short_description = _('内容预览')
    
    def creator_display(self, obj):
        """显示创建者"""
        if obj.is_system_comment:
            return "系统"
        elif obj.created_by_user:
            return f"用户: {obj.created_by_user.username}"
        elif obj.created_by_agent:
            return f"代理: {obj.created_by_agent.name}"
        return "未知"
    creator_display.short_description = _('创建者')

@admin.register(TaskTag)
class TaskTagAdmin(admin.ModelAdmin):
    """任务标签管理"""
    list_display = ('name', 'color_display', 'description', 'task_count')
    search_fields = ('name', 'description')
    
    def color_display(self, obj):
        """显示颜色"""
        return format_html(
            '<span style="background-color:{};width:20px;height:20px;'
            'display:inline-block;border-radius:3px"></span> {}',
            obj.color, obj.color
        )
    color_display.short_description = _('颜色')
    
    def task_count(self, obj):
        """显示关联任务数量"""
        return obj.task_assignments.count()
    task_count.short_description = _('任务数')

@admin.register(TaskTagAssignment)
class TaskTagAssignmentAdmin(admin.ModelAdmin):
    """任务标签分配管理"""
    list_display = ('task', 'tag', 'assigned_at', 'assigned_by')
    list_filter = ('tag', 'assigned_at', 'assigned_by')
    search_fields = ('task__title', 'tag__name')
    date_hierarchy = 'assigned_at'

@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    """任务依赖管理"""
    list_display = ('dependent_task', 'prerequisite_task', 'created_at', 'created_by')
    list_filter = ('created_at', 'created_by')
    search_fields = ('dependent_task__title', 'prerequisite_task__title', 'notes')
    date_hierarchy = 'created_at'
