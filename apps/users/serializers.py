import logging
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

from apps.core.serializers import BaseSerializer, DynamicFieldsMixin
from apps.core.utils import generate_otp
from apps.users.models import User, UserProfile, UserRole, Role, LoginHistory, IDVerificationStatus

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )
    accepted_terms = serializers.BooleanField(required=True)
    accepted_privacy = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ['email', 'phone_number', 'first_name', 'last_name', 'password', 'password_confirm', 'accepted_terms', 'accepted_privacy']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_('A user with this email address already exists.'))
        return value.lower().strip()

    def validate_phone_number(self, value):
        import re
        cleaned = re.sub(r'\s+', '', value)
        if not re.match(r'^(?:\+?254|0)[17]\d{8}$', cleaned):
            raise serializers.ValidationError(_('Enter a valid Kenyan phone number.'))
        if User.objects.filter(phone_number=cleaned).exists():
            raise serializers.ValidationError(_('A user with this phone number already exists.'))
        return cleaned

    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match.')})
        if not data.get('accepted_terms'):
            raise serializers.ValidationError({'accepted_terms': _('You must accept the Terms of Service.')})
        if not data.get('accepted_privacy'):
            raise serializers.ValidationError({'accepted_privacy': _('You must accept the Privacy Policy.')})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.pop('accepted_terms')
        validated_data.pop('accepted_privacy')
        password = validated_data.pop('password')

        user = User.objects.create_user(password=password, **validated_data)
        # UserProfile is created automatically by the post_save signal.
        # Do NOT call UserProfile.objects.create(user=user) here.

        user.email_verification_code = generate_otp()
        user.phone_verification_code = generate_otp()
        user.email_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.phone_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.save()

        logger.info(f"New user registered: {user.email}", extra={'user_id': str(user.id)})
        return user


class UserLoginSerializer(serializers.Serializer):

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
    device_info = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                _('No account found with this email address.'),
                code='no_account'
            )

        if user.is_account_locked():
            remaining = user.account_locked_until - timezone.now()
            minutes = int(remaining.total_seconds() / 60)
            raise AuthenticationFailed(
                _('Account temporarily locked. Try again in %(minutes)d minutes.') % {
                    'minutes': max(1, minutes)
                },
                code='account_locked'
            )

        if not user.is_active:
            raise AuthenticationFailed(
                _('This account has been deactivated.'),
                code='account_inactive'
            )

        request = self.context.get('request')
        authenticated_user = authenticate(request=request, email=email, password=password)

        if not authenticated_user:
            try:
                user_obj = User.objects.get(email__iexact=email)
                user_obj.increment_failed_login()
            except User.DoesNotExist:
                pass
            raise AuthenticationFailed(
                _('Invalid email or password.'),
                code='invalid_credentials'
            )

        authenticated_user.reset_failed_login()

        LoginHistory.objects.create(
            user=authenticated_user,
            ip_address=self.context.get('ip_address', ''),
            user_agent=self.context.get('user_agent', ''),
            device_type=data.get('device_info', 'unknown'),
            login_successful=True
        )

        data['user'] = authenticated_user
        return data

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['phone_number'] = user.phone_number
        token['full_name'] = user.get_full_name()
        token['roles'] = list(user.user_roles.filter(is_active=True).values_list('role', flat=True))
        token['trust_score'] = str(user.trust_score)
        token['email_verified'] = user.email_verified
        token['phone_verified'] = user.phone_verified
        token['two_factor_enabled'] = user.two_factor_enabled
        return token


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    device_info = serializers.CharField(required=False, allow_blank=True)


class TwoFactorSetupSerializer(serializers.Serializer):
    enable = serializers.BooleanField(required=True)
    totp_code = serializers.CharField(required=False, max_length=6, min_length=6)


class TwoFactorVerifySerializer(serializers.Serializer):
    totp_code = serializers.CharField(required=True, max_length=6, min_length=6)
    session_token = serializers.CharField(required=True)


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=6, min_length=6)

    def validate(self, data):
        email = data.get('email', '').lower().strip()
        otp = data.get('otp', '')
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': _('No account found.')})
        if user.email_verified:
            raise serializers.ValidationError({'email': _('Email already verified.')})
        if user.email_verification_expiry and user.email_verification_expiry < timezone.now():
            raise serializers.ValidationError({'otp': _('Code expired.')})
        if user.email_verification_code != otp:
            raise serializers.ValidationError({'otp': _('Invalid code.')})
        data['user'] = user
        return data


class PhoneVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    otp = serializers.CharField(required=True, max_length=6, min_length=6)

    def validate(self, data):
        import re
        phone = re.sub(r'\s+', '', data.get('phone_number', ''))
        otp = data.get('otp', '')
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError({'phone_number': _('No account found.')})
        if user.phone_verified:
            raise serializers.ValidationError({'phone_number': _('Phone already verified.')})
        if user.phone_verification_expiry and user.phone_verification_expiry < timezone.now():
            raise serializers.ValidationError({'otp': _('Code expired.')})
        if user.phone_verification_code != otp:
            raise serializers.ValidationError({'otp': _('Invalid code.')})
        data['user'] = user
        return data


class ResendVerificationSerializer(serializers.Serializer):
    contact = serializers.CharField(required=True)
    method = serializers.ChoiceField(choices=['email', 'sms'], required=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, validators=[validate_password], style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(required=True, style={'input_type': 'password'})


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password], style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(required=True, style={'input_type': 'password'})


class UserProfileSerializer(BaseSerializer, DynamicFieldsMixin):
    full_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'full_name', 'initials', 'profile_picture', 'date_of_birth',
            'email_verified', 'phone_verified', 'id_verification_status',
            'roles', 'trust_score', 'two_factor_enabled',
            'preferred_language', 'notification_settings',
            'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'email', 'phone_number', 'email_verified', 'phone_verified', 'id_verification_status', 'trust_score', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_initials(self, obj):
        return obj.get_initials()

    def get_roles(self, obj):
        return list(obj.user_roles.filter(is_active=True).values('role', 'assigned_at'))


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'profile_picture',
            'date_of_birth', 'preferred_language',
            'notification_settings',
        ]


class UserProfileDetailSerializer(BaseSerializer):
    user = UserProfileSerializer(read_only=True)
    occupation = serializers.CharField(required=False, allow_blank=True)
    employer = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ['user', 'occupation', 'employer', 'address_line_1', 'address_line_2', 'city', 'county', 'postal_code', 'monthly_income_range', 'source_of_funds', 'risk_tolerance', 'investment_experience']


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = ['login_timestamp', 'ip_address', 'device_type', 'login_successful', 'failure_reason', 'location_city']


class PhoneNumberUpdateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)

    def validate_phone_number(self, value):
        import re
        cleaned = re.sub(r'\s+', '', value)
        if not re.match(r'^(?:\+?254|0)[17]\d{8}$', cleaned):
            raise serializers.ValidationError(_('Enter a valid Kenyan phone number.'))
        if User.objects.filter(phone_number=cleaned).exists():
            raise serializers.ValidationError(_('A user with this phone number already exists.'))
        return cleaned