from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Agent, AgentSkill, AgentSkillAssignment, AgentInteraction, AgentListeningRule


class AgentMinimalSerializer(serializers.ModelSerializer):
    """简化版的代理序列化器，只包含最基本的信息"""
    
    class Meta:
        model = Agent
        fields = ['id', 'name', 'role', 'status', 'is_public']
        read_only_fields = ['id']


class AgentSkillSerializer(serializers.ModelSerializer):
    """代理技能序列化器"""
    
    class Meta:
        model = AgentSkill
        fields = ['id', 'name', 'description', 'configuration', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentSkillAssignmentSerializer(serializers.ModelSerializer):
    """代理技能分配序列化器"""
    skill_name = serializers.ReadOnlyField(source='skill.name')
    
    class Meta:
        model = AgentSkillAssignment
        fields = ['id', 'skill', 'skill_name', 'custom_configuration', 'enabled', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentSerializer(serializers.ModelSerializer):
    """AI代理序列化器"""
    owner_username = serializers.ReadOnlyField(source='owner.username')
    role_display = serializers.ReadOnlyField(source='get_role_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    skill_assignments = AgentSkillAssignmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'role', 'role_display', 'description', 'owner', 'owner_username',
            'created_at', 'updated_at', 'status', 'status_display', 'is_public',
            'skills', 'system_prompt', 'model_config', 'api_access', 'skill_assignments'
        ]
        read_only_fields = ['id', 'owner', 'owner_username', 'created_at', 'updated_at', 'role_display', 'status_display']
    
    def create(self, validated_data):
        """创建Agent时自动设置当前用户为所有者"""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class AgentCreateSerializer(serializers.ModelSerializer):
    """Agent创建序列化器，用于创建新Agent的简化表单"""
    
    class Meta:
        model = Agent
        fields = ['name', 'role', 'description', 'status', 'is_public', 'system_prompt']
    
    def create(self, validated_data):
        """创建Agent时自动设置当前用户为所有者"""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class AgentInteractionSerializer(serializers.ModelSerializer):
    """代理交互记录序列化器"""
    initiator_name = serializers.ReadOnlyField(source='initiator.name')
    receiver_name = serializers.ReadOnlyField(source='receiver.name')
    interaction_type_display = serializers.ReadOnlyField(source='get_interaction_type_display')
    
    class Meta:
        model = AgentInteraction
        fields = [
            'id', 'initiator', 'initiator_name', 'receiver', 'receiver_name',
            'content', 'interaction_type', 'interaction_type_display', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'initiator_name', 'receiver_name', 'interaction_type_display'] 


class AgentListeningRuleSerializer(serializers.ModelSerializer):
    """代理监听规则序列化器"""
    agent_name = serializers.ReadOnlyField(source='agent.name')
    trigger_type_display = serializers.ReadOnlyField(source='get_trigger_type_display')
    response_type_display = serializers.ReadOnlyField(source='get_response_type_display')
    
    class Meta:
        model = AgentListeningRule
        fields = [
            'id', 'name', 'description', 'agent', 'agent_name',
            'is_active', 'priority',
            'trigger_type', 'trigger_type_display', 'trigger_condition',
            'listen_in_groups', 'listen_in_direct', 'allowed_groups',
            'response_type', 'response_type_display', 'response_content',
            'cooldown_period', 'last_triggered', 'trigger_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_triggered', 
                           'trigger_count', 'agent_name', 'trigger_type_display', 
                           'response_type_display']
    
    def validate(self, data):
        """验证规则数据"""
        
        # 验证触发条件
        trigger_type = data.get('trigger_type')
        trigger_condition = data.get('trigger_condition', {})
        
        if trigger_type == AgentListeningRule.TriggerType.KEYWORD:
            if 'keywords' not in trigger_condition or not isinstance(trigger_condition['keywords'], list):
                raise serializers.ValidationError(
                    {'trigger_condition': _('关键词触发类型必须包含keywords字段，且必须是列表')}
                )
                
            if not trigger_condition['keywords']:
                raise serializers.ValidationError(
                    {'trigger_condition': _('关键词列表不能为空')}
                )
                
        elif trigger_type == AgentListeningRule.TriggerType.REGEX:
            if 'pattern' not in trigger_condition or not isinstance(trigger_condition['pattern'], str):
                raise serializers.ValidationError(
                    {'trigger_condition': _('正则表达式触发类型必须包含pattern字段，且必须是字符串')}
                )
                
            # 验证正则表达式是否有效
            try:
                import re
                re.compile(trigger_condition['pattern'])
            except Exception as e:
                raise serializers.ValidationError(
                    {'trigger_condition': _('无效的正则表达式: {}').format(str(e))}
                )
        
        # 验证响应内容
        response_type = data.get('response_type')
        response_content = data.get('response_content', {})
        
        if response_type == AgentListeningRule.ResponseType.AUTO_REPLY:
            if 'reply_template' not in response_content or not isinstance(response_content['reply_template'], str):
                raise serializers.ValidationError(
                    {'response_content': _('自动回复类型必须包含reply_template字段，且必须是字符串')}
                )
                
            if not response_content['reply_template'].strip():
                raise serializers.ValidationError(
                    {'response_content': _('回复模板不能为空')}
                )
                
        elif response_type == AgentListeningRule.ResponseType.NOTIFICATION:
            if 'notification_text' not in response_content or not isinstance(response_content['notification_text'], str):
                raise serializers.ValidationError(
                    {'response_content': _('通知类型必须包含notification_text字段，且必须是字符串')}
                )
                
        elif response_type == AgentListeningRule.ResponseType.TASK:
            if 'task_title' not in response_content or not isinstance(response_content['task_title'], str):
                raise serializers.ValidationError(
                    {'response_content': _('任务类型必须包含task_title字段，且必须是字符串')}
                )
        
        return data
    
    def create(self, validated_data):
        """创建监听规则时的附加处理"""
        return super().create(validated_data)


class AgentListeningRuleCreateSerializer(serializers.ModelSerializer):
    """代理监听规则创建序列化器，用于创建新规则的简化表单"""
    
    class Meta:
        model = AgentListeningRule
        fields = [
            'name', 'description', 'agent', 'is_active', 'priority',
            'trigger_type', 'trigger_condition',
            'listen_in_groups', 'listen_in_direct',
            'response_type', 'response_content', 'cooldown_period'
        ]
    
    def validate(self, data):
        """验证创建数据"""
        # 验证用户是否有权限为该代理创建规则
        request = self.context.get('request')
        agent = data.get('agent')
        
        if request and agent and request.user != agent.owner:
            raise serializers.ValidationError(
                {'agent': _('您没有权限为此代理创建规则')}
            )
        
        # 调用父类的验证
        return AgentListeningRuleSerializer().validate(data) 