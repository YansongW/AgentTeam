import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import models
from rest_framework import status, permissions, serializers, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    UserRegistrationSerializer, EmailVerificationSerializer, 
    UserSerializer, UserLoginSerializer
)
from .utils import (
    generate_token, verify_token, check_login_attempts, 
    increment_login_attempts, reset_login_attempts, get_client_ip,
    get_all_locked_ips, unlock_ip, MAX_LOGIN_ATTEMPTS, LOGIN_ATTEMPTS_TIMEOUT
)
from .permissions import IsOwnerOrAdmin, IsAdminUser, ReadOnly

# 获取User模型
User = get_user_model()

# 创建日志记录器
logger = logging.getLogger(__name__)

class UserRegistrationView(generics.CreateAPIView):
    """
    用户注册视图
    
    处理用户注册请求、创建新用户并发送验证邮件
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="用户注册API",
        responses={
            201: openapi.Response(
                description="注册成功，验证邮件已发送",
                examples={
                    'application/json': {
                        'message': '注册成功，请查收验证邮件激活账号',
                        'username': 'testuser'
                    }
                }
            ),
            400: openapi.Response(
                description="注册失败",
                examples={
                    'application/json': {
                        'error': {'field': ['错误描述']},
                        'code': 400
                    }
                }
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """处理用户注册请求"""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(f"用户注册失败: {serializer.errors}")
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 创建用户但不激活
        user = serializer.save()
        
        try:
            # 生成验证令牌
            token = generate_token(user.email)
            
            # 构建验证URL
            verification_url = f"{request.build_absolute_uri('/')[:-1]}/api/users/verify-email/{token}/"
            
            # 发送验证邮件
            self.send_verification_email(user, verification_url)
            
            logger.info(f"用户 {user.username} 注册成功，验证邮件已发送到 {user.email}")
            
            return Response({
                'message': '注册成功，请查收验证邮件激活账号',
                'username': user.username
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # 发送失败，回滚用户创建
            user.delete()
            logger.error(f"发送验证邮件失败，用户注册回滚: {str(e)}")
            
            return Response({
                'error': '注册过程中发生错误，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def send_verification_email(self, user, verification_url):
        """
        发送验证邮件
        
        参数:
        - user: 用户实例
        - verification_url: 验证链接URL
        """
        subject = 'Chatbot平台 - 账号激活'
        
        # 使用HTML模板
        html_message = render_to_string('email/email_verification.html', {
            'user': user,
            'verification_url': verification_url
        })
        
        # 提取纯文本内容
        plain_message = strip_tags(html_message)
        
        # 发送邮件
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message
        )
        
        logger.info(f"验证邮件已发送到 {user.email}")

class EmailVerificationView(APIView):
    """
    邮箱验证视图
    
    验证用户注册时发送的邮箱验证链接
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="验证邮箱",
        manual_parameters=[
            openapi.Parameter(
                name='token',
                in_=openapi.IN_PATH,
                description="验证令牌",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="验证成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="验证失败",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
        }
    )
    def get(self, request, token):
        """
        验证邮箱 - 通过令牌查找并激活用户
        """
        email = verify_token(token)
        
        if not email:
            return Response(
                {'error': '验证链接无效或已过期'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 查找对应的用户
            user = User.objects.get(email=email)
                
            # 判断用户是否已激活
            if user.is_active:
                return Response({'message': '您的账号已经激活，无需重复验证'}, status=status.HTTP_200_OK)
                
            # 激活用户
            user.is_active = True
            user.save()
            
            logger.info(f"用户 {user.username} 完成邮箱验证，账号已激活")
            
            return Response({'message': '邮箱验证成功，账号已激活'}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            logger.warning(f"邮箱验证失败，未找到对应邮箱 {email} 的用户")
            return Response(
                {'error': '未找到对应的用户账号'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class UserLoginView(APIView):
    """
    用户登录API
    
    提供用户登录功能，成功后返回JWT令牌
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="用户登录",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description="用户名或邮箱"),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description="密码"),
            }
        ),
        responses={
            200: openapi.Response(
                description="登录成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description="访问令牌"),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description="刷新令牌"),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            }
                        )
                    }
                )
            ),
            401: openapi.Response(
                description="登录失败",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            429: openapi.Response(
                description="登录尝试次数过多",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request):
        # 获取客户端IP
        ip = get_client_ip(request)
        
        # 检查登录尝试次数
        if not check_login_attempts(ip):
            logger.warning(f"IP {ip} 登录尝试次数过多，请求被拒绝")
            return Response(
                {'error': '登录尝试次数过多，请稍后再试'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # 验证登录数据
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            # 增加登录失败计数
            increment_login_attempts(ip)
            return Response(
                {'error': '请提供有效的登录信息'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        username = serializer.validated_data.get('username')
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        
        # 根据用户名或邮箱查找用户
        if username:
            user = User.objects.filter(username=username).first()
        elif email:
            user = User.objects.filter(email=email).first()
        else:
            # 增加登录失败计数
            increment_login_attempts(ip)
            return Response(
                {'error': '请提供用户名或邮箱'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 用户不存在或密码错误
        if not user or not user.check_password(password):
            # 增加登录失败计数
            increment_login_attempts(ip)
            logger.warning(f"登录失败，无效的凭据: {username or email}")
            return Response(
                {'error': '用户名/邮箱或密码不正确'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # 检查用户是否激活
        if not user.is_active:
            # 增加登录失败计数
            increment_login_attempts(ip)
            logger.warning(f"非激活用户尝试登录: {user.username}")
            return Response(
                {'error': '您的账户尚未激活，请查收邮件完成验证'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # 登录成功，重置尝试次数
        reset_login_attempts(ip)
        
        # 生成令牌
        refresh = RefreshToken.for_user(user)
        
        # 记录登录成功
        logger.info(f"用户登录成功: {user.username}")
        
        # 返回令牌和用户信息
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_staff': user.is_staff,
            }
        })

class UserProfileView(APIView):
    """
    用户个人资料视图
    
    允许用户查看和更新自己的个人资料
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    @swagger_auto_schema(
        operation_description="获取用户个人资料",
        responses={
            200: openapi.Response(
                description="获取成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                        'role': openapi.Schema(type=openapi.TYPE_STRING),
                        'bio': openapi.Schema(type=openapi.TYPE_STRING),
                        'avatar': openapi.Schema(type=openapi.TYPE_STRING),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            ),
            404: openapi.Response(description="用户不存在")
        }
    )
    def get(self, request, user_id):
        """获取用户个人资料"""
        try:
            user = get_object_or_404(User, id=user_id)
            
            # 检查权限由DRF框架自动处理
            self.check_object_permissions(request, user)
            
            # 记录日志
            logger.info(f"用户 {request.user.username} 查看了用户 {user.username} 的个人资料")
            
            # 返回用户资料
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'bio': user.bio,
                'avatar': user.avatar,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
            })
            
        except permissions.exceptions.PermissionDenied as e:
            # 权限被拒绝，返回403
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"获取用户资料时出错: {str(e)}")
            return Response(
                {'error': '获取用户资料时发生错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_description="更新用户个人资料",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'bio': openapi.Schema(type=openapi.TYPE_STRING),
                'avatar': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(description="更新成功"),
            400: openapi.Response(description="请求数据无效"),
            404: openapi.Response(description="用户不存在")
        }
    )
    def patch(self, request, user_id):
        """更新用户个人资料"""
        try:
            user = get_object_or_404(User, id=user_id)
            
            # 检查权限
            self.check_object_permissions(request, user)
            
            # 获取要更新的字段
            updateable_fields = ['first_name', 'last_name', 'bio', 'avatar']
            update_data = {}
            
            for field in updateable_fields:
                if field in request.data:
                    update_data[field] = request.data[field]
                    
            if not update_data:
                return Response(
                    {'error': '没有提供有效的更新字段'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # 更新用户资料
            for key, value in update_data.items():
                setattr(user, key, value)
                
            user.save()
            
            # 记录日志
            logger.info(f"用户 {request.user.username} 更新了个人资料: {update_data}")
            
            return Response({
                'message': '个人资料更新成功',
                'updated_fields': list(update_data.keys())
            })
            
        except Exception as e:
            logger.error(f"更新用户资料时出错: {str(e)}")
            return Response(
                {'error': '更新用户资料时发生错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserManagementView(APIView):
    """
    用户管理视图
    
    允许管理员查看和管理所有用户
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="获取用户列表",
        manual_parameters=[
            openapi.Parameter(
                'page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'size', openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'search', openapi.IN_QUERY, description="搜索关键词", type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="获取成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                                    'role': openapi.Schema(type=openapi.TYPE_STRING),
                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                }
                            )
                        ),
                        'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'size': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            )
        }
    )
    def get(self, request):
        """获取用户列表，支持分页和搜索"""
        # 获取查询参数
        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 10))
        search = request.query_params.get('search', '')
        
        # 计算分页偏移量
        offset = (page - 1) * size
        limit = offset + size
        
        # 构建查询
        query = User.objects.all()
        
        # 如果有搜索关键词，过滤结果
        if search:
            query = query.filter(
                models.Q(username__icontains=search) | 
                models.Q(email__icontains=search)
            )
            
        # 计算总数和总页数
        total_count = query.count()
        total_pages = (total_count + size - 1) // size  # 向上取整
        
        # 获取当前页的数据
        users = query[offset:limit]
        
        # 构建响应数据
        results = []
        for user in users:
            results.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
            })
            
        # 记录日志
        logger.info(f"管理员 {request.user.username} 查看了用户列表")
        
        return Response({
            'count': total_count,
            'results': results,
            'page': page,
            'size': size,
            'total_pages': total_pages,
        })
    
    @swagger_auto_schema(
        operation_description="更新用户状态",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'is_active'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={
            200: openapi.Response(description="更新成功"),
            400: openapi.Response(description="请求数据无效"),
            404: openapi.Response(description="用户不存在")
        }
    )
    def post(self, request):
        """更新用户状态（激活/禁用）"""
        user_id = request.data.get('user_id')
        is_active = request.data.get('is_active')
        
        # 验证参数
        if user_id is None or is_active is None:
            return Response(
                {'error': '必须提供user_id和is_active参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取要更新的用户
            target_user = User.objects.get(id=user_id)
            
            # 防止管理员禁用自己的账户
            if target_user.id == request.user.id:
                logger.warning(f"管理员 {request.user.username} 尝试修改自己的账户状态")
                return Response(
                    {'error': '不能修改自己的账户状态'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # 更新用户状态
            target_user.is_active = is_active
            target_user.save()
            
            # 记录日志
            action = "激活" if is_active else "禁用"
            logger.info(f"管理员 {request.user.username} {action}了用户 {target_user.username}")
            
            return Response({
                'message': f'已成功{action}用户 {target_user.username}'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"更新用户状态时出错: {str(e)}")
            return Response(
                {'error': '更新用户状态时发生错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_description="更新用户角色",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'role'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'role': openapi.Schema(type=openapi.TYPE_STRING, enum=['admin', 'user']),
            }
        ),
        responses={
            200: openapi.Response(description="更新成功"),
            400: openapi.Response(description="请求数据无效"),
            404: openapi.Response(description="用户不存在")
        }
    )
    def put(self, request):
        """更新用户角色"""
        user_id = request.data.get('user_id')
        role = request.data.get('role')
        
        # 验证参数
        if user_id is None or role is None:
            return Response(
                {'error': '必须提供user_id和role参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 验证角色值
        valid_roles = [r[0] for r in User.Role.choices]
        if role not in valid_roles:
            return Response(
                {'error': f'无效的角色值，可选值: {", ".join(valid_roles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取要更新的用户
            target_user = User.objects.get(id=user_id)
            
            # 防止管理员降级自己的权限
            if target_user.id == request.user.id and role != 'admin':
                logger.warning(f"管理员 {request.user.username} 尝试降级自己的权限")
                return Response(
                    {'error': '不能降级自己的管理员权限'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # 更新用户角色
            target_user.role = role
            target_user.save()
            
            # 记录日志
            logger.info(f"管理员 {request.user.username} 将用户 {target_user.username} 的角色更新为 {role}")
            
            return Response({
                'message': f'已成功将用户 {target_user.username} 的角色更新为 {role}'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"更新用户角色时出错: {str(e)}")
            return Response(
                {'error': '更新用户角色时发生错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordChangeView(APIView):
    """
    密码修改视图
    
    允许用户修改自己的密码
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="修改密码",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['current_password', 'new_password', 'confirm_password'],
            properties={
                'current_password': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(description="密码修改成功"),
            400: openapi.Response(description="请求数据无效")
        }
    )
    def post(self, request):
        """修改用户密码"""
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        # 验证所有必填字段
        if not all([current_password, new_password, confirm_password]):
            return Response(
                {'error': '所有密码字段都必须填写'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 验证当前密码是否正确
        if not request.user.check_password(current_password):
            logger.warning(f"用户 {request.user.username} 提供了错误的当前密码")
            return Response(
                {'error': '当前密码不正确'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 验证两次输入的新密码是否一致
        if new_password != confirm_password:
            return Response(
                {'error': '两次输入的新密码不一致'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 验证新密码是否与当前密码相同
        if current_password == new_password:
            return Response(
                {'error': '新密码不能与当前密码相同'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 使用Django密码验证器验证新密码
        try:
            validate_password(new_password, request.user)
        except ValidationError as e:
            return Response(
                {'error': e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 更新密码
        request.user.set_password(new_password)
        request.user.save()
        
        # 记录日志
        logger.info(f"用户 {request.user.username} 成功修改了密码")
        
        return Response({
            'message': '密码修改成功，请使用新密码重新登录'
        })

class LoginAttemptsView(APIView):
    """
    登录尝试管理视图
    
    允许管理员查看和解锁被限制的IP地址
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="获取所有被限制的IP地址",
        responses={
            200: openapi.Response(
                description="获取成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'locked_ips': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'ip': openapi.Schema(type=openapi.TYPE_STRING),
                                    'attempts': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'expires_in': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        """获取所有被限制的IP地址"""
        # 获取锁定的IP列表
        locked_ips = get_all_locked_ips()
        
        # 记录日志
        logger.info(f"管理员 {request.user.username} 查看了被锁定的IP列表")
        
        return Response({
            'locked_ips': locked_ips,
            'total': len(locked_ips),
            'threshold': MAX_LOGIN_ATTEMPTS,
            'lock_duration': f"{LOGIN_ATTEMPTS_TIMEOUT // 60} 分钟"
        })
    
    @swagger_auto_schema(
        operation_description="解锁指定IP地址",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['ip'],
            properties={
                'ip': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(description="解锁成功"),
            400: openapi.Response(description="请求数据无效")
        }
    )
    def post(self, request):
        """解锁指定IP地址"""
        ip = request.data.get('ip')
        
        if not ip:
            return Response(
                {'error': '必须提供要解锁的IP地址'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 尝试解锁IP
        success = unlock_ip(ip)
        
        if success:
            # 记录日志
            logger.info(f"管理员 {request.user.username} 解锁了IP: {ip}")
            
            return Response({
                'message': f'已成功解锁IP: {ip}'
            })
        else:
            return Response(
                {'error': f'IP {ip} 未被锁定或解锁失败'},
                status=status.HTTP_400_BAD_REQUEST
            )
