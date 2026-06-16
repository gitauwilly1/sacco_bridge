import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.room_group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        unread_count = await self.get_unread_count(self.user.id)
        await self.send(text_data=json.dumps({
            'type': 'notification.count',
            'unread_count': unread_count,
        }))

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
        except Exception:
            pass

        if close_code != 1000:
            logger.warning(
                f"WebSocket abnormal disconnect: code={close_code}, "
                f"user_id={getattr(self, 'user', 'unknown')}"
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')

            if message_type == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_as_read(notification_id)

            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                }))

        except json.JSONDecodeError:
            pass

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification.new',
            'data': event.get('data', {}),
        }))

    async def notification_count(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification.count',
            'unread_count': event.get('unread_count', 0),
        }))

    async def mark_as_read(self, notification_id):
        from channels.db import database_sync_to_async

        from apps.notifications.models import Notification

        @database_sync_to_async
        def _mark(uid, nid):
            try:
                notif = Notification.objects.get(id=nid, user_id=uid)
                notif.mark_as_read()
                return True
            except Notification.DoesNotExist:
                return False

        await _mark(self.user.id, notification_id)

    @staticmethod
    async def get_unread_count(user_id):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _count(uid):
            from apps.notifications.models import Notification
            return Notification.objects.filter(
                user_id=uid, is_read=False
            ).count()

        return await _count(user_id)