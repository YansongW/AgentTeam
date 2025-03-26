from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "用户管理"
    
    def ready(self):
        """
        应用初始化时执行的代码
        """
        # 导入信号处理器
        try:
            from . import signals  # noqa
            
            # 初始化错误处理
            from chatbot_platform.error_utils import ErrorUtils
            from chatbot_platform.error_codes import UserErrorCodes
            
            # 注册错误处理器
            ErrorUtils.register_app_error_codes('users', UserErrorCodes)
        except ImportError:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("无法导入错误处理工具，错误处理功能可能不可用")
