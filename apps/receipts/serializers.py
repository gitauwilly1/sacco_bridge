from rest_framework import serializers
from apps.receipts.models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):

    receipt_type_display = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'receipt_type',
            'receipt_type_display', 'amount', 'description',
            'party_name', 'verification_code',
            'generated_at', 'download_url',
        ]

    def get_receipt_type_display(self, obj):
        return obj.get_receipt_type_display()

    def get_download_url(self, obj):
        return f"/api/v1/receipts/{obj.receipt_number}/download/"