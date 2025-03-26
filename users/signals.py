"""
用户应用的信号处理器
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def user_saved(sender, instance, created, **kwargs):
    """
    用户保存后的处理
    """
    try:
        if created:
            logger.info(f"新用户已创建: {instance.username} (ID: {instance.id})")
        else:
            logger.info(f"用户已更新: {instance.username} (ID: {instance.id})")
            
        # 如果用户被禁用，记录日志
        if not instance.is_active:
            logger.warning(f"用户已被禁用: {instance.username} (ID: {instance.id})")
            
    except Exception as e:
        logger.error(f"处理用户保存信号时出错: {str(e)}", exc_info=True)


@receiver(post_delete, sender=User)
def user_deleted(sender, instance, **kwargs):
    """
    用户删除后的处理
    """
    try:
        logger.info(f"用户已删除: {instance.username} (ID: {instance.id})")
    except Exception as e:
        logger.error(f"处理用户删除信号时出错: {str(e)}", exc_info=True) 