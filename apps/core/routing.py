from django.urls import re_path
from apps.transactions.consumers import SettlementConsumer
from apps.notifications.consumers import NotificationConsumer
from apps.chatbot.consumers import ChatConsumer

websocket_urlpatterns = [
    # Settlement real-time tracking
    re_path(
        r'ws/settlements/(?P<settlement_id>[0-9a-f-]+)/$',
        SettlementConsumer.as_asgi(),
    ),

    # Notification broadcasting
    re_path(
        r'ws/notifications/$',
        NotificationConsumer.as_asgi(),
    ),

    # AI Chatbot
    re_path(
        r'ws/chat/$',
        ChatConsumer.as_asgi(),
    ),
    re_path(
        r'ws/chat/(?P<session_id>[0-9a-f-]+)/$',
        ChatConsumer.as_asgi(),
    ),
]