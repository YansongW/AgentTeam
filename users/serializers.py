from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
import logging
from django.core.exceptions import ValidationError
import re

# 获取用户模型
User = get_user_model()

# 创建日志记录器
logger = logging.getLogger(__name__)

class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    
    # 添加确认密码字段，仅用于验证
    password2 = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True,
        label=_('确认密码')
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
        }
    
    def validate_email(self, value):
        """验证邮箱唯一性"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("该邮箱已被注册"))
        return value
    
    def validate_username(self, value):
        """验证用户名唯一性"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("该用户名已被使用"))
        return value
    
    def validate(self, data):
        """验证两次密码是否一致"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': _("两次输入的密码不一致")})
        
        # 使用Django的密码验证器验证密码
        validate_password(data['password'])
        
        return data
    
    def create(self, validated_data):
        """创建新用户"""
        # 移除确认密码字段
        validated_data.pop('password2')
        
        # 创建未激活的用户
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False  # 用户需要通过邮箱验证才激活
        )
        
        logger.info(f"创建了新用户: {user.username} (ID: {user.id}) - 等待邮箱验证")
        
        return user

class EmailVerificationSerializer(serializers.Serializer):
    """邮箱验证序列化器"""
    token = serializers.CharField()

class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, attrs):
        """验证登录凭据"""
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')
        
        # 至少需要提供用户名或邮箱
        if not username and not email:
            raise serializers.ValidationError({
                'error': '必须提供用户名或邮箱'
            })
            
        return attrs

class TokenRefreshSerializer(serializers.Serializer):
    """令牌刷新序列化器"""
    refresh = serializers.CharField()
    
    def validate(self, attrs):
        refresh = attrs.get('refresh')
        
        if not refresh:
            raise serializers.ValidationError({
                'error': '必须提供刷新令牌'
            })
        
        return attrs 

class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined', 'last_login')
        read_only_fields = ('id', 'is_active', 'is_staff', 'date_joined', 'last_login')

class UserMinimalSerializer(serializers.ModelSerializer):
    """用户最小化序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id', 'email'] 