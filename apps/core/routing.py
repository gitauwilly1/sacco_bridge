from django.urls import re_path
from apps.chatbot.consumers import ChatConsumer
from apps.transactions.consumers import SettlementConsumer
from apps.notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    # Chat - AI assistant
    re_path(r'^ws/chat/$', ChatConsumer.as_asgi()),
    re_path(r'^ws/chat/(?P<session_id>[^/]+)/$', ChatConsumer.as_asgi()),

    # Settlement tracking - live status updates
    re_path(r'^ws/settlements/(?P<intent_id>[^/]+)/$', SettlementConsumer.as_asgi()),

    # Notifications - real-time push
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]