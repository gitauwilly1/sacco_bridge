import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from apps.core.exceptions import AuthenticationFailedError, VerificationError
from apps.users.models import LoginHistory
from apps.users.serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    EmailVerificationSerializer, PhoneVerificationSerializer,
    ResendVerificationSerializer, GoogleAuthSerializer,
    TwoFactorSetupSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, UserProfileDetailSerializer,
    LoginHistorySerializer,
)
from apps.users.services import AuthenticationService, TwoFactorService, GoogleAuthService

logger = logging.getLogger(__name__)
User = get_user_model()

class RegistrationView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    @extend_schema(tags=['Authentication'], summary='Register a new user', description='Creates a new user account with email and phone verification.')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            AuthenticationService.send_verification_email(user)
        except Exception:
            logger.warning(f"Failed to send verification email to {user.email}")

        AuthenticationService.send_verification_sms(user)

        return Response({
            'success': True,
            'data': {
                'user_id': str(user.id),
                'email': user.email,
                'phone_number': user.phone_number,
                'message': _('Registration successful. Please verify your email and phone number.'),
            },
            'message': _('Registration successful'),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer

    @extend_schema(tags=['Authentication'], summary='User login', description='Authenticate user credentials and return JWT tokens.')
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={
            'request': request,
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        })
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user.two_factor_enabled:
            session_token = RefreshToken.for_user(user)
            session_token['purpose'] = '2fa_pending'
            return Response({
                'success': True,
                'data': {
                    'requires_2fa': True,
                    'session_token': str(session_token.access_token),
                    'message': _('Please enter your authenticator code to complete login.'),
                },
            })

        token_data = AuthenticationService.get_token_response(user)
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip(request)
        user.last_login_device = request.META.get('HTTP_USER_AGENT', '')
        user.save(update_fields=['last_login', 'last_login_ip', 'last_login_device'])

        return Response({'success': True, 'data': token_data, 'message': _('Login successful')})

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

class TwoFactorSetupView(APIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorSetupSerializer

    @extend_schema(tags=['Authentication'], summary='Get 2FA setup information')
    def get(self, request):
        user = request.user
        if user.two_factor_enabled:
            return Response({'success': True, 'data': {'two_factor_enabled': True, 'message': _('2FA is enabled.')}})

        secret = TwoFactorService.generate_totp_secret()
        request.session['pending_totp_secret'] = secret
        provisioning_uri = TwoFactorService.get_totp_uri(user, secret)
        qr_code_svg = TwoFactorService.generate_qr_code(provisioning_uri)

        return Response({
            'success': True,
            'data': {'two_factor_enabled': False, 'qr_code_svg': qr_code_svg, 'secret': secret, 'provisioning_uri': provisioning_uri}
        })

    @extend_schema(tags=['Authentication'], summary='Enable two-factor authentication')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not serializer.validated_data.get('enable'):
            return Response({'success': False, 'error': {'code': 'invalid_request', 'message': _('Set enable=true to activate 2FA.')}}, status=status.HTTP_400_BAD_REQUEST)

        secret = request.session.get('pending_totp_secret') or TwoFactorService.generate_totp_secret()
        try:
            TwoFactorService.enable_two_factor(request.user, secret, serializer.validated_data['totp_code'])
        except ValueError as e:
            raise VerificationError(str(e))

        request.session.pop('pending_totp_secret', None)
        return Response({'success': True, 'data': {'two_factor_enabled': True, 'message': _('2FA enabled successfully.')}})

    @extend_schema(tags=['Authentication'], summary='Disable two-factor authentication')
    def delete(self, request):
        totp_code = request.data.get('totp_code')
        if not totp_code:
            return Response({'success': False, 'error': {'code': 'validation_error', 'message': _('TOTP code required.')}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            TwoFactorService.disable_two_factor(request.user, totp_code)
        except ValueError as e:
            raise VerificationError(str(e))

        return Response({'success': True, 'data': {'two_factor_enabled': False, 'message': _('2FA disabled successfully.')}})


class EmailVerificationView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(tags=['Authentication'], summary='Verify email address')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.email_verified = True
        user.email_verification_code = ''
        user.email_verification_expiry = None
        user.save(update_fields=['email_verified', 'email_verification_code', 'email_verification_expiry'])
        return Response({'success': True, 'data': {'email': user.email, 'email_verified': True, 'message': _('Email verified.')}})


class PhoneVerificationView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = PhoneVerificationSerializer

    @extend_schema(tags=['Authentication'], summary='Verify phone number')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.phone_verified = True
        user.phone_verification_code = ''
        user.phone_verification_expiry = None
        user.save(update_fields=['phone_verified', 'phone_verification_code', 'phone_verification_expiry'])
        return Response({'success': True, 'data': {'phone_number': user.phone_number, 'phone_verified': True, 'message': _('Phone verified.')}})


class ResendVerificationView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = ResendVerificationSerializer

    @extend_schema(tags=['Authentication'], summary='Resend verification code')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        method = serializer.validated_data['method']

        if method == 'email':
            AuthenticationService.send_verification_email(user)
        else:
            AuthenticationService.send_verification_sms(user)

        return Response({'success': True, 'data': {'message': _('Verification code sent.')}})


class GoogleAuthView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleAuthSerializer

    @extend_schema(tags=['Authentication'], summary='Google OAuth2 login')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        google_data = serializer.validated_data['id_token']

        try:
            user, created = GoogleAuthService.get_or_create_user(google_data)
        except ValueError as e:
            raise AuthenticationFailedError(str(e))

        token_data = AuthenticationService.get_token_response(user)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return Response({'success': True, 'data': token_data, 'message': _('Google authentication successful')})


class TokenRefreshViewCustom(TokenRefreshView):

    @extend_schema(tags=['Authentication'], summary='Refresh JWT access token')
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data = {'success': True, 'data': response.data, 'message': _('Token refreshed')}
        return response


class LogoutView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Authentication'], summary='User logout')
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({'success': True, 'data': {}, 'message': _('Logged out')})


class PasswordChangeView(APIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    @extend_schema(tags=['Authentication'], summary='Change password')
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        logger.info(f"Password changed for user {user.email}")
        return Response({'success': True, 'data': {'message': _('Password changed.')}})


class PasswordResetRequestView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(tags=['Authentication'], summary='Request password reset')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email__iexact=email)
        AuthenticationService.send_password_reset_email(user)
        return Response({'success': True, 'data': {'message': _('If an account exists, a reset link has been sent.')}})


class UserProfileView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Users'], summary='Get user profile')
    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response({'success': True, 'data': serializer.data})

    @extend_schema(tags=['Users'], summary='Update user profile')
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': UserProfileSerializer(request.user, context={'request': request}).data, 'message': _('Profile updated')})


class UserProfileDetailView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Users'], summary='Get detailed profile')
    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileDetailSerializer(profile)
        data = serializer.data
        data['user'] = UserProfileSerializer(request.user, context={'request': request}).data
        return Response({'success': True, 'data': data})

    @extend_schema(tags=['Users'], summary='Update detailed profile')
    def patch(self, request):
        profile = request.user.profile
        serializer = UserProfileDetailSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': serializer.data, 'message': _('Profile updated')})


class LoginHistoryView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Users'], summary='Get login history')
    def get(self, request):
        limit = int(request.query_params.get('limit', 20))
        history = LoginHistory.objects.filter(user=request.user)[:limit]
        serializer = LoginHistorySerializer(history, many=True)
        return Response({'success': True, 'data': {'login_history': serializer.data, 'total_logins': LoginHistory.objects.filter(user=request.user).count()}})

class DevVerifyUserView(APIView):
    """
    Development-only endpoint to verify a user's email and phone.
    Remove in production.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not settings.DEBUG:
            return Response(
                {'success': False, 'error': {'message': 'Only available in DEBUG mode'}},
                status=403
            )

        email = request.data.get('email')
        if not email:
            return Response(
                {'success': False, 'error': {'message': 'Email required'}},
                status=400
            )

        try:
            user = User.objects.get(email__iexact=email)
            user.email_verified = True
            user.phone_verified = True
            user.email_verification_code = ''
            user.phone_verification_code = ''
            user.save()
            return Response({
                'success': True,
                'data': {'email': user.email, 'verified': True},
                'message': 'User verified for development testing.'
            })
        except User.DoesNotExist:
            return Response(
                {'success': False, 'error': {'message': 'User not found'}},
                status=404
            )