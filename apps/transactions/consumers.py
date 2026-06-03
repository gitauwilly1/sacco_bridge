import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class SettlementConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get('user')
        self.intent_id = self.scope['url_route']['kwargs'].get('intent_id')

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.room_group_name = f'settlement_{self.intent_id}'

        # Verify user is part of this settlement
        is_participant = await self.verify_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current settlement status on connect
        status_data = await self.get_settlement_status()
        await self.send(text_data=json.dumps({
            'type': 'settlement.status',
            'data': status_data,
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
            message_type = data.get('type', '')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': str(__import__('django.utils.timezone').now()),
                }))

        except json.JSONDecodeError:
            pass

    async def settlement_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'settlement.update',
            'data': {
                'intent_id': event.get('intent_id'),
                'from_state': event.get('from_state'),
                'to_state': event.get('to_state'),
                'state_display': event.get('state_display'),
                'timestamp': event.get('timestamp'),
                'message': event.get('message', ''),
            }
        }))

    @database_sync_to_async
    def verify_participant(self):
        from apps.transactions.models import SettlementIntent
        try:
            intent = SettlementIntent.objects.get(uuid=self.intent_id)
            return intent.buyer == self.user or intent.seller == self.user
        except SettlementIntent.DoesNotExist:
            return False

    @database_sync_to_async
    def get_settlement_status(self):
        from apps.transactions.models import SettlementIntent
        from apps.transactions.serializers import SettlementIntentSerializer
        try:
            intent = SettlementIntent.objects.get(uuid=self.intent_id)
            serializer = SettlementIntentSerializer(intent)
            return serializer.data
        except SettlementIntent.DoesNotExist:
            return {'error': 'Settlement not found'}