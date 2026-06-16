import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EscrowStatus(models.TextChoices):
    CREATED = 'CREATED', _('Created')
    FUNDED = 'FUNDED', _('Funded - Buyer Paid')
    HELD = 'HELD', _('Held - Under Review')
    HELD_PARTIAL = 'HELD_PARTIAL', _('Partially Held')
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

    hold_reason = models.TextField(blank=True, default='')
    hold_triggered_by = models.CharField(
        max_length=30,
        choices=[
            ('FRAUD_DETECTION', 'Fraud Detection'),
            ('LARGE_AMOUNT', 'Large Transaction'),
            ('FIRST_TRANSACTION', 'First Transaction'),
            ('NEW_DEVICE', 'New Device'),
            ('ADMIN_MANUAL', 'Admin Manual Hold'),
        ],
        blank=True, default='',
    )
    hold_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text=_("Amount held (may be partial).")
    )
    released_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Amount progressively released.")
    )
    hold_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When the hold automatically expires.")
    )
    released_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='released_escrows'
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

    def mark_held(self, reason='', trigger='', hold_amount=None):
        self.status = EscrowStatus.HELD
        self.hold_reason = reason
        self.hold_triggered_by = trigger
        self.hold_amount = hold_amount or self.amount
        self.hold_expires_at = timezone.now() + timezone.timedelta(hours=48)
        self.save()

    def mark_held_partial(self, hold_amount, reason='', trigger=''):
        self.status = EscrowStatus.HELD_PARTIAL
        self.hold_amount = hold_amount
        self.released_amount = self.amount - hold_amount
        self.hold_reason = reason
        self.hold_triggered_by = trigger
        self.save()

    def release_hold(self, released_by=None):
        self.status = EscrowStatus.RELEASED
        self.released_by = released_by
        self.released_at = timezone.now()
        self.completed_at = timezone.now()
        self.save()

    def progressive_release(self, amount, released_by=None):
        self.released_amount += amount
        if self.released_amount >= self.amount:
            self.status = EscrowStatus.RELEASED
            self.released_at = timezone.now()
            self.completed_at = timezone.now()
        self.released_by = released_by
        self.save()