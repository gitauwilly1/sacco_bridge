import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

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
    REVERSED = 'REVERSED', _('Reversed')
    DISPUTED_MANUAL = 'DISPUTED_MANUAL', _('Disputed - Manual Review')
    FAILED = 'FAILED', _('Failed')


class SettlementEventType(models.TextChoices):
    
    STATE_TRANSITION = 'STATE_TRANSITION', _('State Transition')
    API_CALL = 'API_CALL', _('API Call')
    API_RESPONSE = 'API_RESPONSE', _('API Response')
    RECOVERY_ATTEMPT = 'RECOVERY_ATTEMPT', _('Recovery Attempt')
    MANUAL_INTERVENTION = 'MANUAL_INTERVENTION', _('Manual Intervention')
    DISPUTE_OPENED = 'DISPUTE_OPENED', _('Dispute Opened')
    DISPUTE_RESOLVED = 'DISPUTE_RESOLVED', _('Dispute Resolved')
    TRUSTEE_ESCALATION = 'TRUSTEE_ESCALATION', _('Trustee Escalation')
    SACCO_API_FAILURE = 'SACCO_API_FAILURE', _('SACCO API Failure')
    COMPENSATION_TRIGGERED = 'COMPENSATION_TRIGGERED', _('Compensation Triggered')


class DisputeStatus(models.TextChoices):
    
    OPEN = 'OPEN', _('Open')
    INVESTIGATING = 'INVESTIGATING', _('Investigating')
    AWAITING_SACCO = 'AWAITING_SACCO', _('Awaiting SACCO Response')
    AWAITING_TRUSTEE = 'AWAITING_TRUSTEE', _('Awaiting Trustee Review')
    RESOLVED_BUYER = 'RESOLVED_BUYER', _('Resolved - Buyer')
    RESOLVED_SELLER = 'RESOLVED_SELLER', _('Resolved - Seller')
    RESOLVED_SPLIT = 'RESOLVED_SPLIT', _('Resolved - Split')
    CLOSED = 'CLOSED', _('Closed')


class ResolutionType(models.TextChoices):
    
    MANUAL_CREDIT_CONFIRMED = 'MANUAL_CREDIT_CONFIRMED', _('Manual Credit Confirmed by SACCO')
    BUYER_REVERSAL_INITIATED = 'BUYER_REVERSAL_INITIATED', _('Buyer Reversal Initiated')
    ESCALATED_TO_TRUSTEE = 'ESCALATED_TO_TRUSTEE', _('Escalated to Trustee')
    FORCE_SETTLED = 'FORCE_SETTLED', _('Force Settled - Executive Approval')
    FORCE_REVERSED = 'FORCE_REVERSED', _('Force Reversed - Executive Approval')
    TRUSTEE_ADVANCE = 'TRUSTEE_ADVANCE', _('Trustee Advanced Funds')


