from django.urls import path

from core.realtime.consumers import PingConsumer

websocket_urlpatterns = [
    path("ws/ping/", PingConsumer.as_asgi()),
]
