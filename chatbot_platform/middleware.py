"""
异常处理中间件
捕获所有请求过程中的异常并进行处理
"""

import json
import traceback
from django.http import JsonResponse, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

from chatbot_platform.error_utils import ErrorUtils
from chatbot_platform.error_codes import SystemErrorCodes


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    错误处理中间件
    捕获并处理请求过程中的所有异常
    """
    
    def process_exception(self, request, exception):
        """
        处理请求过程中的异常
        
        参数:
            request: HTTP请求对象
            exception: 捕获到的异常
            
        返回:
            HttpResponse: 错误响应
        """
        # 仅处理API请求
        if not request.path.startswith('/api/'):
            return None
            
        # 如果是API请求，构建错误响应
        error_message = str(exception)
        stack_trace = traceback.format_exc()
        
        # 根据异常类型设置不同的错误代码和状态码
        error_code = SystemErrorCodes.INTERNAL_ERROR
        status_code = 500
        user_message = "处理请求时发生错误"
        
        # 示例：根据异常类型设置不同的错误代码
        exception_name = exception.__class__.__name__
        if exception_name == 'ValidationError':
            error_code = SystemErrorCodes.INTERNAL_ERROR
            status_code = 400
            user_message = "请求数据验证失败"
        elif exception_name == 'PermissionDenied':
            error_code = SystemErrorCodes.INTERNAL_ERROR
            status_code = 403
            user_message = "权限不足，无法执行请求"
        elif exception_name == 'NotFound':
            error_code = SystemErrorCodes.INTERNAL_ERROR
            status_code = 404
            user_message = "请求的资源不存在"
        
        # 记录错误日志
        ErrorUtils.log_error(
            error_code=error_code,
            message=error_message,
            exception=exception,
            level='error',
            extra_data={
                'request_path': request.path,
                'request_method': request.method,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                'stack_trace': stack_trace,
            }
        )
        
        # 构建错误响应
        response_data = {
            'error': {
                'code': error_code,
                'message': user_message,
            }
        }
        
        # 在开发环境中，添加更多错误详情
        if settings.DEBUG:
            response_data['error']['details'] = {
                'exception': error_message,
                'type': exception.__class__.__name__,
                'traceback': stack_trace.split('\n')
            }
        
        # 返回JSON错误响应
        return JsonResponse(response_data, status=status_code)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    请求日志中间件
    记录所有API请求的日志
    """
    
    def process_request(self, request):
        """处理请求，记录请求信息"""
        # 仅记录API请求
        if not request.path.startswith('/api/'):
            return None
            
        import logging
        logger = logging.getLogger('django.request')
        
        # 记录请求信息
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'data': {
                    'method': request.method,
                    'path': request.path,
                    'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                    'ip': request.META.get('REMOTE_ADDR'),
                    'params': dict(request.GET),
                }
            }
        )
        
        return None
    
    def process_response(self, request, response):
        """处理响应，记录响应信息"""
        # 仅记录API请求
        if not request.path.startswith('/api/'):
            return response
            
        import logging
        logger = logging.getLogger('django.request')
        
        # 尝试解析响应内容（如果是JSON）
        response_content = None
        if hasattr(response, 'content'):
            try:
                if isinstance(response.content, bytes):
                    content_str = response.content.decode('utf-8')
                else:
                    content_str = response.content
                    
                response_content = json.loads(content_str)
            except (json.JSONDecodeError, UnicodeDecodeError):
                response_content = "无法解析的响应内容"
        
        # 记录响应信息
        logger.info(
            f"Response: {response.status_code} {request.method} {request.path}",
            extra={
                'data': {
                    'status_code': response.status_code,
                    'method': request.method,
                    'path': request.path,
                    'content_type': response.get('Content-Type', None),
                    'content_length': len(response.content) if hasattr(response, 'content') else 0,
                }
            }
        )
        
        return response 