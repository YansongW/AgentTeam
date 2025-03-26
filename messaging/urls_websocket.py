from django.urls import path
from .views import websocket_test

app_name = 'messaging'

urlpatterns = [
    path('', websocket_test, name='websocket_test'),
] 