import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.core.validators import validate_positive_amount


class MpesaTransactionStatus(models.TextChoices):

    PENDING = 'PENDING', _('Pending')
    INITIATED = 'INITIATED', _('STK Push Initiated')
    PROCESSING = 'PROCESSING', _('Processing')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')
    CANCELLED = 'CANCELLED', _('Cancelled by User')
    TIMEOUT = 'TIMEOUT', _('Request Timed Out')


class MpesaTransactionType(models.TextChoices):

    CHAMA_CONTRIBUTION = 'CHAMA_CONTRIBUTION', _('Chama Contribution')
    LOAN_REPAYMENT = 'LOAN_REPAYMENT', _('Loan Repayment')
    SHARE_PURCHASE = 'SHARE_PURCHASE', _('SACCO Share Purchase')
    PAYOUT = 'PAYOUT', _('Chama Payout')
    PLATFORM_FEE = 'PLATFORM_FEE', _('Platform Fee')


class MpesaTransaction(BaseModel):

    # Unique identifiers
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("Platform-generated unique transaction ID.")
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Merchant Request ID from M-Pesa API.")
    )

    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        db_index=True,
        help_text=_("Checkout Request ID from M-Pesa STK Push.")
    )

    mpesa_receipt_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        db_index=True,
        help_text=_("M-Pesa receipt number for completed transaction.")
    )

    # User and chama references
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='mpesa_transactions',
        help_text=_("The user making the payment.")
    )

    chama = models.ForeignKey(
        'chamas.Chama',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mpesa_transactions',
        help_text=_("The chama this payment is for (if applicable).")
    )

    contribution = models.ForeignKey(
        'chamas.Contribution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mpesa_transactions',
        help_text=_("The contribution this payment fulfills.")
    )

    # Transaction details
    transaction_type = models.CharField(
        max_length=30,
        choices=MpesaTransactionType.choices,
        default=MpesaTransactionType.CHAMA_CONTRIBUTION,
        help_text=_("Type of transaction.")
    )

    phone_number = models.CharField(
        max_length=20,
        help_text=_("Phone number sending the payment (format: 2547XXXXXXXX).")
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Transaction amount in KSh.")
    )

    status = models.CharField(
        max_length=20,
        choices=MpesaTransactionStatus.choices,
        default=MpesaTransactionStatus.PENDING,
        db_index=True,
        help_text=_("Current transaction status.")
    )

    # Reference
    account_reference = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Account reference sent to M-Pesa.")
    )

    transaction_description = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Description of the transaction.")
    )

    # Timing
    initiated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When STK Push was sent to the user.")
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the transaction was confirmed via callback.")
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the transaction failed or timed out.")
    )

    # Raw API data
    stk_request_data = models.JSONField(
        default=dict,
        help_text=_("Request payload sent to M-Pesa STK Push API.")
    )

    stk_response_data = models.JSONField(
        default=dict,
        help_text=_("Response from M-Pesa STK Push API.")
    )

    callback_data = models.JSONField(
        default=dict,
        help_text=_("Raw callback data received from M-Pesa.")
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Error message if transaction failed.")
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of retry attempts for failed callbacks.")
    )

    is_reconciled = models.BooleanField(
        default=False,
        help_text=_("Whether this transaction has been reconciled with chama records.")
    )

    class Meta:
        verbose_name = _('M-Pesa Transaction')
        verbose_name_plural = _('M-Pesa Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['mpesa_receipt_number']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"M-Pesa {self.get_transaction_type_display()} - KSh {self.amount} ({self.get_status_display()})"

    def mark_initiated(self, merchant_request_id, checkout_request_id, response_data):
        self.status = MpesaTransactionStatus.INITIATED
        self.merchant_request_id = merchant_request_id
        self.checkout_request_id = checkout_request_id
        self.stk_response_data = response_data
        self.initiated_at = timezone.now()
        self.save()

    def mark_completed(self, mpesa_receipt_number, callback_data):
        self.status = MpesaTransactionStatus.COMPLETED
        self.mpesa_receipt_number = mpesa_receipt_number
        self.callback_data = callback_data
        self.completed_at = timezone.now()
        self.save()

        # Auto-verify linked contribution
        if self.contribution and self.transaction_type == MpesaTransactionType.CHAMA_CONTRIBUTION:
            self.contribution.mark_as_paid(mpesa_receipt_number)

    def mark_failed(self, error_message, callback_data=None):
        self.status = MpesaTransactionStatus.FAILED
        self.error_message = error_message
        if callback_data:
            self.callback_data = callback_data
        self.failed_at = timezone.now()
        self.save()

    def mark_timeout(self):
        self.status = MpesaTransactionStatus.TIMEOUT
        self.failed_at = timezone.now()
        self.save()