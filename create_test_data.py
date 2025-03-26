#!/usr/bin/env python
"""
创建测试数据脚本
用于生成测试WebSocket和规则引擎所需的测试数据
"""
import os
import django
import sys

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_platform.settings')
django.setup()

from django.contrib.auth import get_user_model
from agents.models import Agent, AgentListeningRule
from groups.models import Group, GroupMember

User = get_user_model()

def create_test_data():
    """创建测试数据"""
    print("开始创建测试数据...")
    
    # 1. 创建测试用户
    test_user, created = User.objects.get_or_create(
        username="testuser",
        defaults={
            "email": "test@example.com",
            "is_active": True
        }
    )
    if created:
        test_user.set_password("testpassword")
        test_user.save()
        print(f"创建测试用户: {test_user.username}")
    else:
        print(f"测试用户已存在: {test_user.username}")
    
    # 2. 创建测试代理
    test_agent, created = Agent.objects.get_or_create(
        name="测试助手",
        defaults={
            "role": "assistant",
            "description": "用于测试的AI助手",
            "owner": test_user,
            "status": "active",
            "is_public": True,
            "system_prompt": "你是一个测试助手，用于测试WebSocket和规则引擎功能。"
        }
    )
    if created:
        print(f"创建测试代理: {test_agent.name}")
    else:
        print(f"测试代理已存在: {test_agent.name}")
    
    # 3. 创建测试群组
    test_group, created = Group.objects.get_or_create(
        name="测试群组",
        defaults={
            "description": "用于测试WebSocket和规则引擎的群组",
            "owner": test_user,
            "is_public": True
        }
    )
    if created:
        print(f"创建测试群组: {test_group.name}")
    else:
        print(f"测试群组已存在: {test_group.name}")
    
    # 4. 将用户添加为群组成员
    member, created = GroupMember.objects.get_or_create(
        group=test_group,
        user=test_user,
        defaults={
            "role": "admin",
            "is_active": True
        }
    )
    if created:
        print(f"将用户 {test_user.username} 添加到群组 {test_group.name}")
    else:
        print(f"用户 {test_user.username} 已是群组 {test_group.name} 的成员")
    
    # 5. 将代理添加为群组成员
    agent_member, created = GroupMember.objects.get_or_create(
        group=test_group,
        agent=test_agent,
        defaults={
            "role": "member",
            "is_active": True
        }
    )
    if created:
        print(f"将代理 {test_agent.name} 添加到群组 {test_group.name}")
    else:
        print(f"代理 {test_agent.name} 已是群组 {test_group.name} 的成员")
    
    # 6. 创建测试监听规则
    rule, created = AgentListeningRule.objects.get_or_create(
        name="问候规则",
        agent=test_agent,
        defaults={
            "description": "当有人说'你好'时自动回复",
            "is_active": True,
            "priority": 1,
            "trigger_type": "keyword",
            "trigger_condition": {"keywords": ["你好", "hello", "hi"]},
            "listen_in_groups": True,
            "listen_in_direct": True,
            "allowed_groups": [str(test_group.id)],
            "response_type": "auto_reply",
            "response_content": {"reply_template": "你好，我是{agent_name}，很高兴为您服务！"}
        }
    )
    if created:
        print(f"创建测试规则: {rule.name}")
    else:
        print(f"测试规则已存在: {rule.name}")
    
    # 7. 创建另一个测试规则
    rule2, created = AgentListeningRule.objects.get_or_create(
        name="帮助规则",
        agent=test_agent,
        defaults={
            "description": "当有人询问帮助时回复",
            "is_active": True,
            "priority": 2,
            "trigger_type": "keyword",
            "trigger_condition": {"keywords": ["帮助", "help", "怎么用"]},
            "listen_in_groups": True,
            "listen_in_direct": True,
            "allowed_groups": [str(test_group.id)],
            "response_type": "auto_reply",
            "response_content": {"reply_template": "我可以帮助您解答问题，请告诉我您需要什么帮助？"}
        }
    )
    if created:
        print(f"创建测试规则: {rule2.name}")
    else:
        print(f"测试规则已存在: {rule2.name}")
    
    print("测试数据创建完成！")
    print(f"\n测试群组ID: {test_group.id} (用于WebSocket连接)")
    print(f"测试用户: {test_user.username} / testpassword")
    print(f"测试代理: {test_agent.name}")
    print("请使用这些信息登录并测试WebSocket功能。")

if __name__ == "__main__":
    create_test_data() 