class SettlementIntent(BaseModel):

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text=_("Public identifier for this settlement.")
    )

    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text=_("Idempotency key to prevent duplicate processing.")
    )

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

    # Connection Reference
    connection = models.ForeignKey(
        'investments.Connection',
        on_delete=models.PROTECT,
        related_name='settlement_intents',
        help_text=_("The connection this settlement is for.")
    )

    # Buyer Information
    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='buyer_settlements',
        help_text=_("The buyer in this transaction.")
    )

    buyer_sacco_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Buyer's SACCO account reference.")
    )

    # Seller Information
    seller = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='seller_settlements',
        help_text=_("The seller in this transaction.")
    )

    seller_sacco_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Seller's SACCO account reference.")
    )

    # Financial Details
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

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Total transaction amount (price * quantity).")
    )

    platform_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Platform fee for this transaction.")
    )

    net_seller_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Net amount the seller receives after fees.")
    )

    # SACCO References
    buyer_sacco_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Buyer's SACCO identifier.")
    )

    seller_sacco_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Seller's SACCO identifier.")
    )

    # External Transaction References
    buyer_debit_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Transaction ID from buyer's SACCO for the debit.")
    )

    seller_credit_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Transaction ID from seller's SACCO for the credit.")
    )

    # M-Pesa References
    buyer_mpesa_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("M-Pesa transaction reference for buyer payment.")
    )

    seller_mpesa_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("M-Pesa transaction reference for seller receipt.")
    )

    # Timing
    matched_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the match was proposed.")
    )

    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When funds and shares were locked.")
    )

    buyer_debit_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When buyer's account was debited.")
    )

    seller_credit_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When seller's account was credited.")
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When settlement was finalized.")
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When settlement failed.")
    )

    # Retry Configuration
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of recovery attempts made.")
    )

    max_retries = models.PositiveIntegerField(
        default=3,
        help_text=_("Maximum number of automatic recovery attempts.")
    )

    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the last recovery attempt was made.")
    )

    # Error Information
    error_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Last error message if settlement failed.")
    )

    error_code = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Error code from the last failure.")
    )

    # TTL for automatic cleanup
    ttl_seconds = models.PositiveIntegerField(
        default=60,
        help_text=_("Time-to-live in seconds for INTENT_LOCKED state.")
    )

    class Meta:
        verbose_name = _('Settlement Intent')
        verbose_name_plural = _('Settlement Intents')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['state', 'updated_at']),
            models.Index(fields=['buyer', 'state']),
            models.Index(fields=['seller', 'state']),
            models.Index(fields=['connection']),
        ]

    def __str__(self):
        return f"Settlement {self.uuid} - {self.get_state_display()}"

    def save(self, *args, **kwargs):
        if self.total_amount and not self.platform_fee:
            from apps.core.utils import calculate_settlement_fee
            self.platform_fee = calculate_settlement_fee(self.total_amount)
            self.net_seller_amount = self.total_amount - self.platform_fee
        super().save(*args, **kwargs)

    def transition_to(self, new_state, error_message='', error_code=''):
        from django.db.models import F

        old_state = self.state
        
        updated = SettlementIntent.objects.filter(
            id=self.id,
            version=self.version
        ).update(
            state=new_state,
            version=F('version') + 1,
            error_message=error_message,
            error_code=error_code,
            updated_at=timezone.now()
        )

        if updated:
            self.refresh_from_db()
            
            SettlementEvent.objects.create(
                settlement_intent=self,
                event_type=SettlementEventType.STATE_TRANSITION,
                from_state=old_state,
                to_state=new_state,
                metadata={
                    'version': self.version,
                    'error_message': error_message,
                    'error_code': error_code,
                }
            )
            
            self._update_timestamps(new_state)
            
            return True
        
        return False

    def _update_timestamps(self, new_state):
        now = timezone.now()
        updates = {}
        
        if new_state == SettlementState.INTENT_LOCKED:
            updates['locked_at'] = now
        elif new_state == SettlementState.BUYER_DEBIT_CONFIRMED:
            updates['buyer_debit_at'] = now
        elif new_state == SettlementState.SELLER_CREDIT_CONFIRMED:
            updates['seller_credit_at'] = now
        elif new_state == SettlementState.LEDGER_FINALIZED:
            updates['completed_at'] = now
        elif new_state in [SettlementState.FAILED, SettlementState.REVERSED]:
            updates['failed_at'] = now
        
        if updates:
            SettlementIntent.objects.filter(id=self.id).update(**updates)

    def is_at_point_of_no_return(self):
        point_of_no_return_states = [
            SettlementState.BUYER_DEBIT_CONFIRMED,
            SettlementState.SELLER_CREDIT_INITIATED,
            SettlementState.SELLER_CREDIT_CONFIRMED,
            SettlementState.LEDGER_FINALIZED,
        ]
        return self.state in point_of_no_return_states

    def needs_recovery(self):
        stuck_states = [
            SettlementState.BUYER_DEBIT_INITIATED,
            SettlementState.SELLER_CREDIT_INITIATED,
        ]
        
        if self.state not in stuck_states:
            return False
        
        timeout_seconds = 300 if self.state == SettlementState.BUYER_DEBIT_INITIATED else 900
        
        if self.updated_at < timezone.now() - timezone.timedelta(seconds=timeout_seconds):
            return True
        
        return False


class SettlementEvent(TimeStampedModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    settlement_intent = models.ForeignKey(
        SettlementIntent,
        on_delete=models.CASCADE,
        related_name='events',
        help_text=_("The settlement this event belongs to.")
    )

    event_type = models.CharField(
        max_length=30,
        choices=SettlementEventType.choices,
        help_text=_("Type of event recorded.")
    )

    from_state = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text=_("Previous settlement state.")
    )

    to_state = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text=_("New settlement state.")
    )

    trigger = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("What triggered this event (e.g., API_TIMEOUT, SACCO_SUCCESS).")
    )

    external_reference = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=_("External transaction reference if applicable.")
    )

    performed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User who performed this action (for manual interventions).")
    )

    metadata = models.JSONField(
        default=dict,
        help_text=_("Additional event data (API payloads, error details, etc.).")
    )

    class Meta:
        verbose_name = _('Settlement Event')
        verbose_name_plural = _('Settlement Events')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['settlement_intent', 'created_at']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"Event: {self.get_event_type_display()} - {self.settlement_intent.uuid}"


