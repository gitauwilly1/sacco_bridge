import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from asyncio.log import logger

from apps.core.models import BaseModel, TimeStampedModel
from apps.core.validators import validate_positive_amount, validate_share_quantity


class SettlementState(models.TextChoices):

    MATCH_PROPOSED = 'MATCH_PROPOSED', _('Match Proposed')
    INTENT_LOCKED = 'INTENT_LOCKED', _('Intent Locked')
    BUYER_DEBIT_INITIATED = 'BUYER_DEBIT_INITIATED', _('Buyer Debit Initiated')
    BUYER_DEBIT_CONFIRMED = 'BUYER_DEBIT_CONFIRMED', _('Buyer Debit Confirmed')
    SELLER_CREDIT_INITIATED = 'SELLER_CREDIT_INITIATED', _('Seller Credit Initiated')
    SELLER_CREDIT_CONFIRMED = 'SELLER_CREDIT_CONFIRMED', _('Seller Credit Confirmed')
    LEDGER_FINALIZED = 'LEDGER_FINALIZED', _('Ledger Finalized')
    COMPENSATING = 'COMPENSATING', _('Compensating - Rolling Back')
    REVERSED = 'REVERSED', _('Reversed - Rolled Back')
    DISPUTED_MANUAL = 'DISPUTED_MANUAL', _('Disputed - Manual Review')
    CLOSED_BY_TRUSTEE = 'CLOSED_BY_TRUSTEE', _('Closed by Trustee')


class SettlementEventTrigger(models.TextChoices):

    SYSTEM_MATCH = 'SYSTEM_MATCH', _('System Match')
    INTENT_CREATED = 'INTENT_CREATED', _('Intent Created')
    BUYER_SACCO_SUCCESS = 'BUYER_SACCO_SUCCESS', _('Buyer SACCO Success')
    BUYER_SACCO_FAILURE = 'BUYER_SACCO_FAILURE', _('Buyer SACCO Failure')
    SELLER_SACCO_SUCCESS = 'SELLER_SACCO_SUCCESS', _('Seller SACCO Success')
    SELLER_SACCO_FAILURE = 'SELLER_SACCO_FAILURE', _('Seller SACCO Failure')
    API_TIMEOUT = 'API_TIMEOUT', _('API Timeout')
    API_RETRY_EXHAUSTED = 'API_RETRY_EXHAUSTED', _('API Retry Exhausted')
    STATUS_LOOKUP = 'STATUS_LOOKUP', _('Status Lookup')
    AMBIGUOUS_RESULT = 'AMBIGUOUS_RESULT', _('Ambiguous Result')
    RECOVERY_WORKER = 'RECOVERY_WORKER', _('Recovery Worker')
    OPS_MANUAL_CONFIRMATION = 'OPS_MANUAL_CONFIRMATION', _('Ops Manual Confirmation')
    OPS_REVERSAL_INITIATED = 'OPS_REVERSAL_INITIATED', _('Ops Reversal Initiated')
    OPS_ESCALATED_TO_TRUSTEE = 'OPS_ESCALATED_TO_TRUSTEE', _('Ops Escalated to Trustee')
    OPS_FORCE_SETTLED = 'OPS_FORCE_SETTLED', _('Ops Force Settled')
    OPS_NOTE_ADDED = 'OPS_NOTE_ADDED', _('Ops Note Added')
    TRUSTEE_RESOLUTION = 'TRUSTEE_RESOLUTION', _('Trustee Resolution')
    TTL_EXPIRED = 'TTL_EXPIRED', _('TTL Expired')
    COMPENSATION_SUCCESS = 'COMPENSATION_SUCCESS', _('Compensation Success')
    COMPENSATION_FAILURE = 'COMPENSATION_FAILURE', _('Compensation Failure')


