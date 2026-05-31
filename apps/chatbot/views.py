from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext_lazy as _

from apps.chatbot.models import (
    ChatSession, ChatMessage, KnowledgeArticle,
    SessionType
)
from apps.chatbot.serializers import (
    ChatSessionSerializer, ChatMessageSerializer,
    KnowledgeArticleSerializer, ChatRequestSerializer,
)
from apps.chatbot.services import GeminiService, KnowledgeService
from apps.users.permissions import IsPlatformStaff


class ChatSessionViewSet(ModelViewSet):

    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(
            user=self.request.user,
            is_deleted=False
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        session = self.get_object()
        messages = session.messages.all().order_by('created_at')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        session = self.get_object()

        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_message = serializer.validated_data['message']

        ChatMessage.objects.create(
            session=session,
            role='USER',
            content=user_message,
            created_by=request.user,
        )

        history = list(
            ChatMessage.objects.filter(session=session)
            .order_by('-created_at')[:10]
            .values('role', 'content')
        )
        history.reverse()

        response = GeminiService.generate_response(user_message, session, history)

        assistant_msg = ChatMessage.objects.create(
            session=session,
            role='ASSISTANT',
            content=response['response_text'],
            intent_detected=response.get('intent', ''),
            confidence_score=response.get('confidence', 0.0),
            sources=response.get('sources', []),
            tokens_used=response.get('tokens_used', 0),
            ai_model='gemini-1.5-flash',
            created_by=request.user,
        )

        session.total_tokens_used += response.get('tokens_used', 0)
        session.save(update_fields=['total_tokens_used', 'updated_at'])

        return Response({
            'success': True,
            'data': {
                'user_message': ChatMessageSerializer(
                    ChatMessage.objects.filter(session=session, role='USER').latest('created_at')
                ).data,
                'assistant_message': ChatMessageSerializer(assistant_msg).data,
            }
        })


class KnowledgeArticleViewSet(ModelViewSet):

    serializer_class = KnowledgeArticleSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get_queryset(self):
        return KnowledgeArticle.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(
            authored_by=self.request.user,
            created_by=self.request.user,
        )


class ChatbotContextView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Chatbot'], summary='Update chat context')
    def post(self, request):
        session_id = request.data.get('session_id')
        context_data = request.data.get('context', {})

        try:
            session = ChatSession.objects.get(
                id=session_id, user=request.user, is_active=True
            )
            for key, value in context_data.items():
                session.add_context(key, value)

            return Response({
                'success': True,
                'data': ChatSessionSerializer(session).data,
                'message': _('Context updated.'),
            })

        except ChatSession.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Session not found.')}
            }, status=status.HTTP_404_NOT_FOUND)