from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TaskManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "task_management"
    verbose_name = _('任务管理')

    def ready(self):
        """应用就绪时的初始化操作"""
        # 导入信号处理器
        try:
            import task_management.signals  # noqa
        except ImportError:
            pass
