"""
URL configuration for chatbot_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView, TemplateView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from agents.urls import api_urlpatterns as agents_api_urls
from agents.urls import page_urlpatterns as agents_page_urls
from agents.urls import urlpatterns as agents_urlpatterns
from groups.urls import api_urlpatterns as groups_api_urls
from groups.urls import page_urlpatterns as groups_page_urls

# 配置Swagger文档
schema_view = get_schema_view(
    openapi.Info(
        title="Multi-Agent协作平台 API",
        default_version='v1',
        description="Multi-Agent协作平台的接口文档",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # 根路径重定向到群组管理页面
    path('', RedirectView.as_view(url='/groups/groups/'), name='home'),
    
    # API路由
    path("api/users/", include("users.urls")),
    path("api/agents/", include(agents_api_urls)),
    path("api/groups/", include("groups.urls")),
    path("api/messaging/", include("messaging.urls")),
    path("api/tasks/", include("task_management.urls", namespace="task_api")),
    
    # 页面路由
    path("agent-rules/", include((agents_page_urls, "agents"), namespace="agent_rules")),
    path("agents/", include((agents_urlpatterns, "agents"), namespace="agents")),
    
    # WebSocket测试页面
    path("websocket-test/", include("messaging.urls_websocket")),
    
    # Swagger文档路由
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # 群组API
    path('api/', include(groups_api_urls)),
    
    # 群组页面
    path('groups/', include(groups_page_urls)),
    
    # 添加任务管理页面路由
    path('tasks/', include('task_management.urls', namespace="task_management")),
]

# 开发环境中添加媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
