import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class SpecialCharacterValidator:

    def __init__(self, special_characters='!@#$%^&*()_+-=[]{}|;:,.<>?/~`'):
        self.special_characters = special_characters

    def validate(self, password, user=None):
        if not any(char in self.special_characters for char in password):
            raise ValidationError(
                _('Password must contain at least one special character: %(chars)s.'),
                params={'chars': self.special_characters},
            )

    def get_help_text(self):
        return _('Your password must contain at least one special character: %(chars)s.') % {
            'chars': '!@#$%^&*()_+-=[]{}|;:,.<>?/~`'
        }


class UppercaseLowercaseValidator:

    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_('Password must contain at least one uppercase letter.'))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_('Password must contain at least one lowercase letter.'))

    def get_help_text(self):
        return _('Your password must contain at least one uppercase and one lowercase letter.')


def validate_kenyan_phone_number(value):
    pattern = r'^(?:\+?254|0)?7\d{8}$'
    cleaned = re.sub(r'\s+', '', value)
    if not re.match(pattern, cleaned):
        raise ValidationError(_('%(value)s is not a valid Kenyan phone number.'), params={'value': value})


def validate_positive_amount(value):
    from decimal import Decimal
    if value <= Decimal('0.00'):
        raise ValidationError(_('Amount must be greater than zero.'))
    if value > Decimal('100000000.00'):
        raise ValidationError(_('Amount cannot exceed KSh 100,000,000.'))


def validate_share_quantity(value):
    from decimal import Decimal
    if value <= Decimal('0.0000'):
        raise ValidationError(_('Share quantity must be greater than zero.'))
    if value > Decimal('10000000.0000'):
        raise ValidationError(_('Share quantity cannot exceed 10,000,000.'))


def validate_percentage(value):
    from decimal import Decimal
    if value < Decimal('0.00'):
        raise ValidationError(_('Percentage cannot be negative.'))
    if value > Decimal('100.00'):
        raise ValidationError(_('Percentage cannot exceed 100%.'))


def validate_id_number(value):
    pattern = r'^\d{6,8}$'
    if not re.match(pattern, str(value)):
        raise ValidationError(_('%(value)s is not a valid Kenyan ID number.'), params={'value': value})