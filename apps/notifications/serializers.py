from rest_framework import serializers
from apps.notifications.models import (
    Notification, UserDevice, NotificationPreference,
    NotificationCategory
)


class NotificationSerializer(serializers.ModelSerializer):

    category_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'category', 'category_display', 'priority',
            'priority_display', 'title', 'body', 'action_url',
            'action_text', 'image_url', 'data', 'is_read',
            'read_at', 'channels_sent', 'created_at',
        ]
        read_only_fields = [
            'id', 'channels_sent', 'created_at',
        ]

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()


class UserDeviceSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserDevice
        fields = [
            'id', 'firebase_token', 'device_type',
            'device_name', 'is_active', 'last_active_at',
            'app_version',
        ]
        read_only_fields = ['id', 'last_active_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):

    category_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'category', 'category_display',
            'in_app_enabled', 'push_enabled',
            'sms_enabled', 'email_enabled',
            'quiet_hours_start', 'quiet_hours_end',
        ]
        read_only_fields = ['id']

    def get_category_display(self, obj):
        return obj.get_category_display()