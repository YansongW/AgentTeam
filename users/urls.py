from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

from .views import (
    UserRegistrationView, EmailVerificationView, UserLoginView,
    UserProfileView, PasswordChangeView, UserManagementView, 
    LoginAttemptsView
)

# 设置应用命名空间
app_name = 'users'

# URL模式
urlpatterns = [
    # 注册与认证
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('verify-email/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 用户资料管理
    path('profile/<int:user_id>/', UserProfileView.as_view(), name='user_profile'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    
    # 管理员功能
    path('admin/users/', UserManagementView.as_view(), name='user_management'),
    path('admin/login-attempts/', LoginAttemptsView.as_view(), name='login_attempts'),
] 