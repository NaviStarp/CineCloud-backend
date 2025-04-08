import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from cinecloud import routing  # Make sure this imports the file with websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinecloud.settings')  # Update project name if needed

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})