class DisputeResolutionType(models.TextChoices):

    MANUAL_CREDIT_CONFIRMED = 'MANUAL_CREDIT_CONFIRMED', _('Manual Credit Confirmed by SACCO')
    BUYER_REVERSAL_INITIATED = 'BUYER_REVERSAL_INITIATED', _('Buyer Reversal Initiated')
    ESCALATED_TO_TRUSTEE = 'ESCALATED_TO_TRUSTEE', _('Escalated to Trustee')
    FORCE_MARKED_SETTLED = 'FORCE_MARKED_SETTLED', _('Force Marked Settled')
    MANUAL_REVERSAL = 'MANUAL_REVERSAL', _('Manual Reversal')


class SettlementIntent(BaseModel):

    # Unique identification and idempotency
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("Public-facing unique identifier for this settlement.")
    )

    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text=_("Idempotency key to prevent duplicate processing.")
    )

    # State management
    state = models.CharField(
        max_length=30,
        choices=SettlementState.choices,
        default=SettlementState.MATCH_PROPOSED,
        db_index=True,
        help_text=_("Current state in the settlement state machine.")
    )

    version = models.PositiveIntegerField(
        default=0,
        help_text=_("Optimistic locking version counter.")
    )

    # Parties involved
    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='buyer_settlements',
        help_text=_("The buyer in this settlement.")
    )

    seller = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='seller_settlements',
        help_text=_("The seller in this settlement.")
    )

    # SACCO references
    buyer_sacco_id = models.IntegerField(
        help_text=_("ID of the buyer's SACCO.")
    )

    buyer_sacco_name = models.CharField(
        max_length=255,
        help_text=_("Name of the buyer's SACCO for audit trail.")
    )

    seller_sacco_id = models.IntegerField(
        help_text=_("ID of the seller's SACCO.")
    )

    seller_sacco_name = models.CharField(
        max_length=255,
        help_text=_("Name of the seller's SACCO for audit trail.")
    )

    # Financial details
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Transaction amount in KSh.")
    )

    share_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[validate_share_quantity],
        help_text=_("Number of shares being transferred.")
    )

    price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Agreed price per share.")
    )

    platform_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Platform fee for this settlement.")
    )

    net_seller_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Net amount the seller receives after fees.")
    )

    # External transaction references
    buyer_debit_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("Transaction reference from buyer's SACCO for the debit.")
    )

    seller_credit_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("Transaction reference from seller's SACCO for the credit.")
    )

    buyer_reversal_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("Reference for buyer debit reversal if applicable.")
    )

    # Connection reference
    connection = models.ForeignKey(
        'investments.Connection',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='settlements',
        help_text=_("The connection that led to this settlement.")
    )

    # Liquidity request reference
    liquidity_request_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=_("Reference to the original liquidity request.")
    )

    # Timing
    matched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the match was first proposed.")
    )

    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the intent was locked and funds reserved.")
    )

    buyer_debited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When buyer funds were successfully debited.")
    )

    seller_credited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When seller was successfully credited.")
    )

    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the ledger was finalized.")
    )

    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the transaction was reversed.")
    )

    # TTL and recovery
    ttl_seconds = models.PositiveIntegerField(
        default=300,
        help_text=_("Time-to-live in seconds before auto-expiry.")
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this intent expires if not progressed.")
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of recovery attempts made.")
    )

    max_retries = models.PositiveIntegerField(
        default=3,
        help_text=_("Maximum number of automated recovery attempts.")
    )

    # Dispute handling
    dispute_opened_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When a dispute was opened for this settlement.")
    )

    dispute_resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the dispute was resolved.")
    )

    dispute_resolution_type = models.CharField(
        max_length=40,
        choices=DisputeResolutionType.choices,
        null=True,
        blank=True,
        help_text=_("How the dispute was resolved.")
    )

    dispute_resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes',
        help_text=_("The staff member who resolved the dispute.")
    )

    trustee_case_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Trustee bank case reference if escalated.")
    )

    # Notes
    internal_notes = models.TextField(
        blank=True,
        default='',
        help_text=_("Internal notes for operations team (not visible to members).")
    )

    class Meta:
        verbose_name = _('Settlement Intent')
        verbose_name_plural = _('Settlement Intents')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['state', 'updated_at']),
            models.Index(fields=['buyer', 'state']),
            models.Index(fields=['seller', 'state']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Settlement {self.uuid} - {self.get_state_display()}"

    def save(self, *args, **kwargs):
        if not self.expires_at and self.ttl_seconds:
            self.expires_at = timezone.now() + timezone.timedelta(
                seconds=self.ttl_seconds
            )

        if self.amount and self.platform_fee:
            self.net_seller_amount = self.amount - self.platform_fee

        super().save(*args, **kwargs)

    def transition_to(self, new_state, trigger, external_ref='', metadata=None):
        from_state = self.state

        if not self._is_valid_transition(from_state, new_state):
            raise ValueError(
                f"Invalid state transition: {from_state} -> {new_state}"
            )

        self.state = new_state
        self.version += 1
        self.updated_at = timezone.now()

        if new_state == SettlementState.INTENT_LOCKED:
            self.locked_at = timezone.now()
        elif new_state == SettlementState.BUYER_DEBIT_CONFIRMED:
            self.buyer_debited_at = timezone.now()
        elif new_state == SettlementState.SELLER_CREDIT_CONFIRMED:
            self.seller_credited_at = timezone.now()
        elif new_state == SettlementState.LEDGER_FINALIZED:
            self.finalized_at = timezone.now()
        elif new_state == SettlementState.REVERSED:
            self.reversed_at = timezone.now()
        elif new_state == SettlementState.DISPUTED_MANUAL:
            self.dispute_opened_at = timezone.now()

        self.save()

        SettlementEvent.objects.create(
            intent=self,
            from_state=from_state,
            to_state=new_state,
            trigger=trigger,
            external_ref=external_ref,
            metadata=metadata or {},
        )

            # Broadcast to WebSocket
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'settlement_{self.uuid}',
                    {
                        'type': 'settlement.update',
                        'intent_id': str(self.uuid),
                        'from_state': from_state,
                        'to_state': new_state,
                        'state_display': self.get_state_display(),
                        'timestamp': str(timezone.now()),
                        'message': f'Settlement moved to {self.get_state_display()}',
                    }
                )
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed for settlement {self.uuid}: {e}")

        return True

    def _is_valid_transition(self, from_state, to_state):
        valid_transitions = {
            SettlementState.MATCH_PROPOSED: [
                SettlementState.INTENT_LOCKED,
                SettlementState.REVERSED,
            ],
            SettlementState.INTENT_LOCKED: [
                SettlementState.BUYER_DEBIT_INITIATED,
                SettlementState.DISPUTED_MANUAL,
                SettlementState.REVERSED,
            ],
            SettlementState.BUYER_DEBIT_INITIATED: [
                SettlementState.BUYER_DEBIT_CONFIRMED,
                SettlementState.DISPUTED_MANUAL,
                SettlementState.REVERSED,
            ],
            SettlementState.BUYER_DEBIT_CONFIRMED: [
                SettlementState.SELLER_CREDIT_INITIATED,
                SettlementState.COMPENSATING,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.SELLER_CREDIT_INITIATED: [
                SettlementState.SELLER_CREDIT_CONFIRMED,
                SettlementState.DISPUTED_MANUAL,
                SettlementState.COMPENSATING,
            ],
            SettlementState.SELLER_CREDIT_CONFIRMED: [
                SettlementState.LEDGER_FINALIZED,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.COMPENSATING: [
                SettlementState.REVERSED,
                SettlementState.DISPUTED_MANUAL,
            ],
            SettlementState.DISPUTED_MANUAL: [
                SettlementState.SELLER_CREDIT_CONFIRMED,
                SettlementState.LEDGER_FINALIZED,
                SettlementState.REVERSED,
                SettlementState.CLOSED_BY_TRUSTEE,
            ],
            SettlementState.LEDGER_FINALIZED: [],
            SettlementState.REVERSED: [],
            SettlementState.CLOSED_BY_TRUSTEE: [],
        }

        return to_state in valid_transitions.get(from_state, [])

    def is_past_point_of_no_return(self):
        irreversible_states = [
            SettlementState.BUYER_DEBIT_CONFIRMED,
            SettlementState.SELLER_CREDIT_INITIATED,
            SettlementState.SELLER_CREDIT_CONFIRMED,
            SettlementState.LEDGER_FINALIZED,
        ]
        return self.state in irreversible_states

    def is_terminal(self):
        terminal_states = [
            SettlementState.LEDGER_FINALIZED,
            SettlementState.REVERSED,
            SettlementState.CLOSED_BY_TRUSTEE,
        ]
        return self.state in terminal_states


class SettlementEvent(models.Model):

    intent = models.ForeignKey(
        SettlementIntent,
        on_delete=models.CASCADE,
        related_name='events',
        help_text=_("The settlement intent this event belongs to.")
    )

    from_state = models.CharField(
        max_length=30,
        choices=SettlementState.choices,
        help_text=_("Previous state before this transition.")
    )

    to_state = models.CharField(
        max_length=30,
        choices=SettlementState.choices,
        help_text=_("New state after this transition.")
    )

    trigger = models.CharField(
        max_length=50,
        choices=SettlementEventTrigger.choices,
        help_text=_("What triggered this state transition.")
    )

    external_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("External reference (e.g., SACCO transaction ID).")
    )

    metadata = models.JSONField(
        default=dict,
        help_text=_("Additional context data for this event.")
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("When this event occurred.")
    )

    actor = models.CharField(
        max_length=100,
        default='system',
        help_text=_("Who or what caused this event (system, worker instance, user).")
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


class LedgerEntry(models.Model):

    settlement = models.OneToOneField(
        SettlementIntent,
        on_delete=models.PROTECT,
        related_name='ledger_entry',
        help_text=_("The settlement that created this ledger entry.")
    )

    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ledger_purchases',
        help_text=_("The buyer receiving shares.")
    )

    seller = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ledger_sales',
        help_text=_("The seller transferring shares.")
    )

    sacco_id = models.IntegerField(
        help_text=_("SACCO where shares are held.")
    )

    share_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text=_("Number of shares transferred.")
    )

    price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Price per share at settlement.")
    )

    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Total transaction value.")
    )

    platform_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Platform fee charged.")
    )

    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When this ledger entry was created.")
    )

    is_reversed = models.BooleanField(
        default=False,
        help_text=_("Whether this ledger entry has been reversed.")
    )

    reversal_entry = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='original_entry',
        help_text=_("Reference to the reversal ledger entry if reversed.")
    )

    class Meta:
        verbose_name = _('Ledger Entry')
        verbose_name_plural = _('Ledger Entries')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['buyer', 'recorded_at']),
            models.Index(fields=['seller', 'recorded_at']),
            models.Index(fields=['sacco_id']),
        ]

    def __str__(self):
        return f"Ledger: {self.share_quantity} shares - KSh {self.total_amount}"


