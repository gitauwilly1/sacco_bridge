import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sacco_bridge.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.core.middleware import WebSocketAuthMiddleware
import apps.core.routing

# Build the WebSocket application with auth middleware first
websocket_application = WebSocketAuthMiddleware(
    URLRouter(
        apps.core.routing.websocket_urlpatterns
    )
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": websocket_application,
})