from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.serializers import BaseSerializer
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, DisputeRecord,
    DisputeEvent, LedgerEntry, SettlementState
)


class SettlementEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = SettlementEvent
        fields = [
            'id', 'from_state', 'to_state', 'trigger',
            'external_ref', 'metadata', 'timestamp', 'actor',
        ]


class SettlementIntentSerializer(BaseSerializer):

    events = SettlementEventSerializer(many=True, read_only=True)
    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    state_display = serializers.SerializerMethodField()
    is_terminal = serializers.SerializerMethodField()

    class Meta:
        model = SettlementIntent
        fields = [
            'id', 'idempotency_key', 'state', 'state_display',
            'version', 'connection', 'buyer', 'buyer_name',
            'seller', 'seller_name', 'share_quantity',
            'price_per_share', 'total_amount', 'platform_fee',
            'buyer_total_debit', 'seller_net_credit',
            'buyer_debit_transaction_id',
            'seller_credit_transaction_id',
            'reversal_transaction_id',
            'retry_count', 'max_retries',
            'last_error', 'last_error_at', 'timeout_at',
            'completed_at', 'events', 'is_terminal',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'idempotency_key', 'state', 'version',
            'platform_fee', 'buyer_total_debit', 'seller_net_credit',
            'buyer_debit_transaction_id', 'seller_credit_transaction_id',
            'reversal_transaction_id', 'retry_count',
            'last_error', 'last_error_at', 'timeout_at',
            'completed_at', 'created_at', 'updated_at',
        ]

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()

    def get_state_display(self, obj):
        return obj.get_state_display()

    def get_is_terminal(self, obj):
        return obj.is_terminal()


class SettlementTimelineSerializer(serializers.Serializer):

    nodes = serializers.ListField()

    @staticmethod
    def build_timeline(intent):
        state_labels = {
            SettlementState.MATCH_PROPOSED: {
                'label': 'Match Proposed',
                'description': 'Buyer and seller have agreed on terms.',
                'icon': 'handshake',
            },
            SettlementState.INTENT_LOCKED: {
                'label': 'Funds Reserved',
                'description': 'Buyer funds have been reserved for this transaction.',
                'icon': 'lock',
            },
            SettlementState.BUYER_DEBIT_INITIATED: {
                'label': 'Processing Payment',
                'description': 'Debiting funds from buyer SACCO account.',
                'icon': 'payment',
            },
            SettlementState.BUYER_DEBIT_CONFIRMED: {
                'label': 'Payment Confirmed',
                'description': 'Funds successfully debited from buyer.',
                'icon': 'check_circle',
            },
            SettlementState.SELLER_CREDIT_INITIATED: {
                'label': 'Transferring to Seller',
                'description': 'Crediting funds to seller SACCO account.',
                'icon': 'transfer',
            },
            SettlementState.SELLER_CREDIT_CONFIRMED: {
                'label': 'Transfer Confirmed',
                'description': 'Funds credited to seller account.',
                'icon': 'check_circle',
            },
            SettlementState.LEDGER_FINALIZED: {
                'label': 'Records Updated',
                'description': 'Share ownership and ledger records updated.',
                'icon': 'book',
            },
            SettlementState.SETTLED: {
                'label': 'Settlement Complete',
                'description': 'Transaction finalized. Funds and shares transferred.',
                'icon': 'flag',
            },
            SettlementState.COMPENSATING: {
                'label': 'Reversing Transaction',
                'description': 'Returning funds to buyer due to settlement issue.',
                'icon': 'undo',
            },
            SettlementState.DISPUTED_MANUAL: {
                'label': 'Under Review',
                'description': 'Our team is investigating a settlement issue.',
                'icon': 'warning',
            },
        }

        nodes = []
        events = intent.events.order_by('timestamp')

        for event in events:
            state_info = state_labels.get(event.to_state, {})
            nodes.append({
                'state': event.to_state,
                'label': state_info.get('label', event.to_state),
                'description': state_info.get('description', ''),
                'icon': state_info.get('icon', 'circle'),
                'timestamp': event.timestamp.isoformat(),
                'completed': event.to_state != intent.state or intent.is_terminal(),
                'current': event.to_state == intent.state,
                'is_error': event.to_state in [
                    SettlementState.COMPENSATING,
                    SettlementState.DISPUTED_MANUAL,
                ],
            })

        if intent.is_terminal() and nodes:
            nodes[-1]['completed'] = True

        return {'nodes': nodes}


class DisputeEventSerializer(serializers.ModelSerializer):

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = DisputeEvent
        fields = [
            'id', 'action', 'description', 'actor', 'actor_name',
            'evidence', 'timestamp',
        ]

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name()
        return 'System'


class DisputeRecordSerializer(BaseSerializer):

    events = DisputeEventSerializer(many=True, read_only=True)
    settlement_summary = serializers.SerializerMethodField()

    class Meta:
        model = DisputeRecord
        fields = [
            'id', 'settlement_intent', 'settlement_summary',
            'dispute_reference', 'status', 'priority',
            'affected_party', 'disputed_amount',
            'resolution_type', 'resolution_notes',
            'resolved_by', 'resolved_at',
            'trustee_case_number', 'events',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'dispute_reference', 'created_at', 'updated_at',
        ]

    def get_settlement_summary(self, obj):
        intent = obj.settlement_intent
        return {
            'id': str(intent.id),
            'buyer': intent.buyer.get_full_name(),
            'seller': intent.seller.get_full_name(),
            'amount': str(intent.total_amount),
            'state': intent.get_state_display(),
        }


class DisputeResolutionSerializer(serializers.Serializer):

    resolution_type = serializers.ChoiceField(
        choices=[
            ('MANUAL_CREDIT_CONFIRMED', 'Credit Confirmed by SACCO'),
            ('BUYER_REVERSAL_INITIATED', 'Initiate Buyer Reversal'),
            ('ESCALATED_TO_TRUSTEE', 'Escalate to Trustee'),
            ('FORCE_SETTLED', 'Force Settle'),
        ],
        required=True,
        help_text=_("Type of resolution to apply.")
    )

    notes = serializers.CharField(
        required=True,
        help_text=_("Detailed resolution notes explaining the decision.")
    )

    sacco_confirmation_ref = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("SACCO confirmation reference (if applicable).")
    )

    external_evidence = serializers.JSONField(
        required=False,
        default=dict,
        help_text=_("Additional evidence supporting the resolution.")
    )


class LedgerEntrySerializer(serializers.ModelSerializer):

    party_name = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = [
            'id', 'settlement_intent', 'entry_type', 'amount',
            'party', 'party_name', 'sacco_reference',
            'description', 'created_at',
        ]

    def get_party_name(self, obj):
        return obj.party.get_full_name()