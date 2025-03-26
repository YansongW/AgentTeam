import pytest
import asyncio
import threading
import time
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from agents.async_processor import AsyncMessageProcessor
from agents.models import Agent, AgentListeningRule

User = get_user_model()

class AsyncProcessorTestCase(TestCase):
    """测试异步消息处理器"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # 创建测试代理
        self.agent = Agent.objects.create(
            name='测试代理',
            role=Agent.Role.ASSISTANT,
            owner=self.user,
            description='用于测试的代理',
            status=Agent.Status.ONLINE,
            is_public=True
        )
        
        # 创建测试规则
        self.rule = AgentListeningRule.objects.create(
            name='测试规则',
            description='用于测试的规则',
            agent=self.agent,
            is_active=True,
            priority=10,
            trigger_type=AgentListeningRule.TriggerType.KEYWORD,
            trigger_condition={
                'keywords': ['测试']
            },
            response_type=AgentListeningRule.ResponseType.AUTO_REPLY,
            response_content={
                'reply_template': '这是一个测试回复'
            },
            listen_in_groups=True,
            listen_in_direct=True
        )
        
        # 创建处理器实例
        self.processor = AsyncMessageProcessor()
    
    def tearDown(self):
        """清理测试环境"""
        if self.processor.running:
            self.processor.stop()
    
    def test_processor_lifecycle(self):
        """测试处理器生命周期"""
        # 初始状态应该是未运行
        self.assertFalse(self.processor.running)
        self.assertIsNone(self.processor.worker_thread)
        
        # 启动处理器
        self.processor.start()
        self.assertTrue(self.processor.running)
        self.assertIsNotNone(self.processor.worker_thread)
        
        # 停止处理器
        self.processor.stop()
        self.assertFalse(self.processor.running)
    
    @patch('agents.services.RuleEngine.process_message')
    def test_add_message(self, mock_process_message):
        """测试添加消息到队列"""
        # 设置模拟返回值
        mock_response = [{'content': '测试响应', 'agent_id': str(self.agent.id)}]
        mock_process_message.return_value = mock_response
        
        # 创建回调函数
        callback_called = threading.Event()
        callback_result = []
        
        def callback(responses):
            callback_result.extend(responses)
            callback_called.set()
        
        # 添加消息
        message = {'content': '这是一条测试消息', 'group_id': 'group1'}
        context = {'group_id': 'group1'}
        
        self.processor.start()
        self.processor.add_message(message, context, callback)
        
        # 等待回调被调用
        callback_called.wait(timeout=2)
        
        # 验证回调被调用且结果正确
        self.assertTrue(callback_called.is_set())
        self.assertEqual(callback_result, mock_response)
        
        # 验证规则引擎的process_message被调用
        mock_process_message.assert_called_once_with(message, context)
    
    @patch('channels.layers.get_channel_layer')
    def test_register_handler(self, mock_get_channel_layer):
        """测试注册处理函数"""
        # 创建模拟异步处理函数
        async def test_handler(response, context):
            return "处理结果"
        
        # 注册处理函数
        self.processor.register_handler('test_type', test_handler)
        
        # 验证处理函数已注册
        self.assertIn('test_type', self.processor.handlers)
        self.assertEqual(self.processor.handlers['test_type'], test_handler)
    
    @patch('agents.services.RuleEngine.process_message')
    @patch('channels.layers.get_channel_layer')
    def test_send_response(self, mock_get_channel_layer, mock_process_message):
        """测试发送响应"""
        # 设置模拟返回值
        mock_response = [{
            'type': 'auto_reply',
            'content': '测试响应',
            'agent_id': str(self.agent.id),
            'agent_name': '测试代理'
        }]
        mock_process_message.return_value = mock_response
        
        # 模拟channel_layer
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        mock_channel_layer.group_send = AsyncMock()
        
        # 设置处理器的channel_layer
        self.processor.channel_layer = mock_channel_layer
        
        # 注册处理函数
        mock_handler = AsyncMock()
        self.processor.register_handler('auto_reply', mock_handler)
        
        # 创建回调函数
        callback_called = threading.Event()
        
        def callback(responses):
            callback_called.set()
        
        # 添加消息
        message = {'content': '这是一条测试消息'}
        context = {'group_id': 'group1'}
        
        self.processor.start()
        self.processor.add_message(message, context, callback)
        
        # 等待回调被调用
        callback_called.wait(timeout=2)
        
        # 等待异步处理
        time.sleep(0.5)
        
        # 验证group_send被调用
        args, kwargs = mock_channel_layer.group_send.await_args
        self.assertEqual(args[0], 'group_group1')
        self.assertEqual(args[1]['type'], 'agent.message')
        
        # 验证处理函数被调用
        mock_handler.assert_awaited_once()


class AsyncMock(MagicMock):
    """用于模拟异步函数的Mock类"""
    
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs) 