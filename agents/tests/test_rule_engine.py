import pytest
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from agents.models import Agent, AgentListeningRule
from agents.services import RuleEngine

User = get_user_model()

class RuleEngineTestCase(TestCase):
    """测试代理监听规则引擎"""
    
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
        
        # 创建关键词规则
        self.keyword_rule = AgentListeningRule.objects.create(
            name='关键词测试规则',
            description='测试关键词匹配',
            agent=self.agent,
            is_active=True,
            priority=10,
            trigger_type=AgentListeningRule.TriggerType.KEYWORD,
            trigger_condition={
                'keywords': ['测试', '帮助', '问题']
            },
            response_type=AgentListeningRule.ResponseType.AUTO_REPLY,
            response_content={
                'reply_template': '我看到你提到了关键词，有什么可以帮助你的吗？'
            },
            listen_in_groups=True,
            listen_in_direct=True
        )
        
        # 创建正则表达式规则
        self.regex_rule = AgentListeningRule.objects.create(
            name='正则测试规则',
            description='测试正则表达式匹配',
            agent=self.agent,
            is_active=True,
            priority=5,
            trigger_type=AgentListeningRule.TriggerType.REGEX,
            trigger_condition={
                'pattern': r'如何(\w+)'
            },
            response_type=AgentListeningRule.ResponseType.AUTO_REPLY,
            response_content={
                'reply_template': '你想知道如何操作是吗？我可以帮助你。'
            },
            listen_in_groups=True,
            listen_in_direct=True
        )
        
        # 创建提及规则
        self.mention_rule = AgentListeningRule.objects.create(
            name='提及测试规则',
            description='测试提及匹配',
            agent=self.agent,
            is_active=True,
            priority=1,
            trigger_type=AgentListeningRule.TriggerType.MENTION,
            trigger_condition={},
            response_type=AgentListeningRule.ResponseType.AUTO_REPLY,
            response_content={
                'reply_template': '你好，我是{agent_name}，我看到你提到了我。'
            },
            listen_in_groups=True,
            listen_in_direct=True
        )
        
        # 创建情感分析规则
        self.sentiment_rule = AgentListeningRule.objects.create(
            name='情感测试规则',
            description='测试情感分析匹配',
            agent=self.agent,
            is_active=True,
            priority=15,
            trigger_type=AgentListeningRule.TriggerType.SENTIMENT,
            trigger_condition={
                'target_sentiment': 'negative',
                'threshold': 0.3
            },
            response_type=AgentListeningRule.ResponseType.AUTO_REPLY,
            response_content={
                'reply_template': '我注意到你似乎有些不开心，有什么可以帮助你的吗？'
            },
            listen_in_groups=True,
            listen_in_direct=True
        )
    
    def test_keyword_matching(self):
        """测试关键词匹配"""
        message = {
            'content': '我有一个测试问题需要帮助。',
            'sender': 'user1',
            'group_id': 'group1'
        }
        
        responses = RuleEngine.process_message(message)
        
        # 应该匹配关键词规则
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]['rule_metadata']['rule_id'], str(self.keyword_rule.id))
        self.assertEqual(responses[0]['content'], '我看到你提到了关键词，有什么可以帮助你的吗？')
    
    def test_regex_matching(self):
        """测试正则表达式匹配"""
        message = {
            'content': '如何使用这个功能？',
            'sender': 'user1',
            'group_id': 'group1'
        }
        
        responses = RuleEngine.process_message(message)
        
        # 应该匹配正则规则，且由于优先级高于关键词规则，所以只返回正则规则的响应
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]['rule_metadata']['rule_id'], str(self.regex_rule.id))
        self.assertEqual(responses[0]['content'], '你想知道如何操作是吗？我可以帮助你。')
    
    def test_mention_matching(self):
        """测试提及匹配"""
        message = {
            'content': f'@{self.agent.name} 你能帮我吗？',
            'sender': 'user1',
            'group_id': 'group1',
            'mentions': [str(self.agent.id)]
        }
        
        responses = RuleEngine.process_message(message)
        
        # 应该匹配提及规则，且由于优先级最高，所以只返回提及规则的响应
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]['rule_metadata']['rule_id'], str(self.mention_rule.id))
        self.assertEqual(responses[0]['content'], f'你好，我是{self.agent.name}，我看到你提到了我。')
    
    def test_sentiment_matching(self):
        """测试情感分析匹配"""
        message = {
            'content': '这个功能真的很差劲，我非常失望，根本无法使用！',
            'sender': 'user1',
            'group_id': 'group1'
        }
        
        responses = RuleEngine.process_message(message)
        
        # 由于消息情感很负面，应该匹配情感规则
        self.assertTrue(any(r['rule_metadata']['rule_id'] == str(self.sentiment_rule.id) for r in responses))
    
    def test_no_matching(self):
        """测试无匹配情况"""
        message = {
            'content': '今天天气真好。',
            'sender': 'user1',
            'group_id': 'group1'
        }
        
        responses = RuleEngine.process_message(message)
        
        # 不应该匹配任何规则
        self.assertEqual(len(responses), 0)
    
    def test_rule_cooldown(self):
        """测试规则冷却时间"""
        # 设置规则冷却时间
        self.keyword_rule.cooldown_period = 60  # 60秒冷却时间
        self.keyword_rule.save()
        
        # 第一次触发
        message = {
            'content': '我有一个测试问题。',
            'sender': 'user1',
            'group_id': 'group1'
        }
        
        responses = RuleEngine.process_message(message)
        
        # 应该匹配关键词规则
        self.assertEqual(len(responses), 1)
        
        # 再次触发，应该被冷却时间阻止
        responses = RuleEngine.process_message(message)
        
        # 不应该有响应
        self.assertEqual(len(responses), 0)
        
        # 重置冷却时间
        self.keyword_rule.last_triggered = timezone.now() - timezone.timedelta(seconds=61)
        self.keyword_rule.save()
        
        # 再次触发，冷却时间已过
        responses = RuleEngine.process_message(message)
        
        # 应该再次匹配
        self.assertEqual(len(responses), 1)
    
    def test_normalize_message(self):
        """测试消息格式标准化"""
        # 字符串消息
        message = "这是一条测试消息"
        
        normalized = RuleEngine._normalize_message(message, {})
        
        self.assertEqual(normalized['content'], message)
        self.assertEqual(normalized['content_type'], 'text')
        self.assertTrue('timestamp' in normalized)
        
        # 已经是字典的消息
        message_dict = {
            'content': '这是一条测试消息',
            'sender': 'user1'
        }
        
        normalized = RuleEngine._normalize_message(message_dict, {'group_id': 'group1'})
        
        self.assertEqual(normalized['content'], message_dict['content'])
        self.assertEqual(normalized['sender'], message_dict['sender'])
        self.assertEqual(normalized['group_id'], 'group1')
        self.assertTrue('content_type' in normalized)
        self.assertTrue('timestamp' in normalized)
    
    def test_context_aware_matching(self):
        """测试上下文感知匹配"""
        # 创建上下文规则
        context_rule = AgentListeningRule.objects.create(
            name='上下文测试规则',
            description='测试上下文感知匹配',
            agent=self.agent,
            is_active=True,
            priority=8,
            trigger_type=AgentListeningRule.TriggerType.CONTEXT_AWARE,
            trigger_condition={
                'context_rules': [
                    {'type': 'keyword', 'value': '数据库', 'weight': 1.0},
                    {'type': 'keyword', 'value': '错误', 'weight': 1.0}
                ],
                'context_size': 3,
                'time_window': 300,
                'match_threshold': 0.7
            },
            response_type=AgentListeningRule.ResponseType.AUTO_REPLY,
            response_content={
                'reply_template': '看起来你遇到了数据库问题，需要查看错误日志吗？'
            },
            listen_in_groups=True,
            listen_in_direct=True
        )
        
        # 创建上下文历史
        now = timezone.now()
        context_messages = [
            {
                'content': '我在尝试连接数据库。',
                'sender': 'user1',
                'timestamp': (now - timezone.timedelta(seconds=60)).isoformat()
            },
            {
                'content': '但是遇到了一些问题。',
                'sender': 'user1',
                'timestamp': (now - timezone.timedelta(seconds=30)).isoformat()
            }
        ]
        
        # 当前消息
        message = {
            'content': '我遇到了一个错误。',
            'sender': 'user1',
            'group_id': 'group1',
            'context_messages': context_messages,
            'timestamp': now.isoformat()
        }
        
        responses = RuleEngine.process_message(message)
        
        # 应该匹配上下文规则
        self.assertTrue(any(r['rule_metadata']['rule_id'] == str(context_rule.id) for r in responses)) 