import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from apps.core.models import BaseModel, TimeStampedModel, UUIDModel
from apps.core.validators import validate_positive_amount


class SettlementState(models.TextChoices):

    MATCH_PROPOSED = 'MATCH_PROPOSED', _('Match Proposed')
    INTENT_LOCKED = 'INTENT_LOCKED', _('Intent Locked')
    BUYER_DEBIT_INITIATED = 'BUYER_DEBIT_INITIATED', _('Buyer Debit Initiated')
    BUYER_DEBIT_CONFIRMED = 'BUYER_DEBIT_CONFIRMED', _('Buyer Debit Confirmed')
    SELLER_CREDIT_INITIATED = 'SELLER_CREDIT_INITIATED', _('Seller Credit Initiated')
    SELLER_CREDIT_CONFIRMED = 'SELLER_CREDIT_CONFIRMED', _('Seller Credit Confirmed')
    LEDGER_FINALIZED = 'LEDGER_FINALIZED', _('Ledger Finalized')
    COMPENSATING = 'COMPENSATING', _('Compensating')
    DISPUTED_MANUAL = 'DISPUTED_MANUAL', _('Disputed - Manual Review')
    SETTLED = 'SETTLED', _('Settled')


class DisputeResolutionType(models.TextChoices):

    AUTOMATIC_RECOVERY = 'AUTOMATIC_RECOVERY', _('Automatic Recovery')
    MANUAL_CREDIT_CONFIRMED = 'MANUAL_CREDIT_CONFIRMED', _('Manual Credit Confirmed by SACCO')
    BUYER_REVERSAL_INITIATED = 'BUYER_REVERSAL_INITIATED', _('Buyer Reversal Initiated')
    ESCALATED_TO_TRUSTEE = 'ESCALATED_TO_TRUSTEE', _('Escalated to Trustee')
    FORCE_SETTLED = 'FORCE_SETTLED', _('Force Settled - Executive Authorization')
    CLOSED_BY_TRUSTEE = 'CLOSED_BY_TRUSTEE', _('Closed by Trustee Determination')


