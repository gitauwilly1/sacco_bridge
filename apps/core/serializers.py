from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.recaptcha import ReCaptchaService

class ReCaptchaField(serializers.CharField):

    def __init__(self, action=None, **kwargs):
        self.recaptcha_action = action
        kwargs.setdefault('write_only', True)
        kwargs.setdefault('required', True)
        kwargs.setdefault('help_text', _('reCAPTCHA verification token.'))
        super().__init__(**kwargs)

    def validate_recaptcha(self, value):
        result = ReCaptchaService.verify(value, action=self.recaptcha_action)
        if not result['success']:
            raise serializers.ValidationError(result['error'])
        return value

    def run_validation(self, data):
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