from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.serializers import BaseSerializer
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, LedgerEntry,
    SettlementReversal, SettlementState, SettlementEventTrigger
)


class SettlementEventSerializer(serializers.ModelSerializer):

    from_state_display = serializers.SerializerMethodField()
    to_state_display = serializers.SerializerMethodField()
    trigger_display = serializers.SerializerMethodField()

    class Meta:
        model = SettlementEvent
        fields = [
            'id', 'intent', 'from_state', 'from_state_display',
            'to_state', 'to_state_display', 'trigger',
            'trigger_display', 'external_ref', 'metadata',
            'timestamp', 'actor',
        ]
        read_only_fields = fields

    def get_from_state_display(self, obj):
        return obj.get_from_state_display()

    def get_to_state_display(self, obj):
        return obj.get_to_state_display()

    def get_trigger_display(self, obj):
        return obj.get_trigger_display()


class SettlementIntentSerializer(BaseSerializer):

    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    state_display = serializers.SerializerMethodField()
    events = SettlementEventSerializer(many=True, read_only=True)
    is_terminal = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = SettlementIntent
        fields = [
            'id', 'uuid', 'idempotency_key', 'state', 'state_display',
            'version', 'buyer', 'buyer_name', 'seller', 'seller_name',
            'buyer_sacco_id', 'buyer_sacco_name',
            'seller_sacco_id', 'seller_sacco_name',
            'amount', 'share_quantity', 'price_per_share',
            'platform_fee', 'net_seller_amount',
            'buyer_debit_ref', 'seller_credit_ref', 'buyer_reversal_ref',
            'connection', 'liquidity_request_id',
            'matched_at', 'locked_at', 'buyer_debited_at',
            'seller_credited_at', 'finalized_at', 'reversed_at',
            'expires_at', 'retry_count', 'max_retries',
            'dispute_opened_at', 'dispute_resolved_at',
            'dispute_resolution_type', 'dispute_resolved_by',
            'trustee_case_number', 'events', 'is_terminal', 'timeline',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'uuid', 'idempotency_key', 'state', 'version',
            'buyer_debit_ref', 'seller_credit_ref', 'buyer_reversal_ref',
            'matched_at', 'locked_at', 'buyer_debited_at',
            'seller_credited_at', 'finalized_at', 'reversed_at',
            'retry_count', 'dispute_opened_at', 'dispute_resolved_at',
            'dispute_resolution_type', 'dispute_resolved_by',
            'trustee_case_number', 'created_at', 'updated_at',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()

    def get_state_display(self, obj):
        return obj.get_state_display()

    def get_is_terminal(self, obj):
        return obj.is_terminal()

    def get_timeline(self, obj):
        state_descriptions = {
            SettlementState.MATCH_PROPOSED: {
                'label': 'Match Proposed',
                'description': 'A buyer and seller have been matched.',
                'icon': 'match',
            },
            SettlementState.INTENT_LOCKED: {
                'label': 'Funds Reserved',
                'description': 'Funds have been reserved in the buyer account.',
                'icon': 'lock',
            },
            SettlementState.BUYER_DEBIT_INITIATED: {
                'label': 'Debit Initiated',
                'description': 'Debiting the buyer account.',
                'icon': 'processing',
            },
            SettlementState.BUYER_DEBIT_CONFIRMED: {
                'label': 'Payment Confirmed',
                'description': 'Buyer payment confirmed by their SACCO.',
                'icon': 'confirmed',
            },
            SettlementState.SELLER_CREDIT_INITIATED: {
                'label': 'Crediting Seller',
                'description': 'Transferring funds to the seller account.',
                'icon': 'processing',
            },
            SettlementState.SELLER_CREDIT_CONFIRMED: {
                'label': 'Seller Credited',
                'description': 'Funds arrived in seller account.',
                'icon': 'confirmed',
            },
            SettlementState.LEDGER_FINALIZED: {
                'label': 'Complete',
                'description': 'Transaction finalized. Shares transferred.',
                'icon': 'complete',
            },
            SettlementState.COMPENSATING: {
                'label': 'Reversing',
                'description': 'Returning funds to buyer.',
                'icon': 'reversing',
            },
            SettlementState.REVERSED: {
                'label': 'Reversed',
                'description': 'Transaction reversed. All funds returned.',
                'icon': 'reversed',
            },
            SettlementState.DISPUTED_MANUAL: {
                'label': 'Under Review',
                'description': 'Our team is investigating this transaction.',
                'icon': 'disputed',
            },
            SettlementState.CLOSED_BY_TRUSTEE: {
                'label': 'Resolved by Trustee',
                'description': 'The trustee bank has resolved this transaction.',
                'icon': 'resolved',
            },
        }

        timeline = []
        for event in obj.events.all().order_by('timestamp'):
            state_info = state_descriptions.get(
                event.to_state,
                {'label': event.get_to_state_display(), 'description': ''}
            )
            timeline.append({
                'state': event.to_state,
                'label': state_info['label'],
                'description': state_info['description'],
                'icon': state_info.get('icon', 'default'),
                'timestamp': event.timestamp.isoformat(),
                'is_completed': True,
            })

        if obj.state not in [SettlementState.LEDGER_FINALIZED, SettlementState.REVERSED, SettlementState.CLOSED_BY_TRUSTEE]:
            if timeline:
                timeline[-1]['is_completed'] = False

        return timeline


class SettlementIntentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SettlementIntent
        fields = [
            'connection', 'liquidity_request_id',
            'buyer', 'seller', 'amount', 'share_quantity',
            'price_per_share', 'buyer_sacco_id', 'buyer_sacco_name',
            'seller_sacco_id', 'seller_sacco_name',
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):

    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = [
            'id', 'settlement', 'buyer', 'buyer_name',
            'seller', 'seller_name', 'sacco_id',
            'share_quantity', 'price_per_share', 'total_amount',
            'platform_fee', 'recorded_at', 'is_reversed',
        ]
        read_only_fields = fields

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()


class SettlementReversalSerializer(serializers.ModelSerializer):

    class Meta:
        model = SettlementReversal
        fields = [
            'id', 'settlement', 'reversal_type', 'amount',
            'external_ref', 'initiated_by', 'initiated_at',
            'completed_at', 'status', 'notes',
        ]
        read_only_fields = [
            'id', 'initiated_at', 'completed_at', 'status',
        ]


class DisputeResolutionSerializer(serializers.Serializer):
\
    resolution_type = serializers.ChoiceField(
        choices=[
            ('MANUAL_CREDIT_CONFIRMED', 'Manual Credit Confirmed by SACCO'),
            ('BUYER_REVERSAL_INITIATED', 'Buyer Reversal Initiated'),
            ('ESCALATED_TO_TRUSTEE', 'Escalated to Trustee'),
            ('FORCE_MARKED_SETTLED', 'Force Marked Settled'),
        ],
        required=True
    )
    sacco_confirmation_ref = serializers.CharField(
        required=False,
        help_text="SACCO confirmation reference (required for manual credit confirmation)"
    )
    sacco_officer_name = serializers.CharField(
        required=False,
        help_text="Name of SACCO officer who confirmed"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Resolution notes"
    )
    executive_approval_ref = serializers.CharField(
        required=False,
        help_text="Executive approval reference (required for force settle)"
    )