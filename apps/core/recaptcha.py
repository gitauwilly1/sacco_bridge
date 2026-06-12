from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.recaptcha import ReCaptchaService


class ReCaptchaField(serializers.CharField):

    def __init__(self, action=None, **kwargs):
        self.recaptcha_action = action
        
        # In development, make it optional so Swagger/Postman still work
        if settings.DEBUG:
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
        # Skip in development
        if settings.DEBUG:
            return value
        
        # Verify in production
        if not value:
            raise serializers.ValidationError(_('reCAPTCHA token is required.'))
        
        result = ReCaptchaService.verify(value, action=self.recaptcha_action)
        if not result['success']:
            raise serializers.ValidationError(result['error'])
        return value

    def run_validation(self, data):
        value = super().run_validation(data)
        return self.validate_recaptcha(value)