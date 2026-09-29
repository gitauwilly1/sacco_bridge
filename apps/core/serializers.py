from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty
from apps.core.models import AdminApproval
from apps.core.recaptcha import ReCaptchaService


class ReCaptchaField(serializers.CharField):

    def __init__(self, action=None, **kwargs):
        self.recaptcha_action = action
        
        # Temporary: always optional until reCAPTCHA keys are configured
        kwargs.setdefault('required', False)
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('default', 'bypass')
        
        kwargs.setdefault('write_only', True)
        kwargs.setdefault(
            'help_text',
            _('reCAPTCHA verification token. Not required in development.')
        )
        super().__init__(**kwargs)

    def validate_recaptcha(self, value):
        # Temporary bypass — always pass
        return value

    def run_validation(self, data):
        from rest_framework.fields import empty
        
        # If data is empty and field is optional, use default
        if data is empty and not self.required:
            value = self.default
        else:
            value = super().run_validation(data)
        
        return self.validate_recaptcha(value)    
class BaseSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        abstract = True


class DynamicFieldsMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'context') and self.context.get('request'):
            fields_param = self.context['request'].query_params.get('fields', None)
            if fields_param:
                allowed_fields = set(fields_param.split(','))
                existing_fields = set(self.fields.keys())
                for field_name in existing_fields - allowed_fields:
                    self.fields.pop(field_name)


class AdminApprovalSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = AdminApproval
        fields = [
            'id', 'action', 'action_display', 'target_id', 'target_repr',
            'payload', 'requested_by', 'requested_by_name', 'status',
            'status_display', 'reviewed_by', 'reviewed_by_name',
            'review_notes', 'created_at', 'reviewed_at',
        ]
        read_only_fields = [
            'id', 'requested_by', 'status', 'reviewed_by',
            'reviewed_at', 'created_at', 'reviewed_at',
        ]

    def get_requested_by_name(self, obj):
        return str(obj.requested_by) if obj.requested_by else ''

    def get_reviewed_by_name(self, obj):
        return str(obj.reviewed_by) if obj.reviewed_by else ''

    def get_action_display(self, obj):
        return obj.get_action_display()

    def get_status_display(self, obj):
        return obj.get_status_display()