"""
消息应用的信号处理器
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Message, MessageDeliveryStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def message_saved(sender, instance, created, **kwargs):
    """
    消息保存后的处理
    """
    try:
        if created:
            message_id = getattr(instance, 'message_id', str(instance.id))
            message_type = getattr(instance, 'message_type', 'unknown')
            logger.info(f"新消息已创建: {message_id} (类型: {message_type})")
    except Exception as e:
        logger.error(f"处理消息保存信号时出错: {str(e)}", exc_info=True)


@receiver(post_delete, sender=Message)
def message_deleted(sender, instance, **kwargs):
    """
    消息删除后的处理
    """
    try:
        message_id = getattr(instance, 'message_id', str(instance.id))
        logger.info(f"消息已删除: {message_id}")
    except Exception as e:
        logger.error(f"处理消息删除信号时出错: {str(e)}", exc_info=True)


@receiver(post_save, sender=MessageDeliveryStatus)
def delivery_status_saved(sender, instance, created, **kwargs):
    """
    消息传递状态保存后的处理
    """
    try:
        if created:
            logger.debug(f"新消息传递状态已创建: 消息ID {instance.message.id} -> 用户 {instance.user.username}")
        else:
            # 记录状态变化
            status_info = []
            if instance.is_delivered:
                status_info.append(f"已送达({instance.delivered_at})")
            if instance.is_read:
                status_info.append(f"已读({instance.read_at})")
                
            status_str = ", ".join(status_info) or "未知状态"
            logger.debug(f"消息传递状态已更新: 消息ID {instance.message.id} -> 用户 {instance.user.username}: {status_str}")
    except Exception as e:
        logger.error(f"处理消息传递状态保存信号时出错: {str(e)}", exc_info=True) 