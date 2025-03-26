from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)

class IsGroupOwnerOrAdmin(permissions.BasePermission):
    """
    检查用户是否是群组的所有者或管理员
    """
    message = "您不是群组的所有者或管理员，无权执行此操作。"
    
    def has_object_permission(self, request, view, obj):
        # 管理员用户拥有所有权限
        if request.user.is_staff:
            return True
            
        # 检查是否是群组所有者
        if hasattr(obj, 'owner'):
            is_owner = obj.owner == request.user
            if is_owner:
                return True
        elif hasattr(obj, 'group') and hasattr(obj.group, 'owner'):
            is_owner = obj.group.owner == request.user
            if is_owner:
                return True
                
        # 检查是否是群组管理员
        from .models import GroupMember
        if hasattr(obj, 'id'):
            is_admin = GroupMember.objects.filter(
                group=obj, 
                user=request.user, 
                role=GroupMember.Role.ADMIN,
                is_active=True
            ).exists()
            return is_admin
        elif hasattr(obj, 'group') and hasattr(obj.group, 'id'):
            is_admin = GroupMember.objects.filter(
                group=obj.group, 
                user=request.user, 
                role=GroupMember.Role.ADMIN,
                is_active=True
            ).exists()
            return is_admin
            
        return False


class IsGroupMember(permissions.BasePermission):
    """
    检查用户是否是群组的成员
    """
    message = "您不是群组的成员，无权执行此操作。"
    
    def has_object_permission(self, request, view, obj):
        # 管理员用户拥有所有权限
        if request.user.is_staff:
            return True
            
        # 检查是否是群组所有者
        if hasattr(obj, 'owner'):
            is_owner = obj.owner == request.user
            if is_owner:
                return True
        elif hasattr(obj, 'group') and hasattr(obj.group, 'owner'):
            is_owner = obj.group.owner == request.user
            if is_owner:
                return True
                
        # 检查是否是群组成员
        from .models import GroupMember
        if hasattr(obj, 'id'):
            is_member = GroupMember.objects.filter(
                group=obj, 
                user=request.user,
                is_active=True
            ).exists()
            if not is_member:
                logger.warning(f"用户 {request.user.username} 尝试访问非自己所在的群组 {obj.name}，访问被拒绝。")
            return is_member
        elif hasattr(obj, 'group') and hasattr(obj.group, 'id'):
            is_member = GroupMember.objects.filter(
                group=obj.group, 
                user=request.user,
                is_active=True
            ).exists()
            if not is_member:
                logger.warning(f"用户 {request.user.username} 尝试访问非自己所在的群组 {obj.group.name} 中的资源，访问被拒绝。")
            return is_member
            
        return False


class IsMessageSender(permissions.BasePermission):
    """
    检查用户是否是消息的发送者
    """
    message = "您不是该消息的发送者，无权执行此操作。"
    
    def has_object_permission(self, request, view, obj):
        # 管理员用户拥有所有权限
        if request.user.is_staff:
            return True
            
        # 群组所有者和管理员有权限
        if hasattr(obj, 'group') and hasattr(obj.group, 'owner'):
            is_owner = obj.group.owner == request.user
            if is_owner:
                return True
                
            from .models import GroupMember
            is_admin = GroupMember.objects.filter(
                group=obj.group, 
                user=request.user, 
                role=GroupMember.Role.ADMIN,
                is_active=True
            ).exists()
            if is_admin:
                return True
                
        # 检查是否是消息发送者
        if hasattr(obj, 'sender_user'):
            is_sender = obj.sender_user == request.user
            if not is_sender:
                logger.warning(f"用户 {request.user.username} 尝试修改非自己发送的消息，访问被拒绝。")
            return is_sender
            
        return False


class CanJoinPublicGroup(permissions.BasePermission):
    """
    检查用户是否可以加入公开群组
    """
    message = "您无法加入此群组，可能是因为该群组不是公开的或已达到成员上限。"
    
    def has_object_permission(self, request, view, obj):
        # 管理员用户拥有所有权限
        if request.user.is_staff:
            return True
            
        # 群组所有者可以管理成员
        if hasattr(obj, 'owner'):
            is_owner = obj.owner == request.user
            if is_owner:
                return True
                
        # 检查群组是否公开
        if hasattr(obj, 'is_public'):
            is_public = obj.is_public
            
            # 如果不是公开群组，则需要群组邀请才能加入
            if not is_public:
                logger.warning(f"用户 {request.user.username} 尝试加入非公开群组 {obj.name}，访问被拒绝。")
                return False
                
            # 检查是否已经是成员
            from .models import GroupMember
            is_member = GroupMember.objects.filter(
                group=obj, 
                user=request.user,
                is_active=True
            ).exists()
            
            if is_member:
                return False  # 已经是成员，不能重复加入
                
            # 可以考虑检查成员数量是否达到上限
            member_count = obj.get_member_count()
            max_members = obj.group_settings.get('max_members', 100)  # 默认最大100人
            
            if member_count >= max_members:
                logger.warning(f"用户 {request.user.username} 尝试加入已满员的群组 {obj.name}，访问被拒绝。")
                return False
                
            return True
            
        return False 