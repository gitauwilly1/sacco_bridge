import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from apps.chatbot.models import (
    ChatSession, ChatMessage, SessionType, MessageRole
)
from apps.chatbot.services import GeminiService, KnowledgeService

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.room_group_name = f'chat_{self.user.id}'

        if self.session_id:
            self.room_group_name = f'chat_{self.user.id}_{self.session_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        session = await self.get_or_create_session()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': str(session.id) if session else None,
            'message': 'Connected to Sacco Bridge Assistant.',
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')

            if message_type == 'message':
                user_message = data.get('content', '').strip()
                if user_message:
                    await self.process_user_message(user_message)

            elif message_type == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'is_typing': data.get('is_typing', False),
                    }
                )

            elif message_type == 'feedback':
                await self.save_feedback(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format.',
            }))

    async def process_user_message(self, user_message):
        session = await self.get_or_create_session()
        if not session:
            return

        user_msg = await self.save_message(
            session, MessageRole.USER, user_message
        )

        await self.send(text_data=json.dumps({
            'type': 'message_saved',
            'message_id': str(user_msg.id),
        }))

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': True,
            }
        )

        history = await self.get_conversation_history(session)
        response = await self.generate_ai_response(session, user_message, history)

        assistant_msg = await self.save_message(
            session, MessageRole.ASSISTANT, response['response_text'],
            intent=response.get('intent', ''),
            confidence=response.get('confidence', 0.0),
            sources=response.get('sources', []),
            tokens_used=response.get('tokens_used', 0),
        )

        await self.update_session_tokens(session, response.get('tokens_used', 0))

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': False,
            }
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(assistant_msg.id),
                'content': response['response_text'],
                'role': 'ASSISTANT',
                'intent': response.get('intent', ''),
                'sources': response.get('sources', []),
                'timestamp': str(timezone.now()),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'content': event['content'],
            'role': event['role'],
            'intent': event.get('intent', ''),
            'sources': event.get('sources', []),
            'timestamp': event['timestamp'],
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
        }))

    @database_sync_to_async
    def get_or_create_session(self):
        if self.session_id:
            try:
                return ChatSession.objects.get(
                    id=self.session_id,
                    user=self.user,
                    is_active=True
                )
            except ChatSession.DoesNotExist:
                pass

        return ChatSession.objects.create(
            user=self.user,
            session_type=SessionType.GENERAL_SUPPORT,
            title='New Conversation',
        )

    @database_sync_to_async
    def save_message(self, session, role, content, intent='', confidence=0.0,
                     sources=None, tokens_used=0):
        return ChatMessage.objects.create(
            session=session,
            role=role,
            content=content,
            intent_detected=intent,
            confidence_score=confidence,
            sources=sources or [],
            tokens_used=tokens_used,
            ai_model=getattr(__import__('django.conf').settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        )

    @database_sync_to_async
    def get_conversation_history(self, session):
        messages = ChatMessage.objects.filter(
            session=session
        ).order_by('-created_at')[:10]

        return [
            {
                'role': msg.role,
                'content': msg.content,
            }
            for msg in reversed(messages)
        ]

    @database_sync_to_async
    def generate_ai_response(self, session, user_message, history):
        return GeminiService.generate_response(
            user_message, session, history
        )

    @database_sync_to_async
    def update_session_tokens(self, session, tokens):
        session.total_tokens_used += tokens
        session.save(update_fields=['total_tokens_used', 'updated_at'])

    @database_sync_to_async
    def save_feedback(self, data):
        try:
            session = ChatSession.objects.get(
                id=self.session_id,
                user=self.user
            )
            session.feedback_rating = data.get('rating')
            if data.get('resolved'):
                session.resolved = True
            session.save(update_fields=['feedback_rating', 'resolved'])
        except ChatSession.DoesNotExist:
            pass