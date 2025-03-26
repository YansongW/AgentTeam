import logging
import json
from django.db.models import Q
from django.utils import timezone
from .models import Agent, AgentListeningRule, AgentInteraction

logger = logging.getLogger(__name__)

class RuleEngine:
    """
    代理监听规则引擎
    
    处理消息匹配规则并执行相应的操作
    """
    
    @staticmethod
    def process_message(message, context=None):
        """
        处理消息，检查是否匹配规则并执行响应
        
        参数:
        - message: 消息内容，字典格式
        - context: 上下文信息，可包含群组ID、发送者ID等
        
        返回:
        - 规则响应列表
        """
        if context is None:
            context = {}
            
        # 转换消息格式，确保包含必要的字段
        normalized_message = RuleEngine._normalize_message(message, context)
        
        # 获取最近的消息历史作为上下文（如果可用）
        if 'group_id' in normalized_message and 'message_history' in context:
            group_id = normalized_message['group_id']
            if group_id in context['message_history']:
                normalized_message['context_messages'] = context['message_history'][group_id]
        
        # 如果消息内容是字符串，尝试进行情感分析
        if isinstance(normalized_message.get('content', ''), str):
            content = normalized_message['content']
            try:
                from agents.utils.sentiment_analyzer import analyze_sentiment
                sentiment_score = analyze_sentiment(content)
                normalized_message['sentiment'] = {
                    'score': sentiment_score,
                    'type': 'positive' if sentiment_score > 0.2 else ('negative' if sentiment_score < -0.2 else 'neutral')
                }
            except ImportError:
                logger.warning("情感分析模块未找到，跳过情感分析")
            except Exception as e:
                logger.error(f"情感分析过程中出错: {str(e)}")
            
        # 获取可能适用的规则
        applicable_rules = RuleEngine._get_applicable_rules(normalized_message)
        
        # 存储规则响应
        responses = []
        
        # 遍历规则并检查匹配
        for rule in applicable_rules:
            try:
                # 检查规则是否可以触发
                if not rule.can_trigger():
                    continue
                
                # 检查消息是否匹配规则
                if rule.match_message(normalized_message):
                    # 执行规则响应
                    response = rule.execute_response(normalized_message)
                    
                    if response:
                        # 添加规则元数据
                        response['rule_metadata'] = {
                            'rule_id': str(rule.id),
                            'rule_name': rule.name,
                            'trigger_type': rule.trigger_type,
                            'priority': rule.priority
                        }
                        
                        # 记录交互
                        RuleEngine._record_interaction(rule, normalized_message, response)
                        
                        # 添加到响应列表
                        responses.append(response)
                        
                        # 如果是高优先级规则且配置为独占，则停止处理其他规则
                        if rule.priority <= 5 and rule.trigger_condition.get('exclusive', False):
                            break
                            
            except Exception as e:
                logger.error(f"处理规则 {rule.name} (ID: {rule.id}) 时出错: {str(e)}", exc_info=True)
                continue
        
        return responses
    
    @staticmethod
    def _normalize_message(message, context):
        """
        标准化消息格式
        
        参数:
        - message: 原始消息
        - context: 上下文信息
        
        返回:
        - 标准化的消息字典
        """
        if isinstance(message, str):
            # 如果消息是字符串，转换为标准格式
            normalized = {
                'content': message,
                'content_type': 'text',
                'timestamp': timezone.now().isoformat()
            }
        else:
            # 复制消息以避免修改原始数据
            normalized = message.copy()
        
        # 确保基本字段存在
        if 'content_type' not in normalized:
            normalized['content_type'] = 'text'
            
        if 'timestamp' not in normalized:
            normalized['timestamp'] = timezone.now().isoformat()
            
        # 添加上下文信息
        if context:
            normalized.update({
                k: v for k, v in context.items()
                if k not in normalized  # 不覆盖已有字段
            })
            
        # 处理提及信息
        if 'content' in normalized and isinstance(normalized['content'], str):
            # 提取@提及
            mentions = []
            content = normalized['content']
            
            # 匹配@用户或@agent:名称格式
            import re
            mention_pattern = r'@(?:agent:)?([^\s]+)'
            found_mentions = re.finditer(mention_pattern, content)
            
            for match in found_mentions:
                mentions.append(match.group(1))
            
            normalized['mentions'] = mentions
            
        return normalized
    
    @staticmethod
    def _get_applicable_rules(message):
        """
        获取可能适用于该消息的规则
        
        参数:
        - message: 标准化的消息
        
        返回:
        - 规则查询集，按优先级排序
        """
        # 基本查询条件：规则必须处于激活状态
        query = Q(is_active=True)
        
        # 根据消息上下文筛选规则
        group_id = message.get('group_id')
        
        if group_id:
            # 群组消息
            query &= Q(listen_in_groups=True)
            
            # 检查是否限制了特定群组
            query &= (
                Q(allowed_groups=[]) |  # 空列表表示所有群组
                Q(allowed_groups__contains=[str(group_id)])
            )
        else:
            # 直接消息
            query &= Q(listen_in_direct=True)
        
        # 如果消息中有明确提到的代理
        mentions = message.get('mentions', [])
        if mentions:
            # 查找被提及的代理的规则
            query |= Q(agent__id__in=mentions, trigger_type='mention')
            
        # 查询规则并按优先级排序
        return AgentListeningRule.objects.filter(query).order_by('priority')
    
    @staticmethod
    def _record_interaction(rule, message, response):
        """
        记录代理与消息发送者的交互
        
        参数:
        - rule: 触发的规则
        - message: 消息内容
        - response: 规则响应
        """
        # 仅当消息中包含发送者信息时才记录
        sender_id = message.get('sender')
        if not sender_id:
            return
            
        try:
            # 查找发送者代理
            sender_agent = Agent.objects.get(id=sender_id)
            
            # 创建交互记录
            AgentInteraction.objects.create(
                initiator=sender_agent,
                receiver=rule.agent,
                interaction_type='message',
                content={
                    'user_message': message.get('content', ''),
                    'agent_response': response.get('content', '')
                }
            )
        except Agent.DoesNotExist:
            # 发送者不是代理，可能是普通用户
            logger.debug(f"发送者 {sender_id} 不是代理，跳过交互记录")
        except Exception as e:
            logger.error(f"记录交互时出错: {str(e)}")
            
    @staticmethod
    def get_agent_rules(agent_id):
        """
        获取代理的所有监听规则
        
        参数:
        - agent_id: 代理ID
        
        返回:
        - 规则查询集
        """
        return AgentListeningRule.objects.filter(agent_id=agent_id).order_by('priority')
        
    @staticmethod
    def test_rule(rule_id, message_data, apply_transformation=False):
        """
        测试规则匹配和响应
        
        参数:
        - rule_id: 规则ID
        - message_data: 测试消息内容
        - apply_transformation: 是否应用规则转换
        
        返回:
        - 测试结果
        """
        try:
            # 查找规则
            rule = AgentListeningRule.objects.get(id=rule_id)
            
            # 标准化消息
            normalized_message = RuleEngine._normalize_message(message_data, {})
            
            # 测试匹配
            match_result = rule.match_message(normalized_message)
            
            result = {
                'rule': {
                    'id': str(rule.id),
                    'name': rule.name,
                    'trigger_type': rule.trigger_type,
                    'priority': rule.priority
                },
                'message': normalized_message,
                'match': match_result
            }
            
            # 如果匹配且需要应用转换
            if match_result and apply_transformation:
                response = rule.execute_response(normalized_message)
                result['response'] = response
                
            return result
            
        except AgentListeningRule.DoesNotExist:
            return {'error': f'规则未找到: {rule_id}'}
        except Exception as e:
            logger.error(f"测试规则时出错: {str(e)}", exc_info=True)
            return {'error': f'测试过程出错: {str(e)}'}
    
    @staticmethod
    def get_recent_messages(group_id, limit=10):
        """
        获取群组最近的消息
        
        参数:
        - group_id: 群组ID
        - limit: 返回的消息数量
        
        返回:
        - 消息列表
        """
        # 实际应用中，这里应该从数据库中查询群组消息
        from groups.models import GroupMessage
        
        try:
            messages = GroupMessage.objects.filter(
                group_id=group_id
            ).order_by('-timestamp')[:limit]
            
            # 转换为标准化格式
            result = []
            for msg in messages:
                result.append({
                    'id': str(msg.id),
                    'content': msg.content.get('text', ''),
                    'sender': msg.sender_user_id or msg.sender_agent_id,
                    'sender_type': msg.sender_type,
                    'timestamp': msg.timestamp.isoformat(),
                    'group_id': str(msg.group_id)
                })
                
            return result
            
        except Exception as e:
            logger.error(f"获取群组消息时出错: {str(e)}", exc_info=True)
            return [] 