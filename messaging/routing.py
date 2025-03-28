from django.urls import re_path
from . import consumers

# WebSocket URL patterns
websocket_urlpatterns = [
    re_path(r'ws/messaging/(?P<room_name>[^/]+)/$', consumers.MessageConsumer.as_asgi()),
] 