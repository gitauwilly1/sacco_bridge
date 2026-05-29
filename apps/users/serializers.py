import logging
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.serializers import BaseSerializer, DynamicFieldsMixin
from apps.core.utils import generate_otp, mask_phone_number, mask_email
from apps.users.models import (
    User, UserProfile, UserRole, Role, LoginHistory,
    IDVerificationStatus
)

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text=_(
            'Password must be at least 12 characters and contain '
            'uppercase, lowercase, numbers, and special characters.'
        )
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text=_('Confirm your password.')
    )
    accepted_terms = serializers.BooleanField(
        required=True,
        help_text=_('Must accept the Terms of Service and Risk Disclosure Statement.')
    )
    accepted_privacy = serializers.BooleanField(
        required=True,
        help_text=_('Must accept the Privacy Policy.')
    )

    class Meta:
        model = User
        fields = [
            'email', 'phone_number', 'first_name', 'last_name',
            'password', 'password_confirm', 'accepted_terms',
            'accepted_privacy',
        ]
        extra_kwargs = {
            'email': {'required': True},
            'phone_number': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                _('A user with this email address already exists.')
            )
        return value.lower().strip()

    def validate_phone_number(self, value):
        import re
        cleaned = re.sub(r'\s+', '', value)

        if not re.match(r'^(?:\+?254|0)?7\d{8}$', cleaned):
            raise serializers.ValidationError(
                _('Enter a valid Kenyan phone number (e.g., 0712345678).')
            )

        if User.objects.filter(phone_number=cleaned).exists():
            raise serializers.ValidationError(
                _('A user with this phone number already exists.')
            )
        return cleaned

    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': _('Passwords do not match.')
            })

        if not data.get('accepted_terms'):
            raise serializers.ValidationError({
                'accepted_terms': _('You must accept the Terms of Service.')
            })

        if not data.get('accepted_privacy'):
            raise serializers.ValidationError({
                'accepted_privacy': _('You must accept the Privacy Policy.')
            })

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.pop('accepted_terms')
        validated_data.pop('accepted_privacy')

        password = validated_data.pop('password')

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        UserProfile.objects.create(user=user)

        email_otp = generate_otp()
        phone_otp = generate_otp()

        user.email_verification_code = email_otp
        user.phone_verification_code = phone_otp
        user.email_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.phone_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.save()

        logger.info(
            f"New user registered: {user.email}",
            extra={'user_id': str(user.id)}
        )

        return user


class UserLoginSerializer(serializers.Serializer):

    email = serializers.EmailField(
        required=True,
        help_text=_('Registered email address.')
    )
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        help_text=_('Account password.')
    )
    device_info = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_('Device information for security logging.')
    )

    def validate(self, data):
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': _('No account found with this email address.')
            })

        if user.is_account_locked():
            remaining_time = user.account_locked_until - timezone.now()
            minutes = int(remaining_time.total_seconds() / 60)
            raise serializers.ValidationError({
                'email': _(
                    'Account is temporarily locked due to multiple failed attempts. '
                    'Please try again in %(minutes)d minutes.'
                ) % {'minutes': max(1, minutes)}
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'email': _('This account has been deactivated. Please contact support.')
            })

        user = authenticate(email=email, password=password)

        if not user:
            try:
                user_obj = User.objects.get(email__iexact=email)
                user_obj.increment_failed_login()
            except User.DoesNotExist:
                pass
            raise serializers.ValidationError({
                'password': _('Invalid email or password. Please try again.')
            })

        user.reset_failed_login()

        LoginHistory.objects.create(
            user=user,
            ip_address=self.context.get('ip_address', ''),
            user_agent=self.context.get('user_agent', ''),
            device_type=self.get_device_type(data.get('device_info', '')),
            login_successful=True
        )

        data['user'] = user
        return data

    def get_device_type(self, device_info):
        """
        Determine device type from user agent or device info.
        """
        if not device_info:
            return 'unknown'
        device_info_lower = device_info.lower()
        if 'mobile' in device_info_lower or 'android' in device_info_lower or 'iphone' in device_info_lower:
            return 'mobile'
        elif 'tablet' in device_info_lower or 'ipad' in device_info_lower:
            return 'tablet'
        else:
            return 'desktop'


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['phone_number'] = user.phone_number
        token['full_name'] = user.get_full_name()
        token['roles'] = list(
            user.user_roles.filter(is_active=True).values_list('role', flat=True)
        )
        token['trust_score'] = str(user.trust_score)
        token['email_verified'] = user.email_verified
        token['phone_verified'] = user.phone_verified
        token['two_factor_enabled'] = user.two_factor_enabled
        return token