class SettlementIntent(UUIDModel, TimeStampedModel):

    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text=_("Unique key to prevent duplicate settlement processing.")
    )

    state = models.CharField(
        max_length=30,
        choices=SettlementState.choices,
        default=SettlementState.MATCH_PROPOSED,
        db_index=True,
        help_text=_("Current state in the settlement lifecycle.")
    )

    version = models.PositiveIntegerField(
        default=0,
        help_text=_("Optimistic concurrency control version number.")
    )

    connection = models.ForeignKey(
        'investments.Connection',
        on_delete=models.PROTECT,
        related_name='settlement_intents',
        help_text=_("The buyer-seller connection being settled.")
    )

    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='buyer_settlements',
        help_text=_("The buyer in this transaction.")
    )

    seller = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='seller_settlements',
        help_text=_("The seller in this transaction.")
    )

    buyer_sacco_ref = models.CharField(
        max_length=100,
        help_text=_("Reference to the buyer's SACCO for this transaction.")
    )

    seller_sacco_ref = models.CharField(
        max_length=100,
        help_text=_("Reference to the seller's SACCO for this transaction.")
    )

    share_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text=_("Number of shares being transferred.")
    )

    price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Agreed price per share.")
    )

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Total transaction amount (price x quantity).")
    )

    platform_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Platform fee for this transaction.")
    )

    buyer_total_debit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total amount debited from buyer (total + fee).")
    )

    seller_net_credit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Net amount credited to seller (total - fee).")
    )

    buyer_debit_transaction_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("External transaction ID from buyer's SACCO for the debit.")
    )

    seller_credit_transaction_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("External transaction ID from seller's SACCO for the credit.")
    )

    reversal_transaction_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("Transaction ID for reversal if compensating.")
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of recovery retries attempted.")
    )

    max_retries = models.PositiveIntegerField(
        default=3,
        help_text=_("Maximum number of automatic retries before escalation.")
    )

    last_error = models.TextField(
        blank=True,
        default='',
        help_text=_("Last error message received during processing.")
    )

    last_error_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the last error occurred.")
    )

    timeout_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this intent will timeout if not progressed.")
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When settlement was completed or definitively resolved.")
    )

    class Meta:
        verbose_name = _('Settlement Intent')
        verbose_name_plural = _('Settlement Intents')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['state']),
            models.Index(fields=['state', 'updated_at']),
            models.Index(fields=['buyer', 'state']),
            models.Index(fields=['seller', 'state']),
        ]

    def __str__(self):
        return f"Settlement {self.id} - {self.get_state_display()}"

    def save(self, *args, **kwargs):
        if not self.idempotency_key:
            from apps.core.utils import generate_idempotency_key
            self.idempotency_key = generate_idempotency_key(
                str(self.connection_id),
                str(self.total_amount),
                str(timezone.now().timestamp())
            )

        if self.total_amount and not self.platform_fee:
            from apps.core.utils import calculate_settlement_fee
            self.platform_fee = calculate_settlement_fee(self.total_amount)
            self.buyer_total_debit = self.total_amount + self.platform_fee
            self.seller_net_credit = self.total_amount - self.platform_fee

        super().save(*args, **kwargs)

    def transition_to(self, new_state, error_message=''):
        old_state = self.state

        allowed_transitions = {
            SettlementState.MATCH_PROPOSED: [
                SettlementState.INTENT_LOCKED,
                SettlementState.SETTLED,
            ],
            SettlementState.INTENT_LOCKED: [
                SettlementState.BUYER_DEBIT_INITIATED,
                SettlementState.DISPUTED_MANUAL,
                SettlementState.SETTLED,
            ],
            SettlementState.BUYER_DEBIT_INITIATED: [
                SettlementState.BUYER_DEBIT_CONFIRMED,
                SettlementState.COMPENSATING,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.BUYER_DEBIT_CONFIRMED: [
                SettlementState.SELLER_CREDIT_INITIATED,
                SettlementState.COMPENSATING,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.SELLER_CREDIT_INITIATED: [
                SettlementState.SELLER_CREDIT_CONFIRMED,
                SettlementState.COMPENSATING,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.SELLER_CREDIT_CONFIRMED: [
                SettlementState.LEDGER_FINALIZED,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.LEDGER_FINALIZED: [
                SettlementState.SETTLED,
            ],
            SettlementState.COMPENSATING: [
                SettlementState.INTENT_LOCKED,
                SettlementState.DISPUTED_MANUAL,
                SettlementState.SETTLED,
            ],
            SettlementState.DISPUTED_MANUAL: [
                SettlementState.SELLER_CREDIT_CONFIRMED,
                SettlementState.LEDGER_FINALIZED,
                SettlementState.COMPENSATING,
                SettlementState.SETTLED,
            ],
        }

        if new_state not in allowed_transitions.get(old_state, []):
            raise ValueError(
                _(f"Cannot transition from {old_state} to {new_state}")
            )

        self.state = new_state
        self.version += 1

        if error_message:
            self.last_error = error_message
            self.last_error_at = timezone.now()

        if new_state == SettlementState.SETTLED:
            self.completed_at = timezone.now()

        self.save()

        SettlementEvent.objects.create(
            intent=self,
            from_state=old_state,
            to_state=new_state,
            trigger='STATE_TRANSITION',
            metadata={
                'version': self.version,
                'error': error_message if error_message else None,
            }
        )

        return True

    def is_terminal(self):
        return self.state in [
            SettlementState.SETTLED,
        ]

    def is_recoverable(self):
        return self.state in [
            SettlementState.INTENT_LOCKED,
            SettlementState.BUYER_DEBIT_INITIATED,
            SettlementState.SELLER_CREDIT_INITIATED,
            SettlementState.COMPENSATING,
        ]

    def requires_manual_intervention(self):
        return self.state == SettlementState.DISPUTED_MANUAL


class SettlementEvent(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    intent = models.ForeignKey(
        SettlementIntent,
        on_delete=models.CASCADE,
        related_name='events',
        help_text=_("The settlement intent this event belongs to.")
    )

    from_state = models.CharField(
        max_length=30,
        help_text=_("State before the transition.")
    )

    to_state = models.CharField(
        max_length=30,
        help_text=_("State after the transition.")
    )

    trigger = models.CharField(
        max_length=100,
        help_text=_("What triggered this event (API call, timeout, manual action).")
    )

    external_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("External reference (e.g., SACCO transaction ID).")
    )

    metadata = models.JSONField(
        default=dict,
        help_text=_("Additional event metadata for audit purposes.")
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("When this event occurred.")
    )

    actor = models.CharField(
        max_length=100,
        default='system',
        help_text=_("Who or what triggered this event (system, user_id, worker_name).")
    )

    class Meta:
        verbose_name = _('Settlement Event')
        verbose_name_plural = _('Settlement Events')
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['intent', 'timestamp']),
            models.Index(fields=['trigger']),
        ]

    def __str__(self):
        return f"Event: {self.from_state} -> {self.to_state} ({self.trigger})"


class DisputeRecord(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    settlement_intent = models.OneToOneField(
        SettlementIntent,
        on_delete=models.PROTECT,
        related_name='dispute',
        help_text=_("The settlement intent under dispute.")
    )

    dispute_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Human-readable dispute reference number (e.g., DISP-20260529-0001).")
    )

    status = models.CharField(
        max_length=30,
        choices=[
            ('OPEN', 'Open'),
            ('INVESTIGATING', 'Investigating'),
            ('AWAITING_SACCO', 'Awaiting SACCO Response'),
            ('AWAITING_TRUSTEE', 'Awaiting Trustee Determination'),
            ('RESOLVED', 'Resolved'),
            ('CLOSED', 'Closed'),
        ],
        default='OPEN',
        db_index=True,
        help_text=_("Current dispute status.")
    )

    priority = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],
        default='MEDIUM',
        help_text=_("Dispute priority level.")
    )

    affected_party = models.CharField(
        max_length=20,
        choices=[
            ('BUYER', 'Buyer'),
            ('SELLER', 'Seller'),
            ('BOTH', 'Both Parties'),
        ],
        help_text=_("Which party is affected by the dispute.")
    )

    disputed_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Amount in dispute.")
    )

    resolution_type = models.CharField(
        max_length=30,
        choices=DisputeResolutionType.choices,
        null=True,
        blank=True,
        help_text=_("How the dispute was resolved.")
    )

    resolution_notes = models.TextField(
        blank=True,
        default='',
        help_text=_("Detailed resolution notes.")
    )

    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes',
        help_text=_("Staff member who resolved the dispute.")
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the dispute was resolved.")
    )

    trustee_case_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Trustee bank case number if escalated.")
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the dispute was created.")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When the dispute was last updated.")
    )

    class Meta:
        verbose_name = _('Dispute Record')
        verbose_name_plural = _('Dispute Records')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dispute_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"Dispute {self.dispute_reference} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.dispute_reference:
            from apps.core.utils import generate_unique_id
            self.dispute_reference = generate_unique_id('DISP')
        super().save(*args, **kwargs)


