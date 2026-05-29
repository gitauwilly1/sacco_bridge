from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.chatbot.views import (
    ChatSessionViewSet, KnowledgeArticleViewSet,
    ChatbotContextView,
)

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='chat-session')
router.register(r'knowledge', KnowledgeArticleViewSet, basename='knowledge-article')

urlpatterns = [
    path('', include(router.urls)),
    path('context/', ChatbotContextView.as_view(), name='chat-context'),
]