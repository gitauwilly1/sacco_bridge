import logging
import json
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import firebase_admin
from firebase_admin import credentials, messaging

from apps.notifications.models import (
    Notification, NotificationPreference, NotificationTemplate, UserDevice,
    NotificationChannel, NotificationStatus, NotificationCategory,
    NotificationPriority, DevicePlatform
)

logger = logging.getLogger(__name__)


class FirebaseService:

    _initialized = False

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            try:
                cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                if cred_path:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
                cls._initialized = True
                logger.info("Firebase Admin SDK initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {str(e)}")
                raise

    @classmethod
    def send_push_notification(cls, user, title, body, data=None, action_url=''):
        cls.initialize()

        devices = UserDevice.objects.filter(
            user=user,
            is_active=True
        )

        if not devices.exists():
            logger.info(f"No active devices for user {user.email}")
            return 0, 0, []

        success_count = 0
        failure_count = 0
        message_ids = []

        for device in devices:
            try:
                message = messaging.Message(
                    token=device.fcm_token,
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data or {},
                    android=messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            channel_id='sacco_bridge_default',
                            click_action=action_url or 'FLUTTER_NOTIFICATION_CLICK',
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                alert=messaging.ApsAlert(
                                    title=title,
                                    body=body,
                                ),
                                sound='default',
                                badge=1,
                            ),
                        ),
                    ),
                )

                response = messaging.send(message)
                message_ids.append(response)
                success_count += 1
                logger.info(f"Push notification sent to {user.email}: {response}")

            except messaging.UnregisteredError:
                device.is_active = False
                device.save()
                failure_count += 1
                logger.warning(f"Device token unregistered for {user.email}")

            except Exception as e:
                failure_count += 1
                logger.error(f"Failed to send push to {user.email}: {str(e)}")

        return success_count, failure_count, message_ids

    @classmethod
    def send_multicast(cls, users, title, body, data=None):
        cls.initialize()

        total_success = 0
        total_failure = 0

        for user in users:
            success, failure, _ = cls.send_push_notification(
                user, title, body, data
            )
            total_success += success
            total_failure += failure

        return total_success, total_failure

    @classmethod
    def register_device(cls, user, fcm_token, platform, device_name='', device_model='', app_version=''):
        device, created = UserDevice.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={
                'user': user,
                'platform': platform,
                'device_name': device_name,
                'device_model': device_model,
                'app_version': app_version,
                'is_active': True,
            }
        )

        if created:
            logger.info(f"New device registered for {user.email}: {device_name}")
        else:
            logger.info(f"Device updated for {user.email}: {device_name}")

        return device

    @classmethod
    def unregister_device(cls, fcm_token):
        UserDevice.objects.filter(fcm_token=fcm_token).update(is_active=False)
        logger.info(f"Device unregistered: {fcm_token}")


class SMSService:

    @classmethod
    def send_sms(cls, phone_number, message):
        try:
            import africastalking
            africastalking.initialize(
                settings.AFRICASTALKING_USERNAME,
                settings.AFRICASTALKING_API_KEY
            )

            sms = africastalking.SMS

            response = sms.send(
                message=message,
                recipients=[phone_number],
                sender_id='SACCO_BRIDGE'
            )

            logger.info(f"SMS sent to {phone_number}: {response}")

            return {
                'status': 'SUCCESS',
                'message_id': str(response.get('SMSMessageData', {}).get('Recipients', [{}])[0].get('messageId', '')),
            }

        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return {
                'status': 'FAILED',
                'error': str(e),
            }

    @classmethod
    def format_kenyan_number(cls, phone_number):
        import re
        cleaned = re.sub(r'\s+', '', phone_number)

        if cleaned.startswith('0'):
            return '+254' + cleaned[1:]
        elif cleaned.startswith('254'):
            return '+' + cleaned
        elif cleaned.startswith('+254'):
            return cleaned
        elif cleaned.startswith('7'):
            return '+254' + cleaned

        return cleaned


class EmailService:

    @classmethod
    def send_email(cls, recipient_email, subject, html_body, text_body=''):
        try:
            send_mail(
                subject=subject,
                message=text_body or subject,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_body,
                fail_silently=False,
            )
            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

    @classmethod
    def send_templated_email(cls, recipient_email, template_name, context):
        try:
            html_body = render_to_string(template_name, context)
            subject = context.get('subject', 'Sacco Bridge Notification')

            return cls.send_email(recipient_email, subject, html_body)

        except Exception as e:
            logger.error(f"Failed to send templated email: {str(e)}")
            return False


