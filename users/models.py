from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    自定义用户模型，扩展Django的AbstractUser模型
    
    字段说明:
    - email: 用户电子邮箱，设置为唯一
    - role: 用户角色，用于权限管理
    - bio: 用户简介，可选字段
    - avatar: 用户头像URL，可选字段
    - created_at: 用户创建时间，自动添加
    - updated_at: 用户信息更新时间，自动更新
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('管理员')
        USER = 'user', _('普通用户')
    
    # 邮箱设为唯一字段
    email = models.EmailField(_('电子邮箱'), unique=True)
    
    # 用户角色
    role = models.CharField(
        _('用户角色'),
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    
    # 用户简介
    bio = models.TextField(_('个人简介'), blank=True, null=True)
    
    # 用户头像
    avatar = models.URLField(_('头像URL'), blank=True, null=True)
    
    # 时间戳
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    # 第三方登录相关字段，预留
    google_id = models.CharField(max_length=100, blank=True, null=True)
    facebook_id = models.CharField(max_length=100, blank=True, null=True)
    
    # 必须设置EMAIL_FIELD指定email字段
    EMAIL_FIELD = "email"
    
    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        
    def __str__(self):
        return self.username
