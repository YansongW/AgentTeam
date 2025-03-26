"""
代理应用的信号处理器
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Agent, AgentListeningRule

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Agent)
def agent_saved(sender, instance, created, **kwargs):
    """
    代理保存后的处理
    """
    try:
        if created:
            logger.info(f"新代理已创建: {instance.name} (ID: {instance.id})")
        else:
            logger.info(f"代理已更新: {instance.name} (ID: {instance.id})")
            
        # 如果代理被禁用，记录日志
        if instance.status == 'disabled':
            logger.warning(f"代理已被禁用: {instance.name} (ID: {instance.id})")
            
    except Exception as e:
        logger.error(f"处理代理保存信号时出错: {str(e)}", exc_info=True)


@receiver(post_delete, sender=Agent)
def agent_deleted(sender, instance, **kwargs):
    """
    代理删除后的处理
    """
    try:
        logger.info(f"代理已删除: {instance.name} (ID: {instance.id})")
    except Exception as e:
        logger.error(f"处理代理删除信号时出错: {str(e)}", exc_info=True)


@receiver(post_save, sender=AgentListeningRule)
def rule_saved(sender, instance, created, **kwargs):
    """
    监听规则保存后的处理
    """
    try:
        if created:
            logger.info(f"新监听规则已创建: {instance.name} (ID: {instance.id})")
        else:
            logger.info(f"监听规则已更新: {instance.name} (ID: {instance.id})")
            
        # 如果规则被禁用，记录日志
        if not instance.is_active:
            logger.warning(f"监听规则已被禁用: {instance.name} (ID: {instance.id})")
            
    except Exception as e:
        logger.error(f"处理监听规则保存信号时出错: {str(e)}", exc_info=True)


@receiver(post_delete, sender=AgentListeningRule)
def rule_deleted(sender, instance, **kwargs):
    """
    监听规则删除后的处理
    """
    try:
        logger.info(f"监听规则已删除: {instance.name} (ID: {instance.id})")
    except Exception as e:
        logger.error(f"处理监听规则删除信号时出错: {str(e)}", exc_info=True) 