import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class RiskLevel(models.TextChoices):
    LOW = 'LOW', _('Low Risk')
    MEDIUM = 'MEDIUM', _('Medium Risk')
    HIGH = 'HIGH', _('High Risk')
    CRITICAL = 'CRITICAL', _('Critical Risk')


class FraudAction(models.TextChoices):
    ALLOW = 'ALLOW', _('Allow')
    FLAG = 'FLAG', _('Flag for Review')
    HOLD = 'HOLD', _('Hold Funds')
    BLOCK = 'BLOCK', _('Block Transaction')


class TransactionRiskAssessment(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='risk_assessments'
    )

    transaction_type = models.CharField(
        max_length=30,
        choices=[
            ('SETTLEMENT', 'Settlement'),
            ('LOAN', 'Loan'),
            ('CONTRIBUTION', 'Contribution'),
            ('WITHDRAWAL', 'Withdrawal'),
        ],
    )

    transaction_reference = models.CharField(max_length=255)

    amount = models.DecimalField(max_digits=15, decimal_places=2)

    risk_score = models.PositiveIntegerField(
        default=0, help_text=_("Risk score 0-100 (higher = more risky)")
    )

    risk_level = models.CharField(
        max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW
    )

    recommended_action = models.CharField(
        max_length=10, choices=FraudAction.choices, default=FraudAction.ALLOW
    )

    applied_action = models.CharField(
        max_length=10, choices=FraudAction.choices, null=True, blank=True
    )

    # Detection signals
    triggers = models.JSONField(
        default=list,
        help_text=_("List of fraud signals that were triggered.")
    )

    velocity_24h_count = models.PositiveIntegerField(default=0)
    velocity_24h_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    velocity_7d_count = models.PositiveIntegerField(default=0)

    device_fingerprint = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    ip_reputation_score = models.PositiveIntegerField(default=50)
    location_mismatch = models.BooleanField(default=False)

    is_new_device = models.BooleanField(default=False)
    is_unusual_hour = models.BooleanField(default=False)
    is_unusual_amount = models.BooleanField(default=False)

    reviewed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fraud_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Transaction Risk Assessment')
        verbose_name_plural = _('Transaction Risk Assessments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['risk_level', '-created_at']),
            models.Index(fields=['applied_action']),
        ]

    def __str__(self):
        return f"Risk {self.risk_score} - {self.risk_level} - {self.transaction_reference}"


class DeviceFingerprint(models.Model):

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='known_devices'
    )
    fingerprint = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_trusted = models.BooleanField(default=False)
    transaction_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['user', 'fingerprint']

    def __str__(self):
        return f"Device {self.fingerprint[:20]}... for {self.user.email}"