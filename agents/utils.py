import re
import json
import logging
import traceback
import openai
from django.conf import settings
from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import AgentErrorCodes, RuleErrorCodes

logger = logging.getLogger(__name__)

def test_rule_match(rule, message_data):
    """
    测试消息是否匹配规则
    
    Args:
        rule: AgentListeningRule实例
        message_data: 消息数据字典
    
    Returns:
        dict: 包含匹配结果和详细信息的字典
    """
    try:
        # 检查消息格式
        if not isinstance(message_data, dict):
            return {
                'matches': False,
                'error': '消息数据必须是字典格式',
                'error_code': RuleErrorCodes.INVALID_MESSAGE_FORMAT
            }
        
        # 获取规则条件
        conditions = rule.conditions
        
        # 检查条件格式
        if not isinstance(conditions, dict):
            return {
                'matches': False,
                'error': '规则条件必须是字典格式',
                'error_code': RuleErrorCodes.INVALID_RULE_FORMAT
            }
        
        # 解析消息内容
        message_type = message_data.get('type', '')
        sender_id = message_data.get('sender', {}).get('id', '')
        sender_type = message_data.get('sender', {}).get('type', '')
        content = message_data.get('payload', {}).get('text', '')
        
        # 按条件类型进行匹配
        match_details = {}
        
        # 1. 消息类型匹配
        if 'message_type' in conditions:
            expected_type = conditions['message_type']
            type_match = message_type == expected_type
            match_details['message_type'] = {
                'expected': expected_type,
                'actual': message_type,
                'matches': type_match
            }
            if not type_match:
                return {
                    'matches': False,
                    'details': match_details,
                    'error_code': RuleErrorCodes.TYPE_MISMATCH
                }
        
        # 2. 发送者类型匹配
        if 'sender_type' in conditions:
            expected_sender_type = conditions['sender_type']
            sender_type_match = sender_type == expected_sender_type
            match_details['sender_type'] = {
                'expected': expected_sender_type,
                'actual': sender_type,
                'matches': sender_type_match
            }
            if not sender_type_match:
                return {
                    'matches': False,
                    'details': match_details,
                    'error_code': RuleErrorCodes.SENDER_TYPE_MISMATCH
                }
        
        # 3. 特定发送者匹配
        if 'sender_id' in conditions:
            expected_sender_id = conditions['sender_id']
            sender_match = sender_id == expected_sender_id
            match_details['sender_id'] = {
                'expected': expected_sender_id,
                'actual': sender_id,
                'matches': sender_match
            }
            if not sender_match:
                return {
                    'matches': False,
                    'details': match_details,
                    'error_code': RuleErrorCodes.SENDER_MISMATCH
                }
        
        # 4. 关键词匹配
        if 'keywords' in conditions and conditions['keywords']:
            keywords = conditions['keywords']
            if not isinstance(keywords, list):
                keywords = [keywords]
                
            keyword_matches = []
            for keyword in keywords:
                found = keyword.lower() in content.lower()
                keyword_matches.append({
                    'keyword': keyword,
                    'found': found
                })
            
            # 根据匹配类型判断结果
            match_type = conditions.get('keyword_match_type', 'any')
            if match_type == 'all':
                keywords_match = all(item['found'] for item in keyword_matches)
            else:  # 默认为 'any'
                keywords_match = any(item['found'] for item in keyword_matches)
                
            match_details['keywords'] = {
                'match_type': match_type,
                'results': keyword_matches,
                'matches': keywords_match
            }
            
            if not keywords_match:
                return {
                    'matches': False,
                    'details': match_details,
                    'error_code': RuleErrorCodes.KEYWORD_MISMATCH
                }
        
        # 5. 正则表达式匹配
        if 'regex_pattern' in conditions and conditions['regex_pattern']:
            pattern = conditions['regex_pattern']
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                regex_match = bool(regex.search(content))
                match_details['regex'] = {
                    'pattern': pattern,
                    'matches': regex_match
                }
                if not regex_match:
                    return {
                        'matches': False,
                        'details': match_details,
                        'error_code': RuleErrorCodes.REGEX_MISMATCH
                    }
            except re.error as e:
                return {
                    'matches': False,
                    'error': f'正则表达式错误: {str(e)}',
                    'error_code': RuleErrorCodes.INVALID_REGEX
                }
        
        # 所有条件都匹配
        return {
            'matches': True,
            'details': match_details
        }
        
    except Exception as e:
        logger.error(f"规则匹配测试失败: {str(e)}", exc_info=True)
        return {
            'matches': False,
            'error': f'规则匹配测试失败: {str(e)}',
            'error_code': RuleErrorCodes.TEST_FAILED
        }

def apply_rule_transformations(rule, message_data, match_result):
    """
    应用规则定义的转换操作
    
    Args:
        rule: AgentListeningRule实例
        message_data: 原始消息数据
        match_result: 规则匹配的结果
    
    Returns:
        dict: 转换后的消息数据
    """
    try:
        # 如果不匹配则直接返回原消息
        if not match_result.get('matches', False):
            return message_data
            
        # 获取转换定义
        transformations = rule.transformations or {}
        
        # 克隆消息以避免修改原始数据
        transformed_message = message_data.copy()
        
        # 应用各种转换
        # 1. 修改消息类型
        if 'message_type' in transformations:
            transformed_message['type'] = transformations['message_type']
        
        # 2. 修改消息内容
        if 'content_template' in transformations:
            template = transformations['content_template']
            original_text = message_data.get('payload', {}).get('text', '')
            
            # 简单的模板替换
            # 支持 {original_text} 变量
            new_text = template.replace('{original_text}', original_text)
            
            # 更新消息内容
            if 'payload' not in transformed_message:
                transformed_message['payload'] = {}
            transformed_message['payload']['text'] = new_text
        
        # 3. 添加元数据
        if 'add_metadata' in transformations:
            metadata = transformations['add_metadata']
            if isinstance(metadata, dict):
                if 'metadata' not in transformed_message:
                    transformed_message['metadata'] = {}
                transformed_message['metadata'].update(metadata)
        
        # 返回转换后的消息
        return transformed_message
        
    except Exception as e:
        logger.error(f"应用规则转换失败: {str(e)}", exc_info=True)
        # 出错时返回原始消息
        return message_data 