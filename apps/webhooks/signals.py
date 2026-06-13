from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.webhooks.tasks import trigger_webhook_event
from apps.webhooks.models import WebhookEventType


@receiver(post_save, sender='transactions.SettlementIntent')
def webhook_settlement(sender, instance, created, **kwargs):
    if instance.state == 'LEDGER_FINALIZED':
        trigger_webhook_event(WebhookEventType.SETTLEMENT_COMPLETED, {
            'settlement_id': str(instance.uuid),
            'amount': str(instance.amount),
            'shares': str(instance.share_quantity),
            'sacco': instance.seller_sacco_name,
            'buyer_id': str(instance.buyer.id),
            'seller_id': str(instance.seller.id),
            'finalized_at': instance.finalized_at.isoformat() if instance.finalized_at else None,
        })
    elif instance.state == 'DISPUTED_MANUAL':
        trigger_webhook_event(WebhookEventType.SETTLEMENT_DISPUTED, {
            'settlement_id': str(instance.uuid),
            'amount': str(instance.amount),
        })


@receiver(post_save, sender='investments.LiquidityRequest')
def webhook_liquidity_request(sender, instance, created, **kwargs):
    if created:
        trigger_webhook_event(WebhookEventType.LIQUIDITY_REQUEST_CREATED, {
            'request_id': str(instance.id),
            'sacco': instance.sacco.name,
            'shares': str(instance.share_quantity),
            'price': str(instance.expected_price_per_share) if instance.expected_price_per_share else None,
        })


@receiver(post_save, sender='investments.Offer')
def webhook_offer_accepted(sender, instance, **kwargs):
    if instance.status == 'ACCEPTED':
        trigger_webhook_event(WebhookEventType.OFFER_ACCEPTED, {
            'offer_id': str(instance.id),
            'price': str(instance.price_per_share),
            'quantity': str(instance.quantity),
            'total': str(instance.total_amount),
        })