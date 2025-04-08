# cinecloud/routing.py

from django.urls import re_path
from . import consumers  # Aquí traes el consumer desde cinecloud.consumers
# Define las rutas de WebSocket directamente aquí
websocket_urlpatterns = [
    re_path(r'ws/progress/(?P<user_id>\w+)/$', consumers.ProgressConsumer.as_asgi()),
]
