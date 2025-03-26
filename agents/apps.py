from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AgentsConfig(AppConfig):
    """代理应用配置类"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agents'
    verbose_name = _("Agent代理")
    
    def ready(self):
        """
        应用就绪时调用
        初始化各种服务和信号处理
        """
        # 导入信号处理器
        import agents.signals
        
        # 初始化异步消息处理器
        from agents.async_processor import init_async_processor
        
        # 注册处理函数
        from agents.handlers import register_handlers
        
        # 在非测试模式下启动异步处理器并注册处理函数
        import sys
        if 'test' not in sys.argv and 'pytest' not in sys.argv:
            init_async_processor()
            register_handlers()
