"""
错误处理工具
提供统一的错误记录和响应格式
"""

import logging
import traceback
import json
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status

# 获取logger实例
logger = logging.getLogger(__name__)


class ErrorUtils:
    """错误处理工具类"""
    
    # 存储应用错误代码类的映射
    _app_error_codes = {}
    
    @classmethod
    def register_app_error_codes(cls, app_name, error_codes_class):
        """
        注册应用的错误代码类
        
        参数:
            app_name (str): 应用名称
            error_codes_class (class): 错误代码类
        """
        cls._app_error_codes[app_name] = error_codes_class
    
    @classmethod
    def get_app_error_codes(cls, app_name):
        """
        获取应用的错误代码类
        
        参数:
            app_name (str): 应用名称
            
        返回:
            class: 错误代码类
        """
        return cls._app_error_codes.get(app_name)
    
    @staticmethod
    def log_error(error_code, message, exception=None, level='error', extra_data=None):
        """
        记录错误日志
        
        参数:
            error_code (str): 错误代码，如USR_AUTH_001
            message (str): 错误消息
            exception (Exception, optional): 异常对象
            level (str): 日志级别 (debug, info, warning, error, critical)
            extra_data (dict, optional): 额外的日志数据
        """
        log_data = {
            'error_code': error_code,
            'message': message,
        }
        
        # 添加异常信息（如果有）
        if exception:
            log_data['exception'] = str(exception)
            log_data['traceback'] = traceback.format_exc()
        
        # 添加额外数据
        if extra_data and isinstance(extra_data, dict):
            log_data.update(extra_data)
        
        # 选择日志级别
        log_method = getattr(logger, level.lower(), logger.error)
        
        # 记录日志
        log_method(f"[{error_code}] {message}", extra={'data': log_data})
    
    @staticmethod
    def format_error_response(error_code, message, details=None, http_status=status.HTTP_400_BAD_REQUEST):
        """
        格式化错误响应
        
        参数:
            error_code (str): 错误代码，如USR_AUTH_001
            message (str): 用户友好的错误消息
            details (dict, optional): 错误详情
            http_status (int): HTTP状态码
        
        返回:
            rest_framework.response.Response: 格式化的错误响应
        """
        response_data = {
            'error': {
                'code': error_code,
                'message': message,
            }
        }
        
        if details:
            response_data['error']['details'] = details
        
        return Response(response_data, status=http_status)
    
    @staticmethod
    def handle_exception(request, exception, error_code, default_message="发生错误，请稍后再试", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR):
        """
        处理异常并返回错误响应
        
        参数:
            request: 当前请求
            exception: 异常对象
            error_code (str): 错误代码
            default_message (str): 默认错误消息
            http_status (int): HTTP状态码
        
        返回:
            rest_framework.response.Response: 错误响应
        """
        # 获取异常信息
        error_message = str(exception) or default_message
        
        # 记录错误日志
        ErrorUtils.log_error(
            error_code, 
            error_message, 
            exception=exception, 
            level='error', 
            extra_data={
                'request_path': request.path,
                'request_method': request.method,
                'user_id': getattr(request.user, 'id', None),
            }
        )
        
        # 返回错误响应
        return ErrorUtils.format_error_response(
            error_code=error_code,
            message=default_message,  # 用户友好的消息
            details={'detail': error_message} if error_message != default_message else None,
            http_status=http_status
        )


# 用于WebSocket错误的处理函数
def format_websocket_error(error_code, message, details=None):
    """
    格式化WebSocket错误消息
    
    参数:
        error_code (str): 错误代码
        message (str): 错误消息
        details (dict, optional): 错误详情
    
    返回:
        dict: 格式化的错误消息
    """
    error_data = {
        'message_type': 'error',
        'error': {
            'code': error_code,
            'message': message
        }
    }
    
    if details:
        error_data['error']['details'] = details
        
    return error_data


# DRF异常处理器
def custom_exception_handler(exc, context):
    """
    DRF自定义异常处理器
    
    参数:
        exc: 异常
        context: 上下文
    
    返回:
        Response: 统一格式的错误响应
    """
    from chatbot_platform.error_codes import SystemErrorCodes
    
    # 获取请求
    request = context.get('request')
    
    # 如果是DRF的异常，尝试获取其详情
    if hasattr(exc, 'get_full_details'):
        details = exc.get_full_details()
    else:
        details = {'detail': str(exc)}
    
    # 记录错误
    ErrorUtils.log_error(
        SystemErrorCodes.INTERNAL_ERROR,
        f"API异常: {exc.__class__.__name__}",
        exception=exc,
        extra_data={
            'request_path': request.path if request else None,
            'details': details
        }
    )
    
    # 返回统一格式的错误响应
    return ErrorUtils.format_error_response(
        error_code=SystemErrorCodes.INTERNAL_ERROR, 
        message="处理请求时发生错误", 
        details=details,
        http_status=getattr(exc, 'status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
    ) 