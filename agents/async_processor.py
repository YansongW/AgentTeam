import asyncio
import logging
import json
import threading
from typing import Dict, List, Any, Optional, Callable
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .services import RuleEngine

logger = logging.getLogger(__name__)

class AsyncMessageProcessor:
    """
    异步消息处理器
    
    负责异步处理消息并发送代理响应
    """
    
    def __init__(self):
        """初始化消息处理器"""
        self.queue = asyncio.Queue()
        self.channel_layer = get_channel_layer()
        self.running = False
        self.worker_thread = None
        self.handlers = {}  # 注册的处理函数
        
    def start(self):
        """启动消息处理器"""
        if self.running:
            logger.warning("消息处理器已经在运行")
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._run_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("异步消息处理器已启动")
        
    def stop(self):
        """停止消息处理器"""
        if not self.running:
            return
            
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
            self.worker_thread = None
        logger.info("异步消息处理器已停止")
        
    def _run_worker(self):
        """运行工作线程"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._process_queue())
        except Exception as e:
            logger.error(f"消息处理器异常: {str(e)}", exc_info=True)
        finally:
            loop.close()
            
    async def _process_queue(self):
        """处理消息队列"""
        while self.running:
            try:
                # 从队列获取消息，超时1秒
                message, context, callback = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                try:
                    # 处理消息
                    responses = RuleEngine.process_message(message, context)
                    
                    # 如果有回调函数，调用它
                    if callback:
                        callback(responses)
                        
                    # 发送响应
                    for response in responses:
                        await self._send_response(response, context)
                        
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
                    
                finally:
                    # 标记任务完成
                    self.queue.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"消息队列处理异常: {str(e)}", exc_info=True)
                
    async def _send_response(self, response, context):
        """发送响应"""
        try:
            # 如果上下文中有WebSocket组，则通过WebSocket发送响应
            if 'group_id' in context:
                group_id = str(context['group_id'])
                
                # 构建通知消息
                message = {
                    'type': 'agent.message',
                    'message': response
                }
                
                # 发送到群组
                await self.channel_layer.group_send(
                    f"group_{group_id}",
                    message
                )
                
                logger.debug(f"已发送代理响应到群组 {group_id}")
                
            # 调用注册的处理函数
            handler_type = response.get('type', '')
            if handler_type in self.handlers:
                await self.handlers[handler_type](response, context)
                
        except Exception as e:
            logger.error(f"发送响应时出错: {str(e)}", exc_info=True)
            
    def add_message(self, message: Dict, context: Dict = None, callback: Callable = None):
        """
        添加消息到处理队列
        
        参数:
        - message: 消息内容
        - context: 上下文信息
        - callback: 处理完成后的回调函数
        """
        if context is None:
            context = {}
            
        # 确保异步队列可用
        if not self.running:
            self.start()
            
        # 在同步环境中调用异步方法
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.queue.put((message, context, callback)))
        finally:
            loop.close()
            
    def register_handler(self, response_type: str, handler: Callable):
        """
        注册响应处理函数
        
        参数:
        - response_type: 响应类型
        - handler: 处理函数，必须是一个async函数
        """
        self.handlers[response_type] = handler
        
# 全局实例
message_processor = AsyncMessageProcessor()

# 应用启动时初始化
def init_async_processor():
    """初始化异步处理器"""
    message_processor.start()
    logger.info("异步消息处理器已初始化") 