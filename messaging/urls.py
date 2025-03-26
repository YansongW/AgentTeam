from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'statuses', views.MessageDeliveryStatusViewSet, basename='status')

# 设置应用命名空间
app_name = 'messaging'

# URL模式
urlpatterns = [
    path('', include((router.urls, app_name))),
    path('websocket-test/', views.websocket_test, name='websocket-test'),
] 