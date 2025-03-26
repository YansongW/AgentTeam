from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken

from agents.models import Agent
from groups.models import Group, GroupMember
from .models import (
    Task, TaskAssignment, TaskComment, 
    TaskTag, TaskTagAssignment, TaskDependency,
    TaskStatus, TaskPriority, TaskType
)

User = get_user_model()

class TaskModelTest(TestCase):
    """任务模型测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.user
        )
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            creator=self.user,
            group=self.group
        )
    
    def test_task_creation(self):
        """测试任务创建"""
        self.assertEqual(self.task.title, 'Test Task')
        self.assertEqual(self.task.status, TaskStatus.PENDING)
        self.assertEqual(self.task.priority, TaskPriority.MEDIUM)
        self.assertEqual(self.task.creator, self.user)
        self.assertEqual(self.task.group, self.group)
    
    def test_task_status_update(self):
        """测试任务状态更新"""
        self.task.status = TaskStatus.IN_PROGRESS
        self.task.save()
        self.assertIsNotNone(self.task.started_at)
        
        self.task.status = TaskStatus.COMPLETED
        self.task.save()
        self.assertIsNotNone(self.task.completed_at)
    
    def test_task_progress(self):
        """测试任务进度更新"""
        self.task.progress = 100
        self.task.save()
        self.assertEqual(self.task.status, TaskStatus.COMPLETED)

class TaskAssignmentTest(TestCase):
    """任务分配测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.agent = Agent.objects.create(
            name='Test Agent',
            owner=self.user
        )
        self.task = Task.objects.create(
            title='Test Task',
            creator=self.user
        )
        self.assignment = TaskAssignment.objects.create(
            task=self.task,
            assigned_user=self.user,
            assigned_by=self.user
        )
    
    def test_assignment_creation(self):
        """测试分配创建"""
        self.assertEqual(self.assignment.task, self.task)
        self.assertEqual(self.assignment.assigned_user, self.user)
        self.assertEqual(self.assignment.assigned_by, self.user)
    
    def test_agent_assignment(self):
        """测试代理分配"""
        agent_assignment = TaskAssignment.objects.create(
            task=self.task,
            assigned_agent=self.agent,
            assigned_by=self.user
        )
        self.assertEqual(agent_assignment.assigned_agent, self.agent)
        self.assertIsNone(agent_assignment.assigned_user)

class TaskCommentTest(TestCase):
    """任务评论测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.agent = Agent.objects.create(
            name='Test Agent',
            owner=self.user
        )
        self.task = Task.objects.create(
            title='Test Task',
            creator=self.user
        )
        self.comment = TaskComment.objects.create(
            task=self.task,
            content='Test Comment',
            created_by_user=self.user
        )
    
    def test_comment_creation(self):
        """测试评论创建"""
        self.assertEqual(self.comment.task, self.task)
        self.assertEqual(self.comment.content, 'Test Comment')
        self.assertEqual(self.comment.created_by_user, self.user)
    
    def test_agent_comment(self):
        """测试代理评论"""
        agent_comment = TaskComment.objects.create(
            task=self.task,
            content='Agent Comment',
            created_by_agent=self.agent
        )
        self.assertEqual(agent_comment.created_by_agent, self.agent)
        self.assertIsNone(agent_comment.created_by_user)

class TaskAPIViewTest(APITestCase):
    """任务API视图测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 使用JWT认证
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # 创建测试数据
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.user
        )
        
        # 将用户添加为群组成员
        GroupMember.objects.create(
            group=self.group,
            user=self.user,
            member_type=GroupMember.MemberType.HUMAN,
            role=GroupMember.Role.ADMIN
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            creator=self.user,
            group=self.group
        )
    
    def test_task_list(self):
        """测试任务列表API"""
        url = reverse('task_api:task-list')
        response = self.client.get(url)
        print(f"Response status: {response.status_code}")
        if response.status_code != status.HTTP_200_OK:
            print(f"Response content: {response.content}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_task_detail(self):
        """测试任务详情API"""
        url = reverse('task_api:task-detail', kwargs={'pk': self.task.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Task')
    
    def test_task_create(self):
        """测试任务创建API"""
        url = reverse('task_api:task-list')
        data = {
            'title': 'New Task',
            'description': 'New Description',
            'group': self.group.id
        }
        response = self.client.post(url, data)
        print(f"Response status: {response.status_code}")
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response content: {response.content}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
    
    def test_task_update(self):
        """测试任务更新API"""
        url = reverse('task_api:task-detail', kwargs={'pk': self.task.id})
        data = {
            'title': 'Updated Task',
            'status': TaskStatus.IN_PROGRESS
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated Task')
        self.assertEqual(self.task.status, TaskStatus.IN_PROGRESS)
    
    def test_task_delete(self):
        """测试任务删除API"""
        url = reverse('task_api:task-detail', kwargs={'pk': self.task.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 0)
