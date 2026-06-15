import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class WebhookEventType(models.TextChoices):
    SETTLEMENT_COMPLETED = 'SETTLEMENT_COMPLETED', _('Settlement Completed')
    SETTLEMENT_DISPUTED = 'SETTLEMENT_DISPUTED', _('Settlement Disputed')
    LIQUIDITY_REQUEST_CREATED = 'LIQUIDITY_REQUEST_CREATED', _('Liquidity Request Created')
    OFFER_ACCEPTED = 'OFFER_ACCEPTED', _('Offer Accepted')
    LOAN_APPROVED = 'LOAN_APPROVED', _('Loan Approved')
    LOAN_DISBURSED = 'LOAN_DISBURSED', _('Loan Disbursed')
    CONTRIBUTION_RECEIVED = 'CONTRIBUTION_RECEIVED', _('Contribution Received')
    CHAMA_CREATED = 'CHAMA_CREATED', _('Chama Created')
    MEMBER_JOINED = 'MEMBER_JOINED', _('Member Joined')
    MEMBER_LEFT = 'MEMBER_LEFT', _('Member Left')


class WebhookSubscription(BaseModel):

    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500, help_text=_("Webhook endpoint URL."))
    secret = models.CharField(
        max_length=128, default=uuid.uuid4,
        help_text=_("Secret key for HMAC signature verification.")
    )
    is_active = models.BooleanField(default=True, db_index=True)
    events = models.JSONField(
        default=list,
        help_text=_("List of WebhookEventType values to subscribe to.")
    )
    retry_limit = models.PositiveIntegerField(default=3)
    last_delivery_at = models.DateTimeField(null=True, blank=True)
    failed_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('Webhook Subscription')
        verbose_name_plural = _('Webhook Subscriptions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.url}"


class WebhookDelivery(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        WebhookSubscription, on_delete=models.CASCADE, related_name='deliveries'
    )
    event_type = models.CharField(max_length=50, choices=WebhookEventType.choices)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'), ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'), ('RETRYING', 'Retrying'),
        ],
        default='PENDING',
    )
    response_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default='')
    attempt_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Webhook Delivery')
        verbose_name_plural = _('Webhook Deliveries')
        ordering = ['-created_at']