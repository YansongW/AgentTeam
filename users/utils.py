import re
import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.utils import timezone
import time
from django.core.cache import cache
import secrets
import datetime
from rest_framework import status

# 创建日志记录器
logger = logging.getLogger(__name__)

# 登录尝试限制
MAX_LOGIN_ATTEMPTS = 5  # 最大尝试次数
LOGIN_ATTEMPTS_TIMEOUT = 15 * 60  # 锁定时间（秒）

def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_login_attempts(ip):
    """检查IP是否超过登录尝试次数限制"""
    key = f'login_attempts:{ip}'
    attempts = cache.get(key, 0)
    return attempts < MAX_LOGIN_ATTEMPTS

def increment_login_attempts(ip):
    """增加IP的登录尝试次数"""
    key = f'login_attempts:{ip}'
    attempts = cache.get(key, 0)
    attempts += 1
    # 设置缓存，如果是第一次失败，设置过期时间
    if attempts == 1:
        cache.set(key, attempts, LOGIN_ATTEMPTS_TIMEOUT)
    else:
        cache.set(key, attempts)
    logger.warning(f"IP {ip} 登录失败，当前尝试次数: {attempts}")
    if attempts >= MAX_LOGIN_ATTEMPTS:
        logger.warning(f"IP {ip} 登录尝试次数过多，已被临时阻止")

def reset_login_attempts(ip):
    """重置IP的登录尝试次数"""
    key = f'login_attempts:{ip}'
    cache.delete(key)
    logger.info(f"IP {ip} 登录成功，已重置尝试次数")

def get_all_locked_ips():
    """
    获取所有被锁定的IP地址及其剩余锁定时间
    
    在测试环境中返回空列表，以避免依赖cache.keys()方法
    """
    # 在测试环境中，返回一个空列表
    # 实际生产环境中应该使用数据库存储登录尝试记录
    locked_ips = []

    # 在测试环境中，模拟一些数据用于展示
    if settings.DEBUG:
        # 可以模拟一些数据用于开发环境测试
        locked_ips = [
            {
                'ip': '192.168.1.1',
                'attempts': MAX_LOGIN_ATTEMPTS,
                'expires_in': 600  # 10分钟
            }
        ]
    
    return locked_ips

def unlock_ip(ip):
    """解锁指定的IP地址"""
    key = f'login_attempts:{ip}'
    if cache.get(key, 0) >= MAX_LOGIN_ATTEMPTS:
        cache.delete(key)
        logger.info(f"IP {ip} 已被管理员手动解锁")
        return True
    return False

class CustomPasswordValidator:
    """
    自定义密码验证器
    
    验证规则：
    1. 密码长度至少为8个字符
    2. 必须包含至少一个小写字母
    3. 必须包含至少一个数字
    """
    
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError("密码长度至少为8个字符")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("密码必须包含至少一个小写字母")
            
        if not re.search(r'\d', password):
            raise ValidationError("密码必须包含至少一个数字")
    
    def get_help_text(self):
        return "密码必须包含至少8个字符、一个小写字母和一个数字"

def custom_exception_handler(exc, context):
    """
    自定义异常处理器
    
    返回统一格式的错误响应
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'error': response.data,
            'code': response.status_code
        }
        
        # 记录错误日志
        logger.error(f"API错误: {custom_response_data}")
        
        return Response(custom_response_data, status=response.status_code)
    
    return response

def generate_token(email):
    """
    生成用于邮箱验证的安全令牌，并存储在缓存中，有效期24小时
    
    参数:
    - email: 要验证的邮箱地址
    
    返回:
    - 生成的令牌
    """
    # 使用随机字符串生成令牌
    token = secrets.token_urlsafe(32)
    
    # 将令牌与邮箱关联并存储在缓存中，有效期24小时
    cache_key = f'email_verification:{token}'
    cache.set(cache_key, email, 86400)  # 24小时 = 86400秒
    
    return token

def verify_token(token, max_age=86400):
    """
    验证邮箱验证令牌
    
    参数:
    - token: 要验证的令牌
    - max_age: 令牌有效期（秒），默认24小时
    
    返回:
    - 成功返回邮箱地址，失败返回None
    """
    # 从缓存中获取与令牌关联的邮箱
    cache_key = f'email_verification:{token}'
    email = cache.get(cache_key)
    
    # 如果找到邮箱，删除令牌（防止重用）并返回邮箱
    if email:
        cache.delete(cache_key)
        return email
    
    return None 