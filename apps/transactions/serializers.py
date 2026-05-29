from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.serializers import BaseSerializer, DynamicFieldsMixin
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, Dispute, SettlementLedger,
    SettlementState, DisputeStatus, SettlementEventType
)


class SettlementEventSerializer(serializers.ModelSerializer):

    event_type_display = serializers.SerializerMethodField()
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SettlementEvent
        fields = [
            'id', 'event_type', 'event_type_display',
            'from_state', 'to_state', 'trigger',
            'external_reference', 'performed_by_name',
            'metadata', 'created_at',
        ]

    def get_event_type_display(self, obj):
        return obj.get_event_type_display()

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.get_full_name()
        return 'System'


class SettlementIntentSerializer(BaseSerializer, DynamicFieldsMixin):

    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    state_display = serializers.SerializerMethodField()
    events = SettlementEventSerializer(many=True, read_only=True)
    dispute_reference = serializers.SerializerMethodField()
    is_point_of_no_return = serializers.SerializerMethodField()

    class Meta:
        model = SettlementIntent
        fields = [
            'id', 'uuid', 'idempotency_key', 'state',
            'state_display', 'version', 'connection',
            'buyer', 'buyer_name', 'seller', 'seller_name',
            'share_quantity', 'price_per_share', 'total_amount',
            'platform_fee', 'net_seller_amount',
            'buyer_debit_transaction_id',
            'seller_credit_transaction_id',
            'matched_at', 'locked_at', 'buyer_debit_at',
            'seller_credit_at', 'completed_at', 'failed_at',
            'retry_count', 'error_message', 'error_code',
            'events', 'dispute_reference',
            'is_point_of_no_return',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'uuid', 'idempotency_key', 'state',
            'version', 'buyer_debit_transaction_id',
            'seller_credit_transaction_id',
            'matched_at', 'locked_at', 'buyer_debit_at',
            'seller_credit_at', 'completed_at', 'failed_at',
            'retry_count', 'error_message', 'error_code',
            'created_at', 'updated_at',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()

    def get_state_display(self, obj):
        return obj.get_state_display()

    def get_dispute_reference(self, obj):
        if hasattr(obj, 'dispute') and obj.dispute:
            return obj.dispute.dispute_reference
        return None

    def get_is_point_of_no_return(self, obj):
        return obj.is_at_point_of_no_return()


class SettlementIntentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SettlementIntent
        fields = [
            'connection', 'buyer', 'seller', 'share_quantity',
            'price_per_share', 'total_amount',
        ]

    def validate_total_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError(
                _('Total amount must be greater than zero.')
            )
        return value


class SettlementLedgerSerializer(BaseSerializer):

    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    sacco_name = serializers.SerializerMethodField()

    class Meta:
        model = SettlementLedger
        fields = [
            'id', 'settlement_intent', 'buyer', 'buyer_name',
            'seller', 'seller_name', 'sacco', 'sacco_name',
            'share_quantity', 'price_per_share', 'total_amount',
            'platform_fee', 'net_seller_amount', 'completed_at',
        ]
        read_only_fields = fields

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()

    def get_sacco_name(self, obj):
        return obj.sacco.name


class DisputeSerializer(BaseSerializer):

    settlement_uuid = serializers.SerializerMethodField()
    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Dispute
        fields = [
            'id', 'dispute_reference', 'settlement_intent',
            'settlement_uuid', 'status', 'opened_at',
            'resolved_at', 'resolution_type', 'resolution_notes',
            'buyer_name', 'seller_name',
            'sacco_confirmation_reference', 'sacco_officer_name',
            'trustee_case_number', 'trustee_advance_amount',
            'resolved_by', 'resolved_by_name',
            'approved_by', 'approved_by_name',
            'buyer_notified_at', 'seller_notified_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'dispute_reference', 'opened_at',
            'resolved_at', 'created_at', 'updated_at',
        ]

    def get_settlement_uuid(self, obj):
        return str(obj.settlement_intent.uuid)

    def get_buyer_name(self, obj):
        return obj.settlement_intent.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.settlement_intent.seller.get_full_name()

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.get_full_name()
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name()
        return None


class DisputeResolveSerializer(serializers.Serializer):

    resolution_type = serializers.CharField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    sacco_confirmation_reference = serializers.CharField(
        required=False, allow_blank=True
    )
    sacco_officer_name = serializers.CharField(
        required=False, allow_blank=True
    )
    trustee_case_number = serializers.CharField(
        required=False, allow_blank=True
    )
    trustee_advance_amount = serializers.DecimalField(
        required=False, max_digits=20, decimal_places=2
    )
    requires_executive_approval = serializers.BooleanField(default=False)
    executive_approved_by = serializers.CharField(required=False)


class SettlementTimelineSerializer(serializers.Serializer):

    nodes = serializers.ListField()

    @classmethod
    def from_settlement(cls, settlement_intent):
        nodes = []
        events = settlement_intent.events.all().order_by('created_at')

        for event in events:
            node = {
                'timestamp': event.created_at,
                'title': cls._get_node_title(event),
                'description': cls._get_node_description(event),
                'status': cls._get_node_status(event, settlement_intent),
                'icon': cls._get_node_icon(event),
            }
            nodes.append(node)

        return {'nodes': nodes}

    @classmethod
    def _get_node_title(cls, event):
        titles = {
            SettlementEventType.STATE_TRANSITION: 'State Updated',
            SettlementEventType.API_CALL: 'Processing',
            SettlementEventType.API_RESPONSE: 'Response Received',
            SettlementEventType.RECOVERY_ATTEMPT: 'Recovery Attempt',
            SettlementEventType.MANUAL_INTERVENTION: 'Manual Review',
            SettlementEventType.DISPUTE_OPENED: 'Dispute Opened',
            SettlementEventType.DISPUTE_RESOLVED: 'Dispute Resolved',
            SettlementEventType.TRUSTEE_ESCALATION: 'Trustee Engaged',
            SettlementEventType.SACCO_API_FAILURE: 'SACCO System Issue',
            SettlementEventType.COMPENSATION_TRIGGERED: 'Rollback Initiated',
        }
        return titles.get(event.event_type, event.get_event_type_display())

    @classmethod
    def _get_node_description(cls, event):
        descriptions = {
            SettlementState.MATCH_PROPOSED: 'Match identified between buyer and seller',
            SettlementState.INTENT_LOCKED: 'Funds and shares reserved',
            SettlementState.BUYER_DEBIT_INITIATED: 'Initiating debit from buyer account',
            SettlementState.BUYER_DEBIT_CONFIRMED: 'Buyer funds debited successfully',
            SettlementState.SELLER_CREDIT_INITIATED: 'Initiating credit to seller account',
            SettlementState.SELLER_CREDIT_CONFIRMED: 'Seller account credited successfully',
            SettlementState.LEDGER_FINALIZED: 'Transaction finalized and recorded',
            SettlementState.COMPENSATING: 'Rolling back transaction',
            SettlementState.REVERSED: 'Transaction fully reversed',
            SettlementState.DISPUTED_MANUAL: 'Flagged for manual review',
            SettlementState.FAILED: 'Settlement failed',
        }
        to_state = event.to_state
        return descriptions.get(to_state, f'Transitioned to {to_state}')

    @classmethod
    def _get_node_status(cls, event, settlement):
        if event.to_state == SettlementState.LEDGER_FINALIZED:
            return 'completed'
        elif event.to_state in [SettlementState.FAILED, SettlementState.REVERSED]:
            return 'failed'
        elif event.to_state == SettlementState.DISPUTED_MANUAL:
            return 'disputed'
        elif settlement.state == event.to_state:
            return 'active'
        return 'completed'

    @classmethod
    def _get_node_icon(cls, event):
        icons = {
            'completed': 'check_circle',
            'active': 'progress_circle',
            'failed': 'error_circle',
            'disputed': 'warning_circle',
        }
        return icons.get('active', 'circle')