class NotificationService:

    @classmethod
    def send_notification(
        cls,
        user,
        category,
        title,
        body,
        channels=None,
        priority=NotificationPriority.MEDIUM,
        data=None,
        action_url='',
        reference_id='',
        reference_type='',
        short_message='',
        email_subject='',
        email_body='',
    ):
        if channels is None:
            channels = [
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.SMS,
                NotificationChannel.EMAIL,
            ]

        # Check user preferences for each channel
        enabled_channels = cls._filter_by_preferences(user, category, channels)

        if not enabled_channels:
            logger.info(f"All channels disabled for user {user.email}, category {category}")
            return None

        # Create the notification record
        notification = Notification.objects.create(
            user=user,
            category=category,
            priority=priority,
            title=title,
            body=body,
            short_message=short_message or body[:160],
            channel=enabled_channels[0],
            action_url=action_url,
            data=data or {},
            reference_id=reference_id,
            reference_type=reference_type,
        )

        # Deliver through each enabled channel
        for channel in enabled_channels:
            cls._deliver_to_channel(
                notification, channel, user, title, body,
                short_message, email_subject, email_body,
                data, action_url
            )

        return notification

    @classmethod
    def send_from_template(cls, user, template_name, context, channels=None):
        try:
            template = NotificationTemplate.objects.get(
                name=template_name,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Notification template not found: {template_name}")
            return None

        rendered = template.render(context)

        if channels is None:
            channels = template.default_channels

        return cls.send_notification(
            user=user,
            category=template.category,
            title=rendered['title'],
            body=rendered['body'],
            channels=channels,
            priority=template.default_priority,
            action_url=rendered.get('action_url', ''),
            reference_id=context.get('reference_id', ''),
            reference_type=context.get('reference_type', ''),
            short_message=rendered.get('sms', ''),
            email_subject=rendered.get('email_subject', ''),
            email_body=rendered.get('email_body', ''),
            data=context.get('data', {}),
        )

    @classmethod
    def send_bulk_from_template(cls, users, template_name, context, channels=None):
        notifications = []

        for user in users:
            user_context = context.copy()
            user_context['user_name'] = user.get_full_name()
            user_context['user_email'] = user.email

            notification = cls.send_from_template(
                user, template_name, user_context, channels
            )
            if notification:
                notifications.append(notification)

        return notifications

    @classmethod
    def _filter_by_preferences(cls, user, category, channels):
        preferences = NotificationPreference.objects.filter(
            user=user,
            category=category
        ).values('channel', 'enabled')

        pref_map = {p['channel']: p['enabled'] for p in preferences}

        enabled_channels = []
        for channel in channels:
            if channel == NotificationChannel.IN_APP:
                enabled_channels.append(channel)
            elif pref_map.get(channel, True):
                enabled_channels.append(channel)

        return enabled_channels

    @classmethod
    def _deliver_to_channel(
        cls, notification, channel, user, title, body,
        short_message, email_subject, email_body, data, action_url
    ):
        if channel == NotificationChannel.PUSH:
            success, failure, msg_ids = FirebaseService.send_push_notification(
                user, title, body, data, action_url
            )
            if success > 0:
                notification.mark_as_sent(msg_ids[0] if msg_ids else '')
            elif failure > 0:
                notification.mark_as_failed('No active devices or delivery failed')

        elif channel == NotificationChannel.SMS:
            phone = SMSService.format_kenyan_number(user.phone_number)
            result = SMSService.send_sms(phone, short_message or body[:160])
            if result['status'] == 'SUCCESS':
                notification.mark_as_sent(result.get('message_id', ''))
            else:
                notification.mark_as_failed(result.get('error', 'SMS delivery failed'))

        elif channel == NotificationChannel.EMAIL:
            subject = email_subject or title
            html_body = email_body or f"<p>{body}</p>"
            success = EmailService.send_email(user.email, subject, html_body)
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed('Email delivery failed')

        elif channel == NotificationChannel.IN_APP:
            notification.mark_as_sent()

    @classmethod
    def mark_all_read(cls, user):
        updated = Notification.objects.filter(
            user=user,
            status__in=[NotificationStatus.SENT, NotificationStatus.DELIVERED]
        ).update(
            status=NotificationStatus.READ,
            read_at=timezone.now()
        )
        return updated

    @classmethod
    def get_unread_count(cls, user):
        return Notification.objects.filter(
            user=user,
            status__in=[NotificationStatus.SENT, NotificationStatus.DELIVERED]
        ).count()