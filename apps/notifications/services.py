import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.models import (
    Notification, NotificationDelivery, NotificationTemplate,
    NotificationChannel, NotificationCategory, NotificationPriority,
    DeliveryStatus, UserDevice, NotificationPreference
)

logger = logging.getLogger(__name__)


class FirebaseService:

    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        try:
            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info("Firebase Admin SDK initialized successfully.")
            else:
                logger.warning("Firebase credentials path not configured.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")

    @classmethod
    def send_push_notification(cls, device_token, title, body, data=None, image_url=None):
        cls.initialize()

        if not cls._initialized:
            return {'status': 'failed', 'error': 'Firebase not initialized'}

        try:
            message = messaging.Message(
                token=device_token,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url if image_url else None,
                ),
                data={k: str(v) for k, v in (data or {}).items()},
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='sacco_bridge_default',
                        color='#C67B5C',
                        icon='notification_icon',
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                            content_available=True,
                        ),
                    ),
                ),
            )

            response = messaging.send(message)
            logger.info(f"Push notification sent: {response}")
            return {'status': 'sent', 'message_id': response}

        except messaging.UnregisteredError:
            UserDevice.objects.filter(firebase_token=device_token).update(
                is_active=False
            )
            logger.warning(f"Device token unregistered: {device_token}")
            return {'status': 'failed', 'error': 'Device unregistered'}

        except Exception as e:
            logger.error(f"Failed to send push notification: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    @classmethod
    def send_multicast(cls, device_tokens, title, body, data=None):
        cls.initialize()

        if not cls._initialized:
            return {'success_count': 0, 'failure_count': len(device_tokens), 'responses': []}

        try:
            message = messaging.MulticastMessage(
                tokens=device_tokens,
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
            )

            response = messaging.send_each_for_multicast(message)
            success_count = response.success_count
            failure_count = response.failure_count

            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    if isinstance(resp.exception, messaging.UnregisteredError):
                        UserDevice.objects.filter(
                            firebase_token=device_tokens[idx]
                        ).update(is_active=False)

            logger.info(
                f"Multicast sent: {success_count} success, {failure_count} failure"
            )

            return {
                'success_count': success_count,
                'failure_count': failure_count,
                'responses': response.responses,
            }

        except Exception as e:
            logger.error(f"Multicast push failed: {str(e)}")
            return {
                'success_count': 0,
                'failure_count': len(device_tokens),
                'error': str(e)
            }


class SMSService:

    @classmethod
    def send_sms(cls, phone_number, message):
        try:
            import africastalking

            username = settings.AFRICASTALKING_USERNAME
            api_key = settings.AFRICASTALKING_API_KEY

            africastalking.initialize(username, api_key)
            sms = africastalking.SMS

            response = sms.send(
                message,
                [phone_number],
                settings.AFRICASTALKING_SENDER_ID if hasattr(settings, 'AFRICASTALKING_SENDER_ID') else None
            )

            logger.info(f"SMS sent to {phone_number}: {response}")

            if response.get('SMSMessageData', {}).get('Recipients'):
                recipient = response['SMSMessageData']['Recipients'][0]
                return {
                    'status': 'sent' if recipient['status'] == 'Success' else 'failed',
                    'message_id': recipient.get('messageId', ''),
                    'cost': recipient.get('cost', ''),
                }

            return {'status': 'failed', 'error': 'No recipient data in response'}

        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return {'status': 'failed', 'error': str(e)}


class EmailService:

    @classmethod
    def send_email(cls, recipient_email, subject, html_body, plain_text=''):
        try:
            send_mail(
                subject=subject,
                message=plain_text or 'Please view this email in HTML format.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_body,
                fail_silently=False,
            )

            logger.info(f"Email sent to {recipient_email}: {subject}")
            return {'status': 'sent'}

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return {'status': 'failed', 'error': str(e)}


class NotificationService:

    @classmethod
    def create_notification(
        cls,
        user,
        category,
        title,
        body,
        priority=NotificationPriority.MEDIUM,
        template=None,
        action_url='',
        action_text='',
        data=None,
        channels=None,
    ):
        notification = Notification.objects.create(
            user=user,
            template=template,
            category=category,
            priority=priority,
            title=title,
            body=body,
            action_url=action_url,
            action_text=action_text,
            data=data or {},
            channels_sent=[],
        )

        if channels is None:
            channels = cls._get_user_channels(user, category)

        sent_channels = []

        for channel in channels:
            success = cls._deliver_channel(notification, channel, user)
            if success:
                sent_channels.append(channel)

        if sent_channels:
            notification.channels_sent = sent_channels
            notification.save(update_fields=['channels_sent'])

        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{user.id}',
                    {
                        'type': 'notification.message',
                        'data': {
                            'id': str(notification.id),
                            'title': notification.title,
                            'body': notification.body,
                            'category': notification.category,
                            'action_url': notification.action_url,
                            'created_at': str(notification.created_at),
                        }
                    }
                )
        except Exception as e:
            logger.warning(f"WebSocket notification push failed: {e}")


        logger.info(
            f"Notification {notification.id} created for user {user.email} "
            f"via channels: {sent_channels}"
        )

        return notification

    @classmethod
    def create_from_template(cls, user, template_name, context, action_url='', data=None):
        try:
            template = NotificationTemplate.objects.get(
                name=template_name, is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Notification template not found: {template_name}")
            return None

        language = user.preferred_language if hasattr(user, 'preferred_language') else 'en'
        rendered = template.render(context, language=language)

        return cls.create_notification(
            user=user,
            category=template.category,
            title=rendered['title'],
            body=rendered['body'],
            priority=template.default_priority,
            template=template,
            action_url=action_url,
            data=data,
        )
    @classmethod
    def _get_user_channels(cls, user, category):
        channels = [NotificationChannel.IN_APP]

        try:
            pref = NotificationPreference.objects.get(
                user=user, category=category
            )

            if pref.push_enabled and not cls._is_quiet_hours(pref):
                channels.append(NotificationChannel.PUSH)

            if pref.sms_enabled:
                channels.append(NotificationChannel.SMS)

            if pref.email_enabled:
                channels.append(NotificationChannel.EMAIL)

        except NotificationPreference.DoesNotExist:
            channels.extend([
                NotificationChannel.PUSH,
                NotificationChannel.SMS,
                NotificationChannel.EMAIL,
            ])

        return channels

    @classmethod
    def _is_quiet_hours(cls, preference):
        if not preference.quiet_hours_start or not preference.quiet_hours_end:
            return False

        now = timezone.localtime().time()
        start = preference.quiet_hours_start
        end = preference.quiet_hours_end

        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    @classmethod
    def _deliver_channel(cls, notification, channel, user):
        # Idempotency check
        existing = NotificationDelivery.objects.filter(
            notification=notification,
            channel=channel,
        ).first()

        if existing and existing.status == DeliveryStatus.DELIVERED:
            logger.info(
                f"Notification {notification.id} already delivered via {channel}. Skipping."
            )
            return True

        if existing and existing.status == DeliveryStatus.SENT:
            logger.info(
                f"Notification {notification.id} already sent via {channel}."
            )
            return True

        if existing:
            logger.info(
                f"Notification {notification.id} has pending delivery via {channel}."
            )
            return False

        delivery = NotificationDelivery.objects.create(
            notification=notification,
            channel=channel,
            recipient=cls._get_recipient(user, channel),
            status=DeliveryStatus.PENDING,
            idempotency_key=f"{notification.id}:{channel}",
        )

        # Dispatch to per-channel Celery task
        from apps.notifications.tasks import (
            deliver_push, deliver_sms, deliver_email, deliver_in_app
        )

        if channel == NotificationChannel.IN_APP:
            deliver_in_app.delay(delivery.id)
            return True

        elif channel == NotificationChannel.PUSH:
            deliver_push.delay(delivery.id)
            return True

        elif channel == NotificationChannel.SMS:
            deliver_sms.delay(delivery.id)
            return True

        elif channel == NotificationChannel.EMAIL:
            deliver_email.delay(delivery.id)
            return True

        return False
    
    @classmethod
    def _get_recipient(cls, user, channel):
        if channel == NotificationChannel.EMAIL:
            return user.email
        elif channel == NotificationChannel.SMS:
            return user.phone_number
        elif channel == NotificationChannel.PUSH:
            devices = UserDevice.objects.filter(user=user, is_active=True)
            return devices.first().firebase_token if devices.exists() else ''
        return ''

    @classmethod
    def mark_all_read(cls, user):
        Notification.objects.filter(
            user=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())

    @classmethod
    def get_unread_count(cls, user):
        return Notification.objects.filter(
            user=user, is_read=False
        ).count()