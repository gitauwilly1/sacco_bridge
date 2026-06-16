import logging
from celery import shared_task
from django.utils import timezone
from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.notifications.tasks.deliver_push',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='push_notifications',
)
def deliver_push(self, notification_id, user_id):
    from apps.notifications.models import Notification, NotificationDelivery, DeliveryStatus, NotificationChannel, UserDevice
    from apps.notifications.services import FirebaseService

    try:
        notification = Notification.objects.get(id=notification_id)
        devices = UserDevice.objects.filter(user_id=user_id, is_active=True)

        if not devices.exists():
            logger.info(f"No active devices for user {user_id}")
            return {'status': 'skipped', 'reason': 'No active devices'}

        tokens = list(devices.values_list('firebase_token', flat=True))

        if len(tokens) == 1:
            result = FirebaseService.send_push_notification(
                tokens[0],
                notification.title,
                notification.body,
                data={
                    'notification_id': str(notification.id),
                    'category': notification.category,
                    'action_url': notification.action_url,
                }
            )
        else:
            result = FirebaseService.send_multicast(
                tokens,
                notification.title,
                notification.body,
                data={
                    'notification_id': str(notification.id),
                    'category': notification.category,
                    'action_url': notification.action_url,
                }
            )

        delivery, _ = NotificationDelivery.objects.get_or_create(
            notification=notification,
            channel=NotificationChannel.PUSH,
            defaults={'recipient': tokens[0], 'status': DeliveryStatus.PENDING}
        )

        if result.get('status') == 'sent' or result.get('success_count', 0) > 0:
            delivery.status = DeliveryStatus.SENT
            delivery.provider_message_id = result.get('message_id', '')
            delivery.sent_at = timezone.now()
            delivery.save()
            return {'status': 'sent'}
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = result.get('error', 'Unknown')
            delivery.save()
            raise self.retry(exc=Exception(result.get('error', 'Push failed')))

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'status': 'failed', 'reason': 'Notification not found'}
    except Exception as e:
        logger.error(f"Push delivery failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.notifications.tasks.deliver_sms',
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    queue='sms_notifications',
)
def deliver_sms(self, notification_id, user_id, phone_number):
    from apps.notifications.models import Notification, NotificationDelivery, DeliveryStatus, NotificationChannel
    from apps.notifications.services import SMSService

    try:
        notification = Notification.objects.get(id=notification_id)

        if not phone_number:
            logger.info(f"No phone number for user {user_id}")
            return {'status': 'skipped', 'reason': 'No phone number'}

        sms_body = notification.body[:160]
        result = SMSService.send_sms(phone_number, sms_body)

        delivery, _ = NotificationDelivery.objects.get_or_create(
            notification=notification,
            channel=NotificationChannel.SMS,
            defaults={'recipient': phone_number, 'status': DeliveryStatus.PENDING}
        )

        if result.get('status') == 'sent':
            delivery.status = DeliveryStatus.SENT
            delivery.provider_message_id = result.get('message_id', '')
            delivery.sent_at = timezone.now()
            delivery.provider_response = result
            delivery.save()
            return {'status': 'sent'}
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = result.get('error', 'Unknown')
            delivery.save()
            raise self.retry(exc=Exception(result.get('error', 'SMS failed')))

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'status': 'failed'}
    except Exception as e:
        logger.error(f"SMS delivery failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.notifications.tasks.deliver_email',
    bind=True,
    max_retries=3,
    default_retry_delay=180,
    queue='email_notifications',
)
def deliver_email(self, notification_id, user_id, email):
    from apps.notifications.models import Notification, NotificationDelivery, DeliveryStatus, NotificationChannel
    from apps.notifications.services import EmailService

    try:
        notification = Notification.objects.get(id=notification_id)

        if not email:
            logger.info(f"No email for user {user_id}")
            return {'status': 'skipped', 'reason': 'No email address'}

        result = EmailService.send_email(
            email,
            notification.title,
            notification.body,
        )

        delivery, _ = NotificationDelivery.objects.get_or_create(
            notification=notification,
            channel=NotificationChannel.EMAIL,
            defaults={'recipient': email, 'status': DeliveryStatus.PENDING}
        )

        if result.get('status') == 'sent':
            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = timezone.now()
            delivery.save()
            return {'status': 'sent'}
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = result.get('error', 'Unknown')
            delivery.save()
            raise self.retry(exc=Exception(result.get('error', 'Email failed')))

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'status': 'failed'}
    except Exception as e:
        logger.error(f"Email delivery failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.notifications.tasks.retry_failed_deliveries',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def retry_failed_deliveries(self):
    from apps.notifications.models import NotificationDelivery, DeliveryStatus

    MAX_RETRIES = 3
    BATCH_SIZE = 50

    failed = NotificationDelivery.objects.filter(
        status=DeliveryStatus.FAILED,
        retry_count__lt=MAX_RETRIES,
    )[:BATCH_SIZE]

    retried = 0
    for delivery in failed:
        try:
            delivery.retry_count += 1
            delivery.status = DeliveryStatus.PENDING
            delivery.save(update_fields=['retry_count', 'status'])

            notification = delivery.notification
            user = notification.user

            if delivery.channel == 'PUSH':
                deliver_push.delay(str(notification.id), str(user.id))
            elif delivery.channel == 'SMS':
                deliver_sms.delay(str(notification.id), str(user.id), user.phone_number)
            elif delivery.channel == 'EMAIL':
                deliver_email.delay(str(notification.id), str(user.id), user.email)

            retried += 1

        except Exception as e:
            logger.error(f"Retry failed for delivery {delivery.id}: {str(e)}")

    logger.info(f"Retried {retried} failed deliveries")
    return {'retried': retried}

@shared_task(
    name='apps.notifications.tasks.queue_notification',
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def queue_notification(self, user_id, category, title, body, priority='MEDIUM',
    template_name=None, action_url='', action_text='', data=None):
    from apps.users.models import User
    from apps.notifications.services import NotificationService
    from apps.notifications.models import NotificationPriority

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for notification")
        return {'error': 'User not found'}

    try:
        if template_name:
            NotificationService.create_from_template(
                user=user,
                template_name=template_name,
                context=data or {},
                action_url=action_url,
            )
        else:
            NotificationService.create_notification(
                user=user,
                category=category,
                title=title,
                body=body,
                priority=getattr(NotificationPriority, priority, NotificationPriority.MEDIUM),
                action_url=action_url,
                action_text=action_text,
                data=data,
            )
        return {'status': 'queued'}
    except Exception as e:
        logger.error(f"Failed to create notification for user {user_id}: {e}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.notifications.tasks.queue_bulk_notification',
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def queue_bulk_notification(self, user_ids, category, title, body, priority='MEDIUM',
    action_url='', action_text='', data=None):
    from apps.users.models import User
    from apps.notifications.models import NotificationPriority

    CHUNK_SIZE = 100
    processed = 0
    failed = 0

    for i in range(0, len(user_ids), CHUNK_SIZE):
        chunk = user_ids[i:i + CHUNK_SIZE]
        users = User.objects.filter(id__in=chunk, is_active=True)

        for user in users:
            try:
                NotificationService.create_notification(
                    user=user,
                    category=category,
                    title=title,
                    body=body,
                    priority=getattr(NotificationPriority, priority, NotificationPriority.MEDIUM),
                    action_url=action_url,
                    action_text=action_text,
                    data=data or {},
                )
                processed += 1
            except Exception as e:
                logger.error(f"Failed to notify user {user.id}: {e}")
                failed += 1

    logger.info(f"Bulk notification complete: {processed} sent, {failed} failed")
    return {'processed': processed, 'failed': failed}