"""
群组应用的信号处理器
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Group, GroupMember

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Group)
def group_saved(sender, instance, created, **kwargs):
    """
    群组保存后的处理
    """
    try:
        if created:
            logger.info(f"新群组已创建: {instance.name} (ID: {instance.id})")
        else:
            logger.info(f"群组已更新: {instance.name} (ID: {instance.id})")
            
    except Exception as e:
        logger.error(f"处理群组保存信号时出错: {str(e)}", exc_info=True)


@receiver(post_delete, sender=Group)
def group_deleted(sender, instance, **kwargs):
    """
    群组删除后的处理
    """
    try:
        logger.info(f"群组已删除: {instance.name} (ID: {instance.id})")
    except Exception as e:
        logger.error(f"处理群组删除信号时出错: {str(e)}", exc_info=True)


@receiver(post_save, sender=GroupMember)
def member_saved(sender, instance, created, **kwargs):
    """
    群组成员保存后的处理
    """
    try:
        group_name = instance.group.name
        
        if instance.user:
            member_name = instance.user.username
        else:
            member_name = instance.agent.name if hasattr(instance, 'agent') and instance.agent else "未知成员"
            
        if created:
            logger.info(f"成员 {member_name} 已加入群组 {group_name} (角色: {instance.role})")
        else:
            logger.info(f"群组 {group_name} 的成员 {member_name} 信息已更新")
            
    except Exception as e:
        logger.error(f"处理群组成员保存信号时出错: {str(e)}", exc_info=True)


@receiver(post_delete, sender=GroupMember)
def member_deleted(sender, instance, **kwargs):
    """
    群组成员删除后的处理
    """
    try:
        group_name = instance.group.name
        
        if instance.user:
            member_name = instance.user.username
        else:
            member_name = instance.agent.name if hasattr(instance, 'agent') and instance.agent else "未知成员"
            
        logger.info(f"成员 {member_name} 已离开群组 {group_name}")
    except Exception as e:
        logger.error(f"处理群组成员删除信号时出错: {str(e)}", exc_info=True) 