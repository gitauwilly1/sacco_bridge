import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EscrowStatus(models.TextChoices):
    CREATED = 'CREATED', _('Created')
    FUNDED = 'FUNDED', _('Funded - Buyer Paid')
    RELEASED = 'RELEASED', _('Released - Seller Paid')
    REFUNDED = 'REFUNDED', _('Refunded - Returned to Buyer')
    DISPUTED = 'DISPUTED', _('Disputed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class EscrowAccount(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    settlement = models.OneToOneField(
        'transactions.SettlementIntent',
        on_delete=models.PROTECT,
        related_name='escrow',
        help_text=_("The settlement this escrow secures.")
    )

    buyer = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='escrow_payments'
    )

    seller = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='escrow_receipts'
    )

    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text=_("Amount held in escrow.")
    )

    platform_fee = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Platform fee to be deducted.")
    )

    status = models.CharField(
        max_length=20, choices=EscrowStatus.choices,
        default=EscrowStatus.CREATED, db_index=True,
    )

    buyer_ref = models.CharField(
        max_length=128, blank=True, default='',
        help_text=_("External reference for buyer payment.")
    )

    seller_ref = models.CharField(
        max_length=128, blank=True, default='',
        help_text=_("External reference for seller payout.")
    )

    refund_ref = models.CharField(
        max_length=128, blank=True, default='',
        help_text=_("External reference for refund if applicable.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Escrow Account')
        verbose_name_plural = _('Escrow Accounts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['seller', 'status']),
        ]

    def __str__(self):
        return f"Escrow {self.id} - KSh {self.amount} ({self.status})"

    def mark_funded(self, buyer_ref=''):
        self.status = EscrowStatus.FUNDED
        self.buyer_ref = buyer_ref
        self.funded_at = timezone.now()
        self.save()

    def mark_released(self, seller_ref=''):
        self.status = EscrowStatus.RELEASED
        self.seller_ref = seller_ref
        self.released_at = timezone.now()
        self.completed_at = timezone.now()
        self.save()

    def mark_refunded(self, refund_ref=''):
        self.status = EscrowStatus.REFUNDED
        self.refund_ref = refund_ref
        self.refunded_at = timezone.now()
        self.completed_at = timezone.now()
        self.save()

    def mark_disputed(self):
        self.status = EscrowStatus.DISPUTED
        self.save()