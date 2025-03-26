from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
import logging
import json
import requests
from django.conf import settings
import openai
from django.utils import timezone
from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import AgentErrorCodes
from .utils import test_rule_match, apply_rule_transformations

from .models import Agent, AgentSkill, AgentInteraction, AgentListeningRule
from .serializers import (
    AgentSerializer, AgentCreateSerializer, AgentSkillSerializer,
    AgentInteractionSerializer, AgentListeningRuleSerializer, 
    AgentListeningRuleCreateSerializer
)
from .permissions import IsAgentOwnerOrAdmin, IsPublicAgentOrOwnerOrAdmin
from .services import RuleEngine

logger = logging.getLogger('agents')


class AgentViewSet(viewsets.ModelViewSet):
    """
    AI代理的API视图集
    提供AI代理的列表、详情、创建、更新、删除等功能
    """
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAgentOwnerOrAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'role']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-updated_at']

    def get_queryset(self):
        """
        根据用户身份过滤查询集:
        - 管理员可以看到所有代理
        - 普通用户只能看到自己的代理和公开的代理
        """
        user = self.request.user
        if user.is_staff:
            return Agent.objects.all()
        # 返回用户自己的代理和公开的代理
        return Agent.objects.filter(Q(owner=user) | Q(is_public=True))

    def get_serializer_class(self):
        """根据动作使用不同的序列化器"""
        if self.action == 'create':
            return AgentCreateSerializer
        return AgentSerializer

    def perform_create(self, serializer):
        """创建代理时设置所有者为当前用户"""
        serializer.save(owner=self.request.user)
        logger.info(f"用户 {self.request.user.username} 创建了新代理 '{serializer.instance.name}'")

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        """
        设置代理状态
        PUT /api/agents/{id}/set_status/
        参数: status - 新状态值
        """
        agent = self.get_object()
        status_value = request.data.get('status')
        
        if not status_value:
            return Response(
                {'error': _('必须提供status字段')}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if status_value not in Agent.Status.values:
            return Response(
                {'error': _('无效的状态值，可用选项：') + ', '.join(Agent.Status.values)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        success = agent.set_status(status_value)
        if success:
            logger.info(f"用户 {request.user.username} 将代理 '{agent.name}' 的状态改为 '{status_value}'")
            return Response(AgentSerializer(agent).data)
        else:
            return Response(
                {'error': _('更新状态失败')},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def my_agents(self, request):
        """
        获取当前用户拥有的所有代理
        GET /api/agents/my_agents/
        """
        agents = Agent.objects.filter(owner=request.user)
        serializer = self.get_serializer(agents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def public_agents(self, request):
        """
        获取所有公开的代理
        GET /api/agents/public_agents/
        """
        agents = Agent.objects.filter(is_public=True)
        serializer = self.get_serializer(agents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def chat(self, request, pk=None):
        """
        与代理聊天的API端点
        POST /api/agents/{id}/chat/
        参数: 
          - message: 用户发送的消息
          - context: 可选的上下文信息，包含历史消息等
          - use_history: 是否使用历史对话作为上下文，默认为true
          - history_hours: 获取多少小时内的历史，默认为24小时
        """
        agent = self.get_object()
        
        # 检查代理是否可用
        if not agent.is_available():
            return Response(
                {'error': _('该代理当前不可用，状态：') + agent.get_status_display()},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 获取请求数据
        message = request.data.get('message')
        context = request.data.get('context', {})
        use_history = request.data.get('use_history', True)
        history_hours = request.data.get('history_hours', 24)
        
        if not message:
            return Response(
                {'error': _('必须提供message字段')},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 记录用户消息
        logger.info(f"用户 {request.user.username} 向代理 '{agent.name}' 发送消息: {message[:50]}...")
        
        try:
            # 如果需要使用历史对话但未提供context中的历史
            if use_history and not context.get('previous_messages'):
                # 获取与该用户的历史对话
                conversation_history = agent.get_conversation_history(
                    user=request.user,
                    hours=history_hours
                )
                
                # 添加到上下文
                context['previous_messages'] = conversation_history
                
            # 调用AI模型生成响应
            response_content = self._generate_ai_response(agent, message, context)
            
            # 将代理状态设置为忙碌中
            previous_status = agent.status
            if previous_status == Agent.Status.ONLINE:
                agent.set_status(Agent.Status.BUSY)
            
            # 创建交互记录
            interaction = AgentInteraction.objects.create(
                initiator=agent,
                receiver=agent,  # 自己与自己对话记录
                content={
                    'user_message': message,
                    'agent_response': response_content,
                    'context': context
                },
                interaction_type=AgentInteraction.InteractionType.MESSAGE
            )
            
            # 恢复之前的状态
            if previous_status == Agent.Status.ONLINE:
                agent.set_status(Agent.Status.ONLINE)
                
            return Response({
                'agent_id': agent.id,
                'agent_name': agent.name,
                'message': message,
                'response': response_content,
                'interaction_id': interaction.id,
                'timestamp': interaction.timestamp,
                'has_history': bool(context.get('previous_messages')),
                'history_count': len(context.get('previous_messages', []))
            })
            
        except Exception as e:
            logger.error(f"处理代理 '{agent.name}' 的聊天请求时出错: {str(e)}")
            return Response(
                {'error': _('处理聊天请求时出错: ') + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_ai_response(self, agent, message, context=None):
        """
        使用AI模型生成代理响应
        
        参数:
        - agent: 代理对象
        - message: 用户消息
        - context: 对话上下文，包含历史消息等
        
        返回:
        - AI生成的响应文本
        """
        # 检查是否应该使用模拟响应（测试环境或未配置API）
        if settings.USE_MOCK_AI_IN_TEST or not settings.OPENAI_API_KEY:
            return self._generate_mock_response(agent, message, context)
        
        # 获取模型配置
        model_config = agent.model_config or {}
        model_name = model_config.get('model', settings.DEFAULT_AI_MODEL)
        
        # 获取系统提示
        system_prompt = agent.system_prompt or f"你是一个名为{agent.name}的{agent.get_role_display()}。"
        
        # 构建对话历史
        conversation = []
        
        # 添加系统消息
        conversation.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史
        if context and 'previous_messages' in context:
            for prev_msg in context['previous_messages']:
                if 'user' in prev_msg:
                    conversation.append({"role": "user", "content": prev_msg['user']})
                if 'assistant' in prev_msg:
                    conversation.append({"role": "assistant", "content": prev_msg['assistant']})
        
        # 添加当前用户消息
        conversation.append({"role": "user", "content": message})
        
        # 确定调用哪个模型API
        api_type = model_config.get('api_type', 'openai')
        
        if api_type == 'openai':
            return self._call_openai_api(conversation, model_name, model_config)
        else:
            # 默认返回模拟响应
            return self._generate_mock_response(agent, message, context)
    
    def _call_openai_api(self, conversation, model_name='gpt-3.5-turbo', config=None):
        """调用OpenAI API生成回复"""
        config = config or {}
        
        try:
            # 设置API密钥
            openai.api_key = settings.OPENAI_API_KEY
            
            # 设置参数
            temperature = config.get('temperature', 0.7)
            max_tokens = config.get('max_tokens', 1000)
            
            # 调用API
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # 提取回复文本
            reply = response.choices[0].message.content
            return reply
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            return f"抱歉，我遇到了技术问题，无法回复你的消息。错误: {str(e)}"
    
    def _generate_mock_response(self, agent, message, context):
        """生成模拟的代理响应（仅用于测试或API不可用时）"""
        # 根据代理角色生成不同的响应
        role_responses = {
            Agent.Role.PRODUCT_MANAGER: f"作为产品经理，我认为我们应该关注用户需求。关于'{message}'，我建议我们进行更多用户调研。",
            Agent.Role.FRONTEND_DEV: f"从前端开发的角度，实现'{message}'需要考虑UI/UX设计和响应式布局。",
            Agent.Role.BACKEND_DEV: f"从后端开发的角度，处理'{message}'需要设计合适的API和数据模型。",
            Agent.Role.UX_DESIGNER: f"作为UX设计师，我认为'{message}'的用户体验可以通过以下方式改进...",
            Agent.Role.QA_TESTER: f"作为测试工程师，我会为'{message}'设计以下测试用例...",
            Agent.Role.DATA_ANALYST: f"基于数据分析，关于'{message}'的数据显示...",
            Agent.Role.VIRTUAL_FRIEND: f"嗨，朋友！关于'{message}'，我想和你分享我的想法...",
            Agent.Role.ASSISTANT: f"我可以帮你处理'{message}'。请告诉我更多细节。",
        }
        
        # 获取对应角色的响应，如果没有则使用默认响应
        response = role_responses.get(
            agent.role, 
            f"我是{agent.name}，我收到了你的消息：'{message}'。请问还有什么我可以帮助你的吗？"
        )
        
        # 添加模拟回复的说明
        response += "\n\n(注意：这是一个模拟回复，因为API服务未配置或不可用)"
            
        return response

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        获取与特定代理的对话历史
        GET /api/agents/{id}/history/
        参数:
          - hours: 获取多少小时内的历史，默认24小时
          - limit: 最多返回多少条记录，默认20条
        """
        agent = self.get_object()
        
        # 获取请求参数
        hours = int(request.query_params.get('hours', 24))
        limit = int(request.query_params.get('limit', 20))
        
        try:
            # 获取历史对话
            conversation_history = agent.get_conversation_history(
                user=request.user,
                hours=hours,
                limit=limit
            )
            
            # 返回结果
            return Response({
                'agent_id': agent.id,
                'agent_name': agent.name,
                'role': agent.get_role_display(),
                'history': conversation_history,
                'count': len(conversation_history)
            })
            
        except Exception as e:
            logger.error(f"获取代理 '{agent.name}' 的对话历史时出错: {str(e)}")
            return Response(
                {'error': _('获取对话历史时出错: ') + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=False, methods=['get'])
    def my_conversations(self, request):
        """
        获取当前用户与所有代理的对话历史
        GET /api/agents/my_conversations/
        参数:
          - hours: 获取多少小时内的历史，默认24小时
          - limit: 最多返回多少条记录，默认为每个代理20条
        """
        # 获取请求参数
        hours = int(request.query_params.get('hours', 24))
        limit = int(request.query_params.get('limit', 20))
        
        try:
            # 获取用户与所有代理的对话
            conversations = AgentInteraction.get_user_agent_conversations(
                user=request.user,
                hours=hours,
                limit=limit
            )
            
            # 返回结果
            return Response({
                'conversations': conversations,
                'agent_count': len(conversations)
            })
            
        except Exception as e:
            logger.error(f"获取用户 '{request.user.username}' 的所有对话历史时出错: {str(e)}")
            return Response(
                {'error': _('获取对话历史时出错: ') + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """部署代理到生产环境"""
        agent = self.get_object()
        
        if not agent.is_validated:
            return ErrorUtils.format_error_response(
                error_code=AgentErrorCodes.NOT_VALIDATED,
                message="代理必须先通过验证才能部署",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            agent.status = 'deployed'
            agent.deployed_at = timezone.now()
            agent.save()
            
            serializer = self.get_serializer(agent)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"部署代理失败: {str(e)}", exc_info=True)
            return ErrorUtils.handle_exception(
                request,
                e,
                AgentErrorCodes.DEPLOY_FAILED,
                "部署代理失败，请稍后再试"
            )

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """验证代理的规则和行为"""
        agent = self.get_object()
        
        try:
            # 验证代理的规则
            validation_result = validate_agent_rules(agent)
            
            if validation_result['valid']:
                agent.is_validated = True
                agent.validation_message = "验证通过"
            else:
                agent.is_validated = False
                agent.validation_message = validation_result['message']
            
            agent.validated_at = timezone.now()
            agent.save()
            
            return Response({
                'valid': agent.is_validated,
                'message': agent.validation_message
            })
        except Exception as e:
            logger.error(f"验证代理失败: {str(e)}", exc_info=True)
            return ErrorUtils.handle_exception(
                request,
                e,
                AgentErrorCodes.VALIDATION_FAILED,
                "验证代理失败，请稍后再试"
            )


class AgentSkillViewSet(viewsets.ModelViewSet):
    """
    代理技能的API视图集
    提供技能的列表、详情、创建、更新、删除等功能
    """
    queryset = AgentSkill.objects.all()
    serializer_class = AgentSkillSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['name']

    def get_queryset(self):
        """
        根据用户身份过滤查询集:
        - 管理员可以看到所有技能
        - 普通用户只能看到公开的技能或与他们相关的技能
        """
        user = self.request.user
        if user.is_staff:
            return AgentSkill.objects.all()
        # 返回与用户相关的技能
        return AgentSkill.objects.filter(
            Q(agents__owner=user) | Q(configuration__is_public=True)
        ).distinct()


class AgentInteractionViewSet(viewsets.ModelViewSet):
    """
    代理交互记录的API视图集
    提供交互的列表、详情、创建等功能
    """
    serializer_class = AgentInteractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        """
        根据用户身份和参数过滤查询集
        """
        user = self.request.user
        queryset = AgentInteraction.objects.all()
        
        # 管理员可以看到所有交互记录
        if not user.is_staff:
            # 普通用户只能看到与他们的代理相关的交互
            user_agents = Agent.objects.filter(owner=user).values_list('id', flat=True)
            queryset = queryset.filter(
                Q(initiator_id__in=user_agents) | Q(receiver_id__in=user_agents)
            )
            
        # 过滤特定代理的交互
        agent_id = self.request.query_params.get('agent_id')
        if agent_id:
            queryset = queryset.filter(
                Q(initiator_id=agent_id) | Q(receiver_id=agent_id)
            )
            
        return queryset

    def perform_create(self, serializer):
        """
        创建交互记录前验证用户权限
        用户只能创建他们拥有的代理的交互记录
        """
        initiator_id = serializer.validated_data.get('initiator').id
        receiver_id = serializer.validated_data.get('receiver').id
        user = self.request.user
        
        # 检查用户是否拥有发起者代理
        if not user.is_staff:
            initiator = get_object_or_404(Agent, id=initiator_id)
            if initiator.owner != user:
                logger.warning(f"用户 {user.username} 尝试为非自己拥有的代理 {initiator.name} 创建交互记录，已拒绝")
                raise permissions.exceptions.PermissionDenied(
                    _("您不能为不属于您的代理创建交互记录")
                )
                
        serializer.save()
        logger.info(f"创建了新的代理交互记录: {serializer.instance}")


class AgentListeningRuleViewSet(viewsets.ModelViewSet):
    """
    代理监听规则的API视图集
    提供监听规则的列表、详情、创建、更新、删除等功能
    """
    serializer_class = AgentListeningRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['priority', 'created_at', 'updated_at', 'name']
    ordering = ['priority', '-updated_at']
    
    def get_queryset(self):
        """
        根据用户身份过滤查询集:
        - 管理员可以看到所有规则
        - 普通用户只能看到自己的代理的规则
        """
        user = self.request.user
        if user.is_staff:
            return AgentListeningRule.objects.all()
        
        # 返回用户自己的代理的规则
        user_agents = Agent.objects.filter(owner=user)
        return AgentListeningRule.objects.filter(agent__in=user_agents)
    
    def get_serializer_class(self):
        """根据动作使用不同的序列化器"""
        if self.action == 'create':
            return AgentListeningRuleCreateSerializer
        return AgentListeningRuleSerializer
    
    def perform_create(self, serializer):
        """创建规则时的额外处理"""
        rule = serializer.save()
        agent = rule.agent
        logger.info(f"用户 {self.request.user.username} 为代理 '{agent.name}' 创建了新的监听规则 '{rule.name}'")
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        切换规则的激活状态
        POST /api/agent-rules/{id}/toggle_active/
        """
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save(update_fields=['is_active', 'updated_at'])
        
        status_text = "激活" if rule.is_active else "禁用"
        logger.info(f"用户 {request.user.username} {status_text}了代理 '{rule.agent.name}' 的规则 '{rule.name}'")
        
        return Response({
            'id': rule.id,
            'name': rule.name,
            'is_active': rule.is_active
        })
    
    @action(detail=True, methods=['post'])
    def test_rule(self, request, pk=None):
        """测试规则匹配"""
        rule = self.get_object()
        message_data = request.data.get('message')
        
        if not message_data:
            return ErrorUtils.format_error_response(
                error_code=AgentErrorCodes.MISSING_REQUIRED_FIELD,
                message="需要提供测试消息数据",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 测试规则匹配
            match_result = test_rule_match(rule, message_data)
            
            # 如果匹配成功且需要转换，应用转换操作
            transformed_message = None
            if match_result.get('matches') and request.data.get('apply_transformation', False):
                transformed_message = apply_rule_transformations(rule, message_data, match_result)
            
            # 构建响应数据
            response_data = {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'matches': match_result.get('matches'),
                'match_details': match_result.get('details', {})
            }
            
            # 添加错误信息（如果有）
            if 'error' in match_result:
                response_data['error'] = match_result['error']
                response_data['error_code'] = match_result.get('error_code')
            
            # 添加转换后的消息（如果有）
            if transformed_message:
                response_data['transformed_message'] = transformed_message
            
            return Response(response_data)
        
        except Exception as e:
            logger.error(f"规则测试失败: {str(e)}", exc_info=True)
            return ErrorUtils.handle_exception(
                request,
                e,
                AgentErrorCodes.RULE_TEST_FAILED,
                "规则测试失败，请稍后再试"
            )
    
    @action(detail=False, methods=['get'])
    def by_agent(self, request):
        """
        获取指定代理的所有规则
        GET /api/agent-rules/by_agent/?agent_id={id}
        """
        agent_id = request.query_params.get('agent_id')
        if not agent_id:
            return Response(
                {'error': _('必须提供agent_id参数')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 确认用户是否有权限查看该代理的规则
        agent = get_object_or_404(Agent, id=agent_id)
        if not request.user.is_staff and agent.owner != request.user:
            return Response(
                {'error': _('您没有权限查看此代理的规则')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        rules = AgentListeningRule.objects.filter(agent=agent).order_by('priority')
        serializer = self.get_serializer(rules, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def process_message(self, request):
        """
        手动处理消息，获取可能的规则响应
        POST /api/agent-rules/process_message/
        参数:
          - message: 消息内容
          - context: 上下文信息（可选）
        """
        message = request.data.get('message')
        context = request.data.get('context', {})
        
        if not message:
            return Response(
                {'error': _('必须提供message字段')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 使用规则引擎处理消息
        responses = RuleEngine.process_message(message, context)
        
        return Response({
            'message': message,
            'responses': responses,
            'response_count': len(responses)
        })

# 添加一个假设的验证函数 (实际实现应根据具体需求)
def validate_agent_rules(agent):
    """验证代理规则的逻辑"""
    # 示例验证逻辑
    try:
        rules = agent.rules.all()
        if not rules.exists():
            return {'valid': False, 'message': '代理必须至少有一条规则'}
        
        # 更多验证逻辑...
        
        return {'valid': True, 'message': '所有规则验证通过'}
    except Exception as e:
        logger.error(f"规则验证过程出错: {str(e)}", exc_info=True)
        return {'valid': False, 'message': f'验证过程出错: {str(e)}'}

def rule_management_view(request):
    """代理规则管理页面"""
    if not request.user.is_authenticated:
        return redirect('login')  # 重定向到登录页面
        
    return render(request, 'agents/rule_management.html')


def agent_management_view(request):
    """代理管理页面"""
    if not request.user.is_authenticated:
        return redirect('login')  # 重定向到登录页面
        
    return render(request, 'agents/agent_management.html')


def agent_demo(request):
    """展示@代理功能的示例页面"""
    if not request.user.is_authenticated:
        return redirect('login')  # 重定向到登录页面
    
    # 获取可用的代理列表
    agents = Agent.objects.filter(
        Q(is_public=True) | 
        Q(owner=request.user)
    ).order_by('-updated_at')[:10]
    
    # 查找或创建一个示例群组
    from groups.models import Group, GroupMember
    demo_group, created = Group.objects.get_or_create(
        name="代理演示群组",
        defaults={
            'owner': request.user,
            'description': "这是一个用于演示@代理功能的群组",
            'is_public': True
        }
    )
    
    # 确保当前用户是群组成员
    GroupMember.objects.get_or_create(
        group=demo_group,
        user=request.user,
        defaults={
            'member_type': 'human',
            'role': 'admin'
        }
    )
    
    # 确保每个代理都是群组成员
    for agent in agents:
        GroupMember.objects.get_or_create(
            group=demo_group,
            agent=agent,
            defaults={
                'member_type': 'agent',
                'role': 'member'
            }
        )
    
    return render(request, 'agents/agent_demo.html', {
        'agents': agents,
        'demo_group': demo_group
    })
