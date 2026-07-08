from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.support.models import SupportMessage, SupportTicket, TicketPriority, TicketStatus


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_staff = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ['id', 'message', 'is_internal', 'attachment', 'author_name', 'is_staff', 'created_at']
        read_only_fields = ['id', 'author_name', 'is_staff', 'created_at']

    def get_author_name(self, obj):
        return obj.author.get_full_name()

    def get_is_staff(self, obj):
        return obj.author.is_staff


class SupportTicketListSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = ['id', 'title', 'category', 'category_display', 'status', 'status_display', 'priority', 'priority_display', 'message_count', 'created_at', 'updated_at']
        read_only_fields = fields

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_message_count(self, obj):
        return obj.messages.count()


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['title', 'description', 'category']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    messages = SupportMessageSerializer(many=True, read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = ['id', 'title', 'description', 'category', 'category_display', 'status', 'status_display', 'priority', 'priority_display', 'assigned_to', 'assigned_to_name', 'messages', 'created_at', 'updated_at', 'resolved_at', 'closed_at']
        read_only_fields = fields

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name()
        return None


class TicketActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['assign', 'update_status', 'update_priority', 'add_note'])
    user_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=TicketStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TicketPriority.choices, required=False)
    note = serializers.CharField(required=False)
