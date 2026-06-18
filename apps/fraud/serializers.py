from rest_framework import serializers
from apps.fraud.models import TransactionRiskAssessment


class RiskAssessmentSerializer(serializers.ModelSerializer):
    risk_level_display = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = TransactionRiskAssessment
        fields = [
            'id', 'user', 'user_name', 'transaction_type',
            'transaction_reference', 'amount', 'risk_score',
            'risk_level', 'risk_level_display',
            'recommended_action', 'applied_action',
            'triggers', 'velocity_24h_count',
            'is_new_device', 'is_unusual_hour',
            'is_unusual_amount', 'location_mismatch',
            'reviewed_by', 'reviewed_at', 'created_at',
        ]

    def get_risk_level_display(self, obj):
        return obj.get_risk_level_display()

    def get_user_name(self, obj):
        return obj.user.get_full_name()