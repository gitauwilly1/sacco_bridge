from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty
from apps.core.recaptcha import ReCaptchaService


class ReCaptchaField(serializers.CharField):

    def __init__(self, action=None, **kwargs):
        self.recaptcha_action = action
        
        from django.conf import settings
        recaptcha_configured = bool(
            getattr(settings, 'RECAPTCHA_SITE_KEY', '') and 
            getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
        )
        
        if not recaptcha_configured or settings.DEBUG:
            kwargs.setdefault('required', False)
            kwargs.setdefault('allow_blank', True)
            kwargs.setdefault('default', 'dev-bypass')
        else:
            kwargs.setdefault('required', True)
        
        kwargs.setdefault('write_only', True)
        kwargs.setdefault(
            'help_text',
            _('reCAPTCHA verification token. Not required in development.')
        )
        super().__init__(**kwargs)

    def validate_recaptcha(self, value):
        from django.conf import settings
        
        recaptcha_configured = bool(
            getattr(settings, 'RECAPTCHA_SITE_KEY', '') and 
            getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
        )
        
        # Skip if not configured
        if not recaptcha_configured or settings.DEBUG:
            return value
        
        # Verify in production
        if not value:
            raise serializers.ValidationError(_('reCAPTCHA token is required.'))
        
        result = ReCaptchaService.verify(value, action=self.recaptcha_action)
        if not result['success']:
            raise serializers.ValidationError(result['error'])
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