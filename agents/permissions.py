from rest_framework import permissions
import logging

logger = logging.getLogger('agents')

class IsAgentOwnerOrAdmin(permissions.BasePermission):
    """
    仅允许Agent的所有者或管理员访问
    """
    
    def has_object_permission(self, request, view, obj):
        # 检查对象是否有owner属性
        if not hasattr(obj, 'owner'):
            return False
            
        # 读取请求始终允许
        if request.method in permissions.SAFE_METHODS:
            # 如果代理是公开的，允许任何已认证用户查看
            if getattr(obj, 'is_public', False):
                return True
            # 非公开代理只允许所有者或管理员查看
        
        # 检查用户是否是对象的所有者或管理员
        is_owner = obj.owner == request.user
        is_admin = request.user.is_staff
        
        if not (is_owner or is_admin):
            logger.warning(
                f"用户 {request.user.username} 尝试访问非自己拥有的代理 {obj}，访问被拒绝。"
            )
            
        return is_owner or is_admin


class IsPublicAgentOrOwnerOrAdmin(permissions.BasePermission):
    """
    允许查看公开Agent，但仅允许所有者或管理员修改Agent
    """
    
    def has_object_permission(self, request, view, obj):
        # 检查对象是否有owner和is_public属性
        if not (hasattr(obj, 'owner') and hasattr(obj, 'is_public')):
            return False
            
        # 如果是安全方法（GET等）且代理是公开的，允许访问
        if request.method in permissions.SAFE_METHODS and obj.is_public:
            return True
            
        # 其他情况，检查用户是否是所有者或管理员
        return obj.owner == request.user or request.user.is_staff 