from rest_framework import serializers

from apps.notifications.models import (
    Notification, UserDevice, NotificationPreference,
    NotificationTemplate, NotificationChannel, DevicePlatform
)


class NotificationSerializer(serializers.ModelSerializer):

    category_display = serializers.SerializerMethodField()
    channel_display = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'category', 'category_display', 'priority',
            'title', 'body', 'channel', 'channel_display',
            'status', 'is_read', 'action_url', 'action_text',
            'data', 'reference_id', 'reference_type',
            'created_at', 'read_at',
        ]
        read_only_fields = fields

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_channel_display(self, obj):
        return obj.get_channel_display()

    def get_is_read(self, obj):
        return obj.status == 'READ'


class UserDeviceSerializer(serializers.ModelSerializer):

    platform_display = serializers.SerializerMethodField()

    class Meta:
        model = UserDevice
        fields = [
            'id', 'platform', 'platform_display', 'device_name',
            'device_model', 'app_version', 'is_active',
            'last_active_at', 'registered_at',
        ]
        read_only_fields = [
            'id', 'last_active_at', 'registered_at',
        ]

    def get_platform_display(self, obj):
        return obj.get_platform_display()


class DeviceRegistrationSerializer(serializers.Serializer):

    fcm_token = serializers.CharField(required=True, max_length=500)
    platform = serializers.ChoiceField(choices=DevicePlatform.choices, required=True)
    device_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    device_model = serializers.CharField(required=False, allow_blank=True, max_length=255)
    app_version = serializers.CharField(required=False, allow_blank=True, max_length=20)


class NotificationPreferenceSerializer(serializers.ModelSerializer):

    category_display = serializers.SerializerMethodField()
    channel_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'category', 'category_display',
            'channel', 'channel_display', 'enabled',
        ]
        read_only_fields = ['id']

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_channel_display(self, obj):
        return obj.get_channel_display()


class NotificationPreferenceBulkUpdateSerializer(serializers.Serializer):

    preferences = serializers.ListField(
        child=serializers.DictField(
            child=serializers.BooleanField()
        ),
        help_text="List of preference objects with category, channel, and enabled fields."
    )