from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.serializers import BaseSerializer, DynamicFieldsMixin
from apps.investments.models import (
    SACCO,
    BuyerInterest,
    Connection,
    LiquidityRequest,
    LiquidityRequestStatus,
    Offer,
    SACCOMemberHolding,
    SACCOShareClass,
)


class SACCOShareClassSerializer(BaseSerializer):

    class Meta:
        model = SACCOShareClass
        fields = [
            'id', 'sacco', 'share_class', 'nominal_value',
            'total_issued', 'minimum_holding', 'is_transferable',
            'lock_in_period_months', 'dividend_eligible', 'voting_rights',
        ]
        read_only_fields = ['id']


class SACCOSerializer(BaseSerializer, DynamicFieldsMixin):

    share_classes = SACCOShareClassSerializer(many=True, read_only=True)
    active_listings = serializers.SerializerMethodField()
    estimated_share_value = serializers.SerializerMethodField()

    class Meta:
        model = SACCO
        fields = [
            'id', 'name', 'registration_number', 'sasra_tier',
            'status', 'description', 'website', 'logo',
            'total_assets', 'total_members', 'total_shares_outstanding',
            'dividend_rate', 'dividend_year',
            'last_disclosure_date', 'disclosure_due_date',
            'trading_halted', 'halt_reason',
            'share_classes', 'active_listings', 'estimated_share_value',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'trading_halted', 'last_disclosure_date',
            'created_at', 'updated_at',
        ]

    def get_active_listings(self, obj):
        return obj.liquidity_requests.filter(
            status=LiquidityRequestStatus.ACTIVE
        ).count()

    def get_estimated_share_value(self, obj):
        recent_offers = Offer.objects.filter(
            connection__liquidity_request__sacco=obj,
            status='ACCEPTED'
        ).order_by('-created_at')[:10]

        if recent_offers.exists():
            avg_price = sum(
                o.price_per_share for o in recent_offers
            ) / recent_offers.count()
            return str(avg_price.quantize(Decimal('0.01')))
        return None


class SACCOMemberHoldingSerializer(BaseSerializer):

    sacco_name = serializers.SerializerMethodField()
    share_class_name = serializers.SerializerMethodField()
    available_shares = serializers.SerializerMethodField()
    estimated_value = serializers.SerializerMethodField()

    class Meta:
        model = SACCOMemberHolding
        fields = [
            'id', 'user', 'sacco', 'sacco_name', 'share_class',
            'share_class_name', 'total_shares', 'reserved_shares',
            'available_shares', 'member_since', 'member_number',
            'verification_status', 'last_verified_at',
            'estimated_value', 'created_at',
        ]
        read_only_fields = [
            'id', 'total_shares', 'reserved_shares',
            'verification_status', 'last_verified_at', 'created_at',
        ]

    def get_sacco_name(self, obj):
        return obj.sacco.name

    def get_share_class_name(self, obj):
        return obj.share_class.get_share_class_display()

    def get_available_shares(self, obj):
        return str(obj.available_shares)

    def get_estimated_value(self, obj):
        recent_offers = Offer.objects.filter(
            connection__liquidity_request__sacco=obj.sacco,
            status='ACCEPTED'
        ).order_by('-created_at')[:10]

        if recent_offers.exists():
            avg_price = sum(
                o.price_per_share for o in recent_offers
            ) / recent_offers.count()
            estimated = obj.available_shares * avg_price
            return str(estimated.quantize(Decimal('0.01')))
        return None


