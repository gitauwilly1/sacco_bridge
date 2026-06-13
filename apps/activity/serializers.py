from rest_framework import serializers
from apps.activity.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):

    activity_type_display = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_initials = serializers.SerializerMethodField()
    chama_name = serializers.SerializerMethodField()
    sacco_name = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_name', 'user_initials',
            'activity_type', 'activity_type_display',
            'title', 'description',
            'chama', 'chama_name', 'sacco', 'sacco_name',
            'reference_id', 'reference_type',
            'metadata', 'created_at', 'time_ago',
        ]

    def get_activity_type_display(self, obj):
        return obj.get_activity_type_display()

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_user_initials(self, obj):
        return obj.user.get_initials()

    def get_chama_name(self, obj):
        return obj.chama.name if obj.chama else None

    def get_sacco_name(self, obj):
        return obj.sacco.name if obj.sacco else None

    def get_time_ago(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at

        if diff.days > 7:
            return obj.created_at.strftime('%d %b %Y')
        elif diff.days > 0:
            return f'{diff.days}d ago'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600}h ago'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60}m ago'
        else:
            return 'Just now'