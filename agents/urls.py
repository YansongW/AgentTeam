from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AgentViewSet, AgentSkillViewSet, AgentInteractionViewSet, AgentListeningRuleViewSet, rule_management_view, agent_management_view, agent_demo

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'skills', AgentSkillViewSet, basename='skill')
router.register(r'interactions', AgentInteractionViewSet, basename='interaction')
router.register(r'rules', AgentListeningRuleViewSet, basename='rule')

# 设置应用命名空间
app_name = 'agents'

# API路由
api_urlpatterns = [
    path('', include(router.urls)),
]

# 页面路由
page_urlpatterns = [
    path('management/', rule_management_view, name='rule_management'),
    path('', agent_management_view, name='agent_management'),
]

# 所有URL模式（API和页面）
urlpatterns = [
    path('demo/', agent_demo, name='agent_demo'),
    path('management/', agent_management_view, name='agent_management'),
] 