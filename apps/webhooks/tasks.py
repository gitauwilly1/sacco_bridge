import hmac
import hashlib
import json
import logging
import requests
from django.utils import timezone
from celery import shared_task

from apps.webhooks.models import WebhookSubscription, WebhookDelivery

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.webhooks.tasks.deliver_webhook',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deliver_webhook(self, delivery_id):
    try:
        delivery = WebhookDelivery.objects.get(id=delivery_id)
    except WebhookDelivery.DoesNotExist:
        return {'error': 'Delivery not found'}

    subscription = delivery.subscription

    if not subscription.is_active:
        return {'error': 'Subscription inactive'}

    delivery.status = 'RETRYING'
    delivery.attempt_count += 1
    delivery.save()

    try:
        # Generate HMAC signature
        payload_str = json.dumps(delivery.payload)
        signature = hmac.new(
            subscription.secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = requests.post(
            subscription.url,
            json=delivery.payload,
            headers={
                'Content-Type': 'application/json',
                'X-SaccoBridge-Event': delivery.event_type,
                'X-SaccoBridge-Signature': signature,
                'X-SaccoBridge-Delivery-ID': str(delivery.id),
                'User-Agent': 'SaccoBridge-Webhook/1.0',
            },
            timeout=10,
        )

        delivery.response_code = response.status_code
        delivery.response_body = response.text[:500]

        if 200 <= response.status_code < 300:
            delivery.status = 'SUCCESS'
            delivery.completed_at = timezone.now()
            delivery.save()

            subscription.last_delivery_at = timezone.now()
            subscription.failed_count = 0
            subscription.save(update_fields=['last_delivery_at', 'failed_count'])

            return {'status': 'success'}
        else:
            delivery.status = 'FAILED'
            delivery.save()

            subscription.failed_count += 1
            subscription.save(update_fields=['failed_count'])

            if subscription.failed_count >= 10:
                subscription.is_active = False
                subscription.save(update_fields=['is_active'])

            raise self.retry(exc=Exception(f'HTTP {response.status_code}'))

    except requests.RequestException as e:
        delivery.status = 'FAILED'
        delivery.save()
        raise self.retry(exc=e)


def trigger_webhook_event(event_type, payload):
    subscriptions = WebhookSubscription.objects.filter(
        is_active=True,
        events__contains=[event_type],
    )

    for sub in subscriptions:
        delivery = WebhookDelivery.objects.create(
            subscription=sub,
            event_type=event_type,
            payload=payload,
        )
        deliver_webhook.delay(str(delivery.id))