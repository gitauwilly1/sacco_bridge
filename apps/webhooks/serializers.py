from rest_framework import serializers

from apps.webhooks.models import WebhookDelivery, WebhookSubscription


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = [
            'id', 'name', 'url', 'secret', 'is_active',
            'events', 'retry_limit', 'last_delivery_at',
            'failed_count', 'created_at',
        ]
        read_only_fields = ['id', 'secret', 'last_delivery_at', 'failed_count', 'created_at']


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'subscription', 'event_type', 'status',
            'response_code', 'attempt_count',
            'created_at', 'completed_at',
        ]