class Dispute(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    settlement_intent = models.OneToOneField(
        SettlementIntent,
        on_delete=models.PROTECT,
        related_name='dispute',
        help_text=_("The disputed settlement.")
    )

    dispute_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Human-readable dispute reference (e.g., CHX-DISP-4521).")
    )

    status = models.CharField(
        max_length=30,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
        db_index=True,
        help_text=_("Current dispute resolution status.")
    )

    opened_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the dispute was opened.")
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the dispute was resolved.")
    )

    resolution_type = models.CharField(
        max_length=30,
        choices=ResolutionType.choices,
        null=True,
        blank=True,
        help_text=_("How the dispute was resolved.")
    )

    resolution_notes = models.TextField(
        blank=True,
        default='',
        help_text=_("Detailed resolution notes.")
    )

    # Evidence and Documentation
    sacco_confirmation_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("SACCO confirmation reference for manual verification.")
    )

    sacco_officer_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Name of SACCO officer who confirmed resolution.")
    )

    trustee_case_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Trustee bank case reference if escalated.")
    )

    trustee_advance_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Amount advanced by trustee while dispute is resolved.")
    )

    # Approval Trail
    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes',
        help_text=_("Operations team member who resolved the dispute.")
    )

    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_disputes',
        help_text=_("Executive who approved the resolution (for force actions).")
    )

    buyer_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the buyer was notified of the dispute.")
    )

    seller_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the seller was notified of the dispute.")
    )

    class Meta:
        verbose_name = _('Dispute')
        verbose_name_plural = _('Disputes')
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['dispute_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['opened_at']),
        ]

    def __str__(self):
        return f"Dispute {self.dispute_reference} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.dispute_reference:
            self.dispute_reference = self._generate_reference()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        import random
        import string
        prefix = 'CHX-DISP'
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}-{suffix}"

    def escalate_to_trustee(self, escalated_by):
        self.status = DisputeStatus.AWAITING_TRUSTEE
        self.save(update_fields=['status'])

        SettlementEvent.objects.create(
            settlement_intent=self.settlement_intent,
            event_type=SettlementEventType.TRUSTEE_ESCALATION,
            from_state=self.settlement_intent.state,
            to_state=self.settlement_intent.state,
            trigger='TRUSTEE_ESCALATION',
            performed_by=escalated_by,
            metadata={
                'dispute_reference': self.dispute_reference,
                'escalated_at': str(timezone.now()),
            }
        )

    def resolve(self, resolution_type, resolved_by, notes='', approved_by=None, **kwargs):
        self.status = DisputeStatus.CLOSED
        self.resolution_type = resolution_type
        self.resolved_by = resolved_by
        self.resolution_notes = notes
        self.resolved_at = timezone.now()

        if approved_by:
            self.approved_by = approved_by

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.save()

        SettlementEvent.objects.create(
            settlement_intent=self.settlement_intent,
            event_type=SettlementEventType.DISPUTE_RESOLVED,
            from_state=self.settlement_intent.state,
            to_state=self.settlement_intent.state,
            trigger=f'DISPUTE_{resolution_type}',
            performed_by=resolved_by,
            metadata={
                'dispute_reference': self.dispute_reference,
                'resolution_type': resolution_type,
                'notes': notes,
            }
        )


class SettlementLedger(BaseModel):

    settlement_intent = models.OneToOneField(
        SettlementIntent,
        on_delete=models.PROTECT,
        related_name='ledger_entry',
        help_text=_("The completed settlement.")
    )

    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ledger_purchases',
        help_text=_("The buyer.")
    )

    seller = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='ledger_sales',
        help_text=_("The seller.")
    )

    sacco = models.ForeignKey(
        'investments.SACCO',
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        help_text=_("The SACCO whose shares were traded.")
    )

    share_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text=_("Number of shares transferred.")
    )

    price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Price per share.")
    )

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Total transaction amount.")
    )

    platform_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Platform fee charged.")
    )

    net_seller_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Net amount credited to seller.")
    )

    completed_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the settlement was finalized.")
    )

    class Meta:
        verbose_name = _('Settlement Ledger')
        verbose_name_plural = _('Settlement Ledger')
        ordering = ['-completed_at']
        indexes = [
            models.Index(fields=['buyer', 'completed_at']),
            models.Index(fields=['seller', 'completed_at']),
            models.Index(fields=['sacco', 'completed_at']),
        ]

    def __str__(self):
        return f"Ledger: {self.share_quantity} shares - {self.sacco.name}"