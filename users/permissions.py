from rest_framework import permissions
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class IsAdminUser(permissions.BasePermission):
    """
    仅允许管理员用户访问
    """
    message = _('此操作需要管理员权限')
    
    def has_permission(self, request, view):
        # 检查用户是否已认证且角色为管理员
        is_admin = request.user.is_authenticated and request.user.role == 'admin'
        
        if not is_admin:
            logger.warning(
                f'用户 {request.user.username if request.user.is_authenticated else "未认证用户"} '
                f'尝试访问仅限管理员的资源: {request.path}'
            )
            
        return is_admin

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    对象级权限，仅允许对象的所有者或管理员访问
    """
    message = _('您只能操作自己的资源')
    
    def has_object_permission(self, request, view, obj):
        # 管理员有全部权限
        if request.user.role == 'admin':
            return True
            
        # 检查对象是否属于当前用户
        is_owner = obj.id == request.user.id if hasattr(obj, 'id') else False
        
        if not is_owner:
            logger.warning(
                f'用户 {request.user.username} 尝试访问不属于自己的资源: {obj}'
            )
            
        return is_owner
        
class ReadOnly(permissions.BasePermission):
    """
    仅允许GET、HEAD、OPTIONS请求
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS 