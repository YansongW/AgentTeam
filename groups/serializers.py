from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Group, GroupMember, GroupMessage, GroupRule
from agents.serializers import AgentSerializer
from agents.models import AgentListeningRule

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """用户基本信息序列化器"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'avatar')
        read_only_fields = ('email',)


class GroupMinimalSerializer(serializers.ModelSerializer):
    """最小化的群组序列化器"""
    class Meta:
        model = Group
        fields = ('id', 'name', 'is_public')
        read_only_fields = ('id',)


class GroupCreateSerializer(serializers.ModelSerializer):
    """群组创建序列化器"""
    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'is_public', 'avatar', 'group_settings')
        
    def create(self, validated_data):
        # 获取当前用户作为群组所有者
        user = self.context['request'].user
        group = Group.objects.create(owner=user, **validated_data)
        
        # 自动将创建者加入为管理员
        GroupMember.objects.create(
            group=group,
            user=user,
            member_type=GroupMember.MemberType.HUMAN,
            role=GroupMember.Role.ADMIN
        )
        
        return group


class GroupMemberDetailSerializer(serializers.ModelSerializer):
    """群组成员详细信息序列化器（用于嵌套在群组详情中）"""
    user_name = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMember
        fields = ('id', 'user', 'agent', 'role', 'user_name', 'agent_name', 'role_display')
    
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.username
        return None
    
    def get_agent_name(self, obj):
        if obj.agent:
            return obj.agent.name
        return None
    
    def get_role_display(self, obj):
        return obj.get_role_display()


class AgentRuleSerializer(serializers.ModelSerializer):
    """代理规则序列化器，用于嵌套在群组详情中"""
    trigger_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentListeningRule
        fields = ('id', 'name', 'description', 'priority', 'trigger_type', 
                  'trigger_type_display', 'is_active', 'agent')
    
    def get_trigger_type_display(self, obj):
        return obj.get_trigger_type_display()


class GroupSerializer(serializers.ModelSerializer):
    """群组序列化器"""
    owner = UserBasicSerializer(read_only=True)
    owner_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    rules = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'owner', 'owner_name', 'is_public', 
                  'created_at', 'updated_at', 'avatar', 'group_settings',
                  'member_count', 'is_member', 'is_owner', 'members', 'rules')
        read_only_fields = ('owner', 'created_at', 'updated_at', 'member_count', 
                           'is_member', 'is_owner', 'members', 'rules')
    
    def get_owner_name(self, obj):
        """获取群主用户名"""
        if obj.owner:
            return obj.owner.username
        return None
    
    def get_member_count(self, obj):
        """获取群组成员数量"""
        return obj.get_member_count()
    
    def get_is_member(self, obj):
        """检查当前用户是否为群组成员"""
        user = self.context['request'].user
        return GroupMember.objects.filter(group=obj, user=user, is_active=True).exists()
    
    def get_is_owner(self, obj):
        """检查当前用户是否为群组所有者"""
        user = self.context['request'].user
        return obj.owner == user
    
    def get_members(self, obj):
        """获取群组成员列表"""
        # 只在详情视图中返回成员列表
        if self.context['request'].parser_context.get('kwargs', {}).get('pk'):
            members = GroupMember.objects.filter(group=obj, is_active=True)
            serializer = GroupMemberDetailSerializer(members, many=True)
            return serializer.data
        return None
    
    def get_rules(self, obj):
        """获取与此群组相关的代理监听规则"""
        # 只在详情视图中返回规则列表
        if self.context['request'].parser_context.get('kwargs', {}).get('pk'):
            # 获取群组中的所有代理成员
            agent_members = GroupMember.objects.filter(
                group=obj, 
                agent__isnull=False, 
                is_active=True
            ).values_list('agent_id', flat=True)
            
            # 获取这些代理的监听规则
            rules = AgentListeningRule.objects.filter(agent_id__in=agent_members)
            serializer = AgentRuleSerializer(rules, many=True)
            return serializer.data
        return None


class GroupMemberSerializer(serializers.ModelSerializer):
    """群组成员序列化器"""
    user_details = UserBasicSerializer(source='user', read_only=True)
    agent_details = AgentSerializer(source='agent', read_only=True)
    member_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMember
        fields = ('id', 'group', 'user', 'agent', 'member_type', 'role', 
                  'joined_at', 'is_active', 'member_settings',
                  'user_details', 'agent_details', 'member_name')
        read_only_fields = ('joined_at',)
    
    def get_member_name(self, obj):
        """获取成员显示名称"""
        if obj.member_type == GroupMember.MemberType.HUMAN and obj.user:
            return obj.user.username
        elif obj.member_type == GroupMember.MemberType.AGENT and obj.agent:
            return obj.agent.name
        return '未知成员'
    
    def validate(self, data):
        """验证数据一致性"""
        member_type = data.get('member_type')
        user = data.get('user')
        agent = data.get('agent')
        
        if member_type == GroupMember.MemberType.HUMAN:
            if not user:
                raise serializers.ValidationError("人类成员必须关联一个用户账号")
            if agent:
                raise serializers.ValidationError("人类成员不应关联代理")
                
        elif member_type == GroupMember.MemberType.AGENT:
            if not agent:
                raise serializers.ValidationError("代理成员必须关联一个代理")
            if user:
                raise serializers.ValidationError("代理成员不应关联用户账号")
                
        return data


class GroupMessageSerializer(serializers.ModelSerializer):
    """群组消息序列化器"""
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMessage
        fields = ('id', 'group', 'sender_user', 'sender_agent', 'sender_type',
                  'content', 'message_type', 'timestamp', 'parent_message',
                  'mentioned_users', 'mentioned_agents', 'metadata', 'sender_name')
        read_only_fields = ('timestamp',)
    
    def get_sender_name(self, obj):
        """获取发送者名称"""
        if obj.sender_type == GroupMessage.SenderType.HUMAN and obj.sender_user:
            return obj.sender_user.username
        elif obj.sender_type == GroupMessage.SenderType.AGENT and obj.sender_agent:
            return obj.sender_agent.name
        return '系统'
    
    def validate(self, data):
        """验证数据一致性"""
        sender_type = data.get('sender_type')
        sender_user = data.get('sender_user')
        sender_agent = data.get('sender_agent')
        
        if sender_type == GroupMessage.SenderType.HUMAN:
            if not sender_user:
                raise serializers.ValidationError("人类发送者必须关联一个用户账号")
            if sender_agent:
                raise serializers.ValidationError("人类发送者不应关联代理")
                
        elif sender_type == GroupMessage.SenderType.AGENT:
            if not sender_agent:
                raise serializers.ValidationError("代理发送者必须关联一个代理")
            if sender_user:
                raise serializers.ValidationError("代理发送者不应关联用户账号")
                
        elif sender_type == GroupMessage.SenderType.SYSTEM:
            if sender_user or sender_agent:
                raise serializers.ValidationError("系统消息不应关联用户或代理")
                
        return data
    
    def create(self, validated_data):
        # 处理@提及功能
        content = validated_data.get('content', {})
        message_text = content.get('text', '')
        
        # 创建消息
        message = GroupMessage.objects.create(**validated_data)
        
        # 处理消息中提到的用户和代理（智能识别方法）
        if message_text and isinstance(message_text, str):
            from django.contrib.auth import get_user_model
            from agents.models import Agent
            User = get_user_model()
            
            # 提取所有@后面的名称
            import re
            all_mentions = re.findall(r'@(agent:)?([^\s]+)', message_text)
            
            for mention in all_mentions:
                prefix, name = mention
                
                # 检查是否使用了显式的agent:前缀
                if prefix:
                    # 明确指定为代理
                    try:
                        agent = Agent.objects.filter(name__icontains=name).first()
                        if agent:
                            message.mentioned_agents.add(agent)
                    except Exception:
                        pass
                    continue
                
                # 没有明确前缀，先尝试查找用户
                try:
                    user = User.objects.filter(username=name).first()
                    if user:
                        message.mentioned_users.add(user)
                        continue
                except User.DoesNotExist:
                    pass
                
                # 如果找不到用户，尝试查找代理
                try:
                    # 先尝试完全匹配
                    agent = Agent.objects.filter(name=name).first()
                    if agent:
                        message.mentioned_agents.add(agent)
                        continue
                        
                    # 如果完全匹配找不到，尝试包含匹配
                    agent = Agent.objects.filter(name__icontains=name).first()
                    if agent:
                        message.mentioned_agents.add(agent)
                except Exception:
                    pass
        
        return message


class GroupRuleSerializer(serializers.ModelSerializer):
    """群组规则序列化器"""
    class Meta:
        model = GroupRule
        fields = ('id', 'group', 'name', 'description', 'rule_type',
                  'target_agents', 'condition', 'action', 'priority',
                  'is_active', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at') 