from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Agent, AgentSkill, AgentInteraction

User = get_user_model()


class AgentModelTests(TestCase):
    """Agent模型测试类"""
    
    def setUp(self):
        """创建测试用户"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
    def test_agent_creation(self):
        """测试创建Agent模型实例"""
        agent = Agent.objects.create(
            name='测试代理',
            role=Agent.Role.BACKEND_DEV,
            description='这是一个测试代理',
            owner=self.user,
            status=Agent.Status.ONLINE,
            is_public=False,
            system_prompt='你是一名后端开发者'
        )
        
        self.assertEqual(agent.name, '测试代理')
        self.assertEqual(agent.role, Agent.Role.BACKEND_DEV)
        self.assertEqual(agent.owner, self.user)
        self.assertEqual(agent.status, Agent.Status.ONLINE)
        self.assertFalse(agent.is_public)
        self.assertTrue(agent.is_available())
        
    def test_set_status_method(self):
        """测试修改代理状态的方法"""
        agent = Agent.objects.create(
            name='状态测试代理',
            role=Agent.Role.ASSISTANT,
            owner=self.user,
            status=Agent.Status.OFFLINE
        )
        
        # 测试有效状态更新
        self.assertTrue(agent.set_status(Agent.Status.ONLINE))
        agent.refresh_from_db()
        self.assertEqual(agent.status, Agent.Status.ONLINE)
        
        # 测试无效状态更新
        self.assertFalse(agent.set_status('invalid_status'))
        agent.refresh_from_db()
        self.assertEqual(agent.status, Agent.Status.ONLINE)


# 使用模拟AI响应进行测试
@override_settings(USE_MOCK_AI_IN_TEST=True)
class AgentAPITests(APITestCase):
    """Agent API测试类"""
    
    def setUp(self):
        """创建测试用户和测试代理"""
        # 创建普通用户
        self.user = User.objects.create_user(
            username='apiuser',
            email='apiuser@example.com',
            password='testpassword'
        )
        
        # 创建管理员用户
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword',
            is_staff=True
        )
        
        # 创建普通用户的代理
        self.user_agent = Agent.objects.create(
            name='用户的代理',
            role=Agent.Role.FRONTEND_DEV,
            description='这是普通用户的代理',
            owner=self.user,
            status=Agent.Status.ONLINE,
            is_public=False,
            system_prompt='你是前端开发人员'
        )
        
        # 创建公开代理
        self.public_agent = Agent.objects.create(
            name='公开代理',
            role=Agent.Role.ASSISTANT,
            description='这是一个公开的代理',
            owner=self.admin_user,
            status=Agent.Status.ONLINE,
            is_public=True,
            system_prompt='你是一个助手'
        )
        
        # API路径
        self.agent_list_url = reverse('agents:agent-list')
        self.my_agents_url = reverse('agents:agent-my-agents')
        self.public_agents_url = reverse('agents:agent-public-agents')
        
    def test_list_agents_authenticated(self):
        """测试已认证用户获取代理列表"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 获取代理列表
        response = self.client.get(self.agent_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 普通用户应该只能看到自己的代理和公开代理
        self.assertEqual(len(response.data), 2)
        agent_ids = [agent['id'] for agent in response.data]
        self.assertIn(self.user_agent.id, agent_ids)
        self.assertIn(self.public_agent.id, agent_ids)
        
    def test_create_agent(self):
        """测试创建新代理"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 创建新代理的数据
        new_agent_data = {
            'name': '新测试代理',
            'role': Agent.Role.PRODUCT_MANAGER,
            'description': '这是一个新创建的测试代理',
            'status': Agent.Status.OFFLINE,
            'is_public': True,
            'system_prompt': '你是一名产品经理'
        }
        
        # 发送创建请求
        response = self.client.post(self.agent_list_url, new_agent_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 检查新代理是否创建成功
        self.assertEqual(response.data['name'], new_agent_data['name'])
        self.assertEqual(response.data['role'], new_agent_data['role'])
        
        # 验证数据库中是否存在该代理且所有者为当前用户
        agent = Agent.objects.get(name=new_agent_data['name'])
        self.assertEqual(agent.owner, self.user)
        self.assertEqual(agent.role, new_agent_data['role'])
        
    def test_my_agents_endpoint(self):
        """测试获取当前用户的代理列表"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 获取我的代理列表
        response = self.client.get(self.my_agents_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 应该只返回用户自己的代理
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.user_agent.id)
        
    def test_public_agents_endpoint(self):
        """测试获取公开代理列表"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 获取公开代理列表
        response = self.client.get(self.public_agents_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 应该只返回公开代理
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.public_agent.id)
        
    def test_update_agent_owner(self):
        """测试代理所有者可以更新代理"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 更新自己的代理
        agent_detail_url = reverse('agents:agent-detail', args=[self.user_agent.id])
        update_data = {
            'name': '更新后的代理名称',
            'status': Agent.Status.BUSY,
            'system_prompt': '更新后的系统提示'
        }
        
        response = self.client.patch(agent_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], update_data['name'])
        self.assertEqual(response.data['status'], update_data['status'])
        
        # 验证数据库中是否更新
        self.user_agent.refresh_from_db()
        self.assertEqual(self.user_agent.name, update_data['name'])
        self.assertEqual(self.user_agent.status, update_data['status'])
        
    def test_cannot_update_others_agent(self):
        """测试用户不能更新他人的代理"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 尝试更新管理员的公开代理
        agent_detail_url = reverse('agents:agent-detail', args=[self.public_agent.id])
        update_data = {
            'name': '尝试更新他人的代理',
            'is_public': False
        }
        
        response = self.client.patch(agent_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_chat_with_agent(self):
        """测试与代理聊天功能"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 构建聊天请求URL
        chat_url = reverse('agents:agent-chat', args=[self.user_agent.id])
        
        # 发送聊天消息
        chat_data = {
            'message': '你好，我需要一个前端页面设计',
            'context': {'previous_messages': []}
        }
        
        response = self.client.post(chat_url, chat_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证响应包含必要的字段
        self.assertIn('agent_id', response.data)
        self.assertIn('agent_name', response.data)
        self.assertIn('message', response.data)
        self.assertIn('response', response.data)
        self.assertIn('interaction_id', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('has_history', response.data)
        self.assertIn('history_count', response.data)
        
        # 验证消息内容
        self.assertEqual(response.data['message'], chat_data['message'])
        self.assertEqual(response.data['agent_id'], self.user_agent.id)
        self.assertEqual(response.data['agent_name'], self.user_agent.name)
        
        # 验证交互记录是否创建
        interaction_id = response.data['interaction_id']
        self.assertTrue(AgentInteraction.objects.filter(id=interaction_id).exists())
        
    def test_chat_with_unavailable_agent(self):
        """测试与不可用代理聊天"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 将代理设为不可用状态
        self.user_agent.status = Agent.Status.DISABLED
        self.user_agent.save()
        
        # 构建聊天请求URL
        chat_url = reverse('agents:agent-chat', args=[self.user_agent.id])
        
        # 发送聊天消息
        chat_data = {
            'message': '你好，我需要帮助'
        }
        
        response = self.client.post(chat_url, chat_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
    def test_chat_without_message(self):
        """测试不提供消息内容的情况"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 构建聊天请求URL
        chat_url = reverse('agents:agent-chat', args=[self.user_agent.id])
        
        # 发送空消息
        chat_data = {
            'context': {'previous_messages': []}
        }
        
        response = self.client.post(chat_url, chat_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_get_agent_history(self):
        """测试获取代理对话历史"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 创建一些历史对话记录
        agent = self.user_agent
        for i in range(3):
            AgentInteraction.objects.create(
                initiator=agent,
                receiver=agent,
                content={
                    'user_message': f'测试消息 {i}',
                    'agent_response': f'测试回复 {i}'
                },
                interaction_type=AgentInteraction.InteractionType.MESSAGE
            )
            
        # 请求对话历史
        history_url = reverse('agents:agent-history', args=[agent.id])
        response = self.client.get(history_url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['agent_id'], agent.id)
        self.assertEqual(response.data['agent_name'], agent.name)
        
        # 应该有3条历史记录
        self.assertEqual(response.data['count'], 3)
        
    def test_get_my_conversations(self):
        """测试获取所有代理对话历史"""
        # 普通用户登录
        self.client.force_authenticate(user=self.user)
        
        # 创建多个代理
        agent2 = Agent.objects.create(
            name='第二个代理',
            role=Agent.Role.DATA_ANALYST,
            owner=self.user,
            status=Agent.Status.ONLINE
        )
        
        # 创建一些历史对话记录
        for agent in [self.user_agent, agent2]:
            for i in range(2):
                AgentInteraction.objects.create(
                    initiator=agent,
                    receiver=agent,
                    content={
                        'user_message': f'对{agent.name}的消息 {i}',
                        'agent_response': f'来自{agent.name}的回复 {i}'
                    },
                    interaction_type=AgentInteraction.InteractionType.MESSAGE
                )
                
        # 请求所有对话历史
        conversations_url = reverse('agents:agent-my-conversations')
        response = self.client.get(conversations_url)
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 应该有2个代理的对话
        self.assertEqual(response.data['agent_count'], 2)
        
        # 验证每个代理都有2条消息
        for agent_id, data in response.data['conversations'].items():
            self.assertEqual(len(data['messages']), 2)
