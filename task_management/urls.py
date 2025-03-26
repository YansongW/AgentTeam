from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TaskViewSet, TaskCommentViewSet, TaskTagViewSet,
    TaskListView  # 添加模板视图
)

app_name = 'task_management'

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'task-comments', TaskCommentViewSet, basename='task-comment')
router.register(r'task-tags', TaskTagViewSet, basename='task-tag')

urlpatterns = [
    path('', include(router.urls)),
    # 添加HTML模板页面路由
    path('management/', TaskListView.as_view(), name='task_list'),
] 