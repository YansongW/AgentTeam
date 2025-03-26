from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GroupViewSet,
    GroupMemberViewSet,
    GroupMessageViewSet,
    GroupRuleViewSet,
    group_management,
    group_chat_view
)

# API路由
router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'group-members', GroupMemberViewSet, basename='group-member')
router.register(r'group-messages', GroupMessageViewSet, basename='group-message')
router.register(r'group-rules', GroupRuleViewSet, basename='group-rule')

api_urlpatterns = [
    path('', include(router.urls)),
]

# 页面路由
page_urlpatterns = [
    path('management/', group_management, name='group_management'),
    path('chat/<str:group_id>/', group_chat_view, name='group_chat'),
]

urlpatterns = api_urlpatterns + page_urlpatterns 