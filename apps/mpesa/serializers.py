from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.mpesa.models import MpesaTransaction, MpesaTransactionType


class StkPushRequestSerializer(serializers.Serializer):

    phone_number = serializers.CharField(
        required=True,
        help_text=_("Phone number to receive the STK Push (07XX or 2547XX).")
    )
    amount = serializers.DecimalField(
        required=True,
        max_digits=15,
        decimal_places=2,
        help_text=_("Amount to pay in KSh.")
    )
    transaction_type = serializers.ChoiceField(
        choices=MpesaTransactionType.choices,
        default=MpesaTransactionType.CHAMA_CONTRIBUTION,
        help_text=_("Type of transaction.")
    )
    chama_id = serializers.UUIDField(
        required=False,
        help_text=_("Chama ID if this is a chama payment.")
    )
    contribution_id = serializers.UUIDField(
        required=False,
        help_text=_("Contribution ID if this is for a specific contribution.")
    )
    account_reference = serializers.CharField(
        required=False,
        max_length=12,
        default='SaccoBridge',
        help_text=_("Account reference for the transaction.")
    )
    transaction_description = serializers.CharField(
        required=False,
        max_length=13,
        default='Payment',
        help_text=_("Description of the transaction.")
    )

    def validate_amount(self, value):
        from decimal import Decimal
        if value < Decimal('1.00'):
            raise serializers.ValidationError(_('Amount must be at least KSh 1.'))
        if value > Decimal('150000.00'):
            raise serializers.ValidationError(_('Amount cannot exceed KSh 150,000.'))
        return value


class StkPushResponseSerializer(serializers.Serializer):

    transaction_id = serializers.UUIDField()
    checkout_request_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()


class MpesaTransactionSerializer(serializers.ModelSerializer):

    transaction_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = MpesaTransaction
        fields = [
            'transaction_id', 'merchant_request_id', 'checkout_request_id',
            'mpesa_receipt_number', 'transaction_type', 'transaction_type_display',
            'phone_number', 'amount', 'status', 'status_display',
            'account_reference', 'transaction_description',
            'initiated_at', 'completed_at', 'failed_at',
            'error_message', 'created_at',
        ]

    def get_transaction_type_display(self, obj):
        return obj.get_transaction_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()