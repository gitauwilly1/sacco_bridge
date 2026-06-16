from rest_framework import serializers

from apps.escrow.models import EscrowAccount


class EscrowAccountSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()

    class Meta:
        model = EscrowAccount
        fields = [
            'id', 'settlement', 'buyer', 'buyer_name',
            'seller', 'seller_name', 'amount', 'platform_fee',
            'status', 'status_display',
            'funded_at', 'released_at', 'refunded_at',
            'created_at',
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()