class SettlementReversal(models.Model):

    settlement = models.ForeignKey(
        SettlementIntent,
        on_delete=models.PROTECT,
        related_name='reversals',
        help_text=_("The settlement being reversed.")
    )

    reversal_type = models.CharField(
        max_length=30,
        choices=[
            ('BUYER_DEBIT', 'Buyer Debit Reversal'),
            ('SELLER_SHARE_RELEASE', 'Seller Share Release'),
            ('FULL_REVERSAL', 'Full Reversal'),
        ],
        help_text=_("Type of reversal.")
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Amount being reversed (if applicable).")
    )

    external_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("External reference for the reversal transaction.")
    )

    initiated_by = models.CharField(
        max_length=100,
        default='system',
        help_text=_("What initiated this reversal.")
    )

    initiated_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When the reversal was initiated.")
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the reversal was completed.")
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('INITIATED', 'Initiated'),
            ('PROCESSING', 'Processing'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ],
        default='INITIATED',
        help_text=_("Current reversal status.")
    )

    notes = models.TextField(
        blank=True,
        default='',
        help_text=_("Notes about the reversal.")
    )

    class Meta:
        verbose_name = _('Settlement Reversal')
        verbose_name_plural = _('Settlement Reversals')
        ordering = ['-initiated_at']

    def __str__(self):
        return f"Reversal for Settlement {self.settlement.uuid}"