class TokenResponseSerializer(serializers.Serializer):

    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField()
    user = serializers.DictField()


class EmailVerificationSerializer(serializers.Serializer):

    email = serializers.EmailField(
        required=True,
        help_text=_('Email address to verify.')
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text=_('6-digit verification code sent to your email.')
    )

    def validate(self, data):
        email = data.get('email', '').lower().strip()
        otp = data.get('otp', '')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': _('No account found with this email address.')
            })

        if user.email_verified:
            raise serializers.ValidationError({
                'email': _('This email is already verified.')
            })

        if not user.email_verification_code:
            raise serializers.ValidationError({
                'otp': _('No verification code was requested. Please request a new code.')
            })

        if user.email_verification_expiry and user.email_verification_expiry < timezone.now():
            raise serializers.ValidationError({
                'otp': _('Verification code has expired. Please request a new code.')
            })

        if user.email_verification_code != otp:
            raise serializers.ValidationError({
                'otp': _('Invalid verification code. Please try again.')
            })

        data['user'] = user
        return data


class PhoneVerificationSerializer(serializers.Serializer):

    phone_number = serializers.CharField(
        required=True,
        help_text=_('Phone number to verify.')
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text=_('6-digit verification code sent via SMS.')
    )

    def validate(self, data):
        import re
        phone = re.sub(r'\s+', '', data.get('phone_number', ''))
        otp = data.get('otp', '')

        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'phone_number': _('No account found with this phone number.')
            })

        if user.phone_verified:
            raise serializers.ValidationError({
                'phone_number': _('This phone number is already verified.')
            })

        if not user.phone_verification_code:
            raise serializers.ValidationError({
                'otp': _('No verification code was requested. Please request a new code.')
            })

        if user.phone_verification_expiry and user.phone_verification_expiry < timezone.now():
            raise serializers.ValidationError({
                'otp': _('Verification code has expired. Please request a new code.')
            })

        if user.phone_verification_code != otp:
            raise serializers.ValidationError({
                'otp': _('Invalid verification code. Please try again.')
            })

        data['user'] = user
        return data


class ResendVerificationSerializer(serializers.Serializer):

    contact = serializers.CharField(
        required=True,
        help_text=_('Email address or phone number for verification.')
    )
    method = serializers.ChoiceField(
        choices=['email', 'sms'],
        required=True,
        help_text=_('Verification method: email or sms.')
    )

    def validate(self, data):
        contact = data.get('contact', '').strip()
        method = data.get('method')

        if method == 'email':
            try:
                user = User.objects.get(email__iexact=contact)
                if user.email_verified:
                    raise serializers.ValidationError({
                        'contact': _('This email is already verified.')
                    })
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    'contact': _('No account found with this email address.')
                })
        elif method == 'sms':
            import re
            phone = re.sub(r'\s+', '', contact)
            try:
                user = User.objects.get(phone_number=phone)
                if user.phone_verified:
                    raise serializers.ValidationError({
                        'contact': _('This phone number is already verified.')
                    })
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    'contact': _('No account found with this phone number.')
                })

        data['user'] = user
        return data


class GoogleAuthSerializer(serializers.Serializer):

    id_token = serializers.CharField(
        required=True,
        help_text=_('Google ID token from the OAuth2 flow.')
    )
    device_info = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_('Device information for security logging.')
    )

    def validate_id_token(self, value):
        from google.oauth2 import id_token
        from google.auth.transport import requests

        try:
            idinfo = id_token.verify_oauth2_token(
                value,
                requests.Request(),
                clock_skew_in_seconds=60
            )

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise serializers.ValidationError(
                    _('Invalid token issuer.')
                )

            return idinfo

        except ValueError as e:
            raise serializers.ValidationError(
                _('Invalid Google token: %(error)s') % {'error': str(e)}
            )


