import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.notifications.tasks.retry_failed_deliveries',
    bind=True,
    max_retries=3,
    default_retry_delay=600,
)
def retry_failed_deliveries(self):
    logger.info("Starting notification delivery retry...")

    from apps.notifications.models import NotificationDelivery, DeliveryStatus
    from apps.notifications.services import NotificationService

    try:
        MAX_RETRIES = 3
        BATCH_SIZE = 50

        failed_deliveries = NotificationDelivery.objects.filter(
            status=DeliveryStatus.FAILED,
            retry_count__lt=MAX_RETRIES,
        )[:BATCH_SIZE]

        retried_count = 0
        permanent_failures = 0

        for delivery in failed_deliveries:
            try:
                delivery.retry_count += 1
                delivery.status = DeliveryStatus.PENDING
                delivery.save(update_fields=['retry_count', 'status'])

                success = NotificationService._deliver_channel(
                    delivery.notification,
                    delivery.channel,
                    delivery.notification.user,
                )

                if success:
                    retried_count += 1
                else:
                    if delivery.retry_count >= MAX_RETRIES:
                        permanent_failures += 1
                        logger.warning(
                            f"Permanent delivery failure for "
                            f"notification {delivery.notification.id} "
                            f"via {delivery.channel}"
                        )

            except Exception as e:
                logger.error(
                    f"Error retrying delivery {delivery.id}: {str(e)}"
                )

        logger.info(
            f"Notification retry complete: "
            f"{retried_count} retried, {permanent_failures} permanent failures"
        )

        return {
            'retried': retried_count,
            'permanent_failures': permanent_failures,
        }

    except Exception as e:
        logger.error(f"Notification retry failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.notifications.tasks.send_bulk_notification',
    bind=True,
)
def send_bulk_notification(self, user_ids, category, title, body, action_url='', data=None):
    from apps.users.models import User
    from apps.notifications.services import NotificationService

    logger.info(f"Sending bulk notification to {len(user_ids)} users...")

    sent_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id, is_active=True)
            NotificationService.create_notification(
                user=user,
                category=category,
                title=title,
                body=body,
                action_url=action_url,
                data=data or {},
            )
            sent_count += 1
        except User.DoesNotExist:
            failed_count += 1
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {str(e)}")
            failed_count += 1

    logger.info(f"Bulk notification complete: {sent_count} sent, {failed_count} failed")

    return {'sent': sent_count, 'failed': failed_count}