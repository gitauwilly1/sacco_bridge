from rest_framework import serializers

from apps.analytics.models import (
    ChamaAnalytics,
    PlatformMetric,
    ReportGeneration,
    SACCOMarketAnalytics,
    ScheduledReport,
)


class PlatformMetricSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlatformMetric
        fields = [
            'id', 'metric_date', 'total_users', 'new_users',
            'verified_users', 'active_users', 'total_chamas',
            'new_chamas', 'total_chama_members',
            'total_chama_savings', 'total_chama_loans',
            'total_liquidity_requests', 'active_liquidity_requests',
            'total_connections', 'total_settlements',
            'completed_settlements', 'reversed_settlements',
            'disputed_settlements', 'total_settlement_volume',
            'total_platform_fees', 'total_premium_revenue',
            'total_saccos', 'active_saccos',
        ]
        read_only_fields = fields


class ChamaAnalyticsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChamaAnalytics
        fields = [
            'id', 'chama', 'period_start', 'period_end',
            'period_type', 'total_members', 'new_members',
            'members_left', 'active_members',
            'total_contributions', 'average_contribution',
            'on_time_rate', 'late_contributions',
            'missed_contributions', 'total_late_fees',
            'total_loans_issued', 'total_loan_amount',
            'total_interest_earned', 'loans_fully_repaid',
            'loans_in_default', 'default_rate',
            'total_meetings', 'average_attendance',
            'savings_growth', 'loan_to_savings_ratio',
        ]
        read_only_fields = fields


class SACCOMarketAnalyticsSerializer(serializers.ModelSerializer):

    class Meta:
        model = SACCOMarketAnalytics
        fields = [
            'id', 'sacco', 'metric_date',
            'average_price_per_share', 'highest_price',
            'lowest_price', 'opening_price', 'closing_price',
            'total_volume_shares', 'total_volume_amount',
            'number_of_transactions', 'active_sellers',
            'active_buyers', 'average_time_to_match',
            'average_buyer_offer', 'average_seller_ask',
            'average_spread',
        ]
        read_only_fields = fields


class ScheduledReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = ScheduledReport
        fields = [
            'id', 'name', 'report_type', 'frequency',
            'export_format', 'recipients', 'parameters',
            'is_active', 'last_generated_at', 'next_generation_at',
            'created_at',
        ]
        read_only_fields = ['id', 'last_generated_at', 'created_at']


class ReportGenerationSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportGeneration
        fields = [
            'id', 'scheduled_report', 'report_type',
            'export_format', 'file', 'parameters',
            'status', 'error_message', 'generated_by',
            'completed_at', 'created_at',
        ]
        read_only_fields = ['id', 'file', 'status', 'error_message', 'completed_at', 'created_at']