class DisputeEvent(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    dispute = models.ForeignKey(
        DisputeRecord,
        on_delete=models.CASCADE,
        related_name='events',
        help_text=_("The dispute this event belongs to.")
    )

    action = models.CharField(
        max_length=100,
        help_text=_("Action taken (e.g., SACCO_CONTACTED, TRUSTEE_ESCALATED, RESOLVED).")
    )

    description = models.TextField(
        help_text=_("Description of the action taken.")
    )

    actor = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_actions',
        help_text=_("Staff member who took this action.")
    )

    evidence = models.JSONField(
        default=dict,
        help_text=_("Structured evidence for this action.")
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text=_("When this action was taken.")
    )

    class Meta:
        verbose_name = _('Dispute Event')
        verbose_name_plural = _('Dispute Events')
        ordering = ['timestamp']

    def __str__(self):
        return f"Dispute Event: {self.action} at {self.timestamp}"


class LedgerEntry(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    settlement_intent = models.ForeignKey(
        SettlementIntent,
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        help_text=_("The settlement this entry belongs to.")
    )

    entry_type = models.CharField(
        max_length=20,
        choices=[
            ('BUYER_DEBIT', 'Buyer Debit'),
            ('SELLER_CREDIT', 'Seller Credit'),
            ('PLATFORM_FEE', 'Platform Fee'),
            ('REVERSAL', 'Reversal'),
        ],
        help_text=_("Type of ledger entry.")
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Entry amount (positive for credit, negative for debit).")
    )

    party = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        help_text=_("The party this entry affects.")
    )

    sacco_reference = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("Reference from the SACCO system.")
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text=_("Human-readable description of the entry.")
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When this entry was created.")
    )

    class Meta:
        verbose_name = _('Ledger Entry')
        verbose_name_plural = _('Ledger Entries')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['settlement_intent']),
            models.Index(fields=['party', 'created_at']),
            models.Index(fields=['entry_type']),
        ]

    def __str__(self):
        return f"Ledger: {self.get_entry_type_display()} - KSh {self.amount}"