class TwoFactorSetupSerializer(serializers.Serializer):

    enable = serializers.BooleanField(
        required=True,
        help_text=_('Whether to enable or disable 2FA.')
    )
    totp_code = serializers.CharField(
        required=False,
        max_length=6,
        min_length=6,
        help_text=_('TOTP code from authenticator app for verification.')
    )

    def validate(self, data):
        if data.get('enable') and not data.get('totp_code'):
            raise serializers.ValidationError({
                'totp_code': _('TOTP code is required to enable two-factor authentication.')
            })
        return data


class TwoFactorVerifySerializer(serializers.Serializer):

    totp_code = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text=_('6-digit TOTP code from your authenticator app.')
    )
    session_token = serializers.CharField(
        required=True,
        help_text=_('Temporary session token from the initial login step.')
    )


class PasswordChangeSerializer(serializers.Serializer):

    current_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        help_text=_('Your current password.')
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text=_('New password meeting all complexity requirements.')
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        help_text=_('Confirm your new password.')
    )

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                _('Current password is incorrect.')
            )
        return value

    def validate(self, data):
        if data.get('new_password') != data.get('new_password_confirm'):
            raise serializers.ValidationError({
                'new_password_confirm': _('New passwords do not match.')
            })

        if data.get('current_password') == data.get('new_password'):
            raise serializers.ValidationError({
                'new_password': _('New password must be different from your current password.')
            })

        return data


class PasswordResetRequestSerializer(serializers.Serializer):

    email = serializers.EmailField(
        required=True,
        help_text=_('Email address associated with your account.')
    )

    def validate_email(self, value):
        email = value.lower().strip()
        try:
            user = User.objects.get(email__iexact=email)
            if not user.is_active:
                raise serializers.ValidationError(
                    _('This account has been deactivated.')
                )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _('No account found with this email address.')
            )
        return email


class PasswordResetConfirmSerializer(serializers.Serializer):

    token = serializers.CharField(
        required=True,
        help_text=_('Password reset token sent to your email.')
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text=_('New password meeting all complexity requirements.')
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        help_text=_('Confirm your new password.')
    )

    def validate(self, data):
        if data.get('new_password') != data.get('new_password_confirm'):
            raise serializers.ValidationError({
                'new_password_confirm': _('Passwords do not match.')
            })
        return data


class UserProfileSerializer(BaseSerializer, DynamicFieldsMixin):

    full_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    trust_score = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'full_name', 'initials', 'profile_picture', 'date_of_birth',
            'email_verified', 'phone_verified', 'id_verification_status',
            'roles', 'trust_score', 'two_factor_enabled',
            'preferred_language', 'notification_preferences',
            'date_joined', 'last_login',
        ]
        read_only_fields = [
            'id', 'email', 'phone_number', 'email_verified',
            'phone_verified', 'id_verification_status',
            'trust_score', 'date_joined', 'last_login',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_initials(self, obj):
        return obj.get_initials()

    def get_roles(self, obj):
        return list(
            obj.user_roles.filter(is_active=True).values('role', 'assigned_at')
        )


class UserProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'profile_picture',
            'date_of_birth', 'preferred_language',
            'notification_preferences',
        ]

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(_('First name cannot be empty.'))
        return value.strip()

    def validate_last_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(_('Last name cannot be empty.'))
        return value.strip()


class UserProfileDetailSerializer(BaseSerializer):

    user = UserProfileSerializer(read_only=True)
    occupation = serializers.CharField(required=False, allow_blank=True)
    employer = serializers.CharField(required=False, allow_blank=True)
    address_line_1 = serializers.CharField(required=False, allow_blank=True)
    address_line_2 = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    county = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)
    risk_tolerance = serializers.CharField(required=False)
    investment_experience = serializers.CharField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'occupation', 'employer', 'address_line_1',
            'address_line_2', 'city', 'county', 'postal_code',
            'monthly_income_range', 'source_of_funds',
            'risk_tolerance', 'investment_experience',
        ]


class LoginHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = LoginHistory
        fields = [
            'login_timestamp', 'ip_address', 'device_type',
            'login_successful', 'failure_reason', 'location_city',
        ]


class SessionSerializer(serializers.Serializer):

    session_id = serializers.CharField()
    device_type = serializers.CharField()
    ip_address = serializers.CharField()
    location_city = serializers.CharField()
    last_active = serializers.DateTimeField()
    is_current = serializers.BooleanField()
    user_agent = serializers.CharField()