class LiquidityRequestSerializer(BaseSerializer, DynamicFieldsMixin):

    seller_name = serializers.SerializerMethodField()
    sacco_name = serializers.SerializerMethodField()
    share_class_name = serializers.SerializerMethodField()
    buyer_interest_count = serializers.SerializerMethodField()
    holding_available = serializers.SerializerMethodField()

    class Meta:
        model = LiquidityRequest
        fields = [
            'id', 'seller', 'seller_name', 'sacco', 'sacco_name',
            'share_class', 'share_class_name', 'share_quantity',
            'expected_price_per_share', 'minimum_price_per_share',
            'total_expected_value', 'status', 'urgency',
            'allow_institutional_buyers', 'expires_at', 'notes',
            'holding', 'holding_available',
            'buyer_interest_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'seller', 'status', 'total_expected_value',
            'expires_at', 'created_at', 'updated_at',
        ]

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()

    def get_sacco_name(self, obj):
        return obj.sacco.name

    def get_share_class_name(self, obj):
        return obj.share_class.get_share_class_display()

    def get_buyer_interest_count(self, obj):
        return obj.buyer_interests.filter(is_active=True).count()

    def get_holding_available(self, obj):
        if obj.holding:
            return str(obj.holding.available_shares)
        return None


class LiquidityRequestCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = LiquidityRequest
        fields = [
            'sacco', 'share_class', 'holding', 'share_quantity',
            'expected_price_per_share', 'minimum_price_per_share',
            'urgency', 'allow_institutional_buyers', 'notes',
        ]

    def validate_share_quantity(self, value):
        holding_id = self.initial_data.get('holding')
        if holding_id:
            from apps.investments.models import SACCOMemberHolding
            try:
                holding = SACCOMemberHolding.objects.get(id=holding_id)
                if value > holding.available_shares:
                    raise serializers.ValidationError(
                        _('Insufficient available shares. Available: %(available)s') % {
                            'available': holding.available_shares
                        }
                    )
            except SACCOMemberHolding.DoesNotExist:
                pass
        return value


class BuyerInterestSerializer(BaseSerializer):

    buyer_name = serializers.SerializerMethodField()
    buyer_trust_score = serializers.SerializerMethodField()
    liquidity_request_summary = serializers.SerializerMethodField()

    class Meta:
        model = BuyerInterest
        fields = [
            'id', 'liquidity_request', 'liquidity_request_summary',
            'buyer', 'buyer_name', 'buyer_trust_score',
            'is_active', 'buyer_message', 'viewed_by_seller',
            'created_at',
        ]
        read_only_fields = ['id', 'viewed_by_seller', 'created_at']

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_buyer_trust_score(self, obj):
        return str(obj.buyer.trust_score)

    def get_liquidity_request_summary(self, obj):
        return f"{obj.liquidity_request.share_quantity} shares in {obj.liquidity_request.sacco.name}"


class OfferSerializer(BaseSerializer):

    offered_by_name = serializers.SerializerMethodField()
    connection_status = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            'id', 'connection', 'offered_by', 'offered_by_name',
            'price_per_share', 'quantity', 'total_amount',
            'status', 'message', 'connection_status',
            'responded_at', 'created_at',
        ]
        read_only_fields = [
            'id', 'offered_by', 'total_amount', 'status',
            'responded_at', 'created_at',
        ]

    def get_offered_by_name(self, obj):
        return obj.offered_by.get_full_name()

    def get_connection_status(self, obj):
        return obj.connection.status


class ConnectionSerializer(BaseSerializer, DynamicFieldsMixin):

    seller_name = serializers.SerializerMethodField()
    buyer_name = serializers.SerializerMethodField()
    sacco_name = serializers.SerializerMethodField()
    offers = OfferSerializer(many=True, read_only=True)
    latest_offer = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = [
            'id', 'liquidity_request', 'buyer', 'buyer_name',
            'seller', 'seller_name', 'sacco_name', 'status',
            'agreed_price_per_share', 'agreed_quantity',
            'total_amount', 'settlement_intent_id',
            'accepted_at', 'settled_at', 'offers', 'latest_offer',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'agreed_price_per_share',
            'agreed_quantity', 'total_amount', 'settlement_intent_id',
            'accepted_at', 'settled_at', 'created_at', 'updated_at',
        ]

    def get_seller_name(self, obj):
        return obj.seller.get_full_name()

    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name()

    def get_sacco_name(self, obj):
        return obj.liquidity_request.sacco.name

    def get_latest_offer(self, obj):
        latest = obj.offers.first()
        if latest:
            return OfferSerializer(latest).data
        return None