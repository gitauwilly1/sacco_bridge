import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.exceptions import AuthenticationFailedError, VerificationError
from apps.core.pagination import SmallPagination
from apps.core.throttling import SensitiveOperationThrottle
from apps.users.models import LoginHistory
from apps.users.permissions import IsPlatformStaff
from apps.users.serializers import (
    EmailVerificationSerializer,
    GoogleAuthSerializer,
    LoginHistorySerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneNumberUpdateSerializer,
    PhoneVerificationSerializer,
    ResendVerificationSerializer,
    TwoFactorSetupSerializer,
    UserLoginSerializer,
    UserProfileDetailSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserRegistrationSerializer,
)
from apps.users.services import (
    AuthenticationService,
    GoogleAuthService,
    TwoFactorService,
)

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

        if not user.is_active and user.notification_settings.get('account_deactivated'):
            user.is_active = True
            user.notification_settings.pop('account_deactivated', None)
            user.notification_settings.pop('deactivated_at', None)
            user.save()

        token_data = AuthenticationService.get_token_response(user)
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip(request)
        user.last_login_device = request.META.get('HTTP_USER_AGENT', '')
        user.save(update_fields=['last_login', 'last_login_ip', 'last_login_device'])

        response = Response({
            'success': True,
            'data': {
                'access_token': token_data['access_token'],
                'token_type': token_data['token_type'],
                'expires_in': token_data['expires_in'],
                'user': token_data['user'],
            },
            'message': _('Login successful'),
        })

        # Set refresh token as httpOnly cookie
        response.set_cookie(
            key='refresh_token',
            value=token_data['refresh_token'],
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            path='/api/v1/auth',
        )

        return response
    
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
            backup_codes = TwoFactorService.enable_two_factor(request.user, secret, serializer.validated_data['totp_code'])
        except ValueError as e:
            raise VerificationError(str(e))

        request.session.pop('pending_totp_secret', None)
        return Response({
            'success': True,
            'data': {
                'two_factor_enabled': True,
                'backup_codes': backup_codes,
                'message': _('2FA enabled. Save your backup codes. They will not be shown again.'),
            },
            'message': _('2FA enabled successfully'),
        })

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
        user.email_verification_attempts = 0
        user.save(update_fields=['email_verified', 'email_verification_code', 'email_verification_expiry', 'email_verification_attempts'])
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
        user.phone_verification_attempts = 0
        user.save(update_fields=['phone_verified', 'phone_verification_code', 'phone_verification_expiry', 'phone_verification_attempts'])
        return Response({'success': True, 'data': {'phone_number': user.phone_number, 'phone_verified': True, 'message': _('Phone verified.')}})


class ResendVerificationView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = ResendVerificationSerializer
    throttle_classes = [SensitiveOperationThrottle]

    @extend_schema(tags=['Authentication'], summary='Resend verification code')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        method = serializer.validated_data['method']

        try:
            if method == 'email':
                AuthenticationService.send_verification_email(user)
            else:
                AuthenticationService.send_verification_sms(user)
        except ValueError as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'rate_limited',
                    'message': str(e)
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        return Response({
            'success': True,
            'data': {'message': _('Verification code sent.')}
        })

class GoogleAuthView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleAuthSerializer

    @extend_schema(tags=['Authentication'], summary='Google OAuth2 login')
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data['id_token']

        try:
            # Verify the Google ID token and extract user info
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            try:
                idinfo = google_id_token.verify_oauth2_token(
                    id_token,
                    google_requests.Request(),
                    clock_skew_in_seconds=60
                )

                # Validate issuer
                if idinfo['iss'] not in [
                    'accounts.google.com',
                    'https://accounts.google.com'
                ]:
                    raise AuthenticationFailedError(
                        _('Invalid token issuer.')
                    )

            except ValueError as e:
                raise AuthenticationFailedError(
                    _('Invalid Google token: %(error)s') % {'error': str(e)}
                )

            # Pass the verified user info dict to get_or_create_user
            user, created = GoogleAuthService.get_or_create_user(idinfo)

        except AuthenticationFailedError:
            raise
        except ValueError as e:
            raise AuthenticationFailedError(str(e))
        except Exception as e:
            logger.error(f"Google auth error: {str(e)}")
            raise AuthenticationFailedError(
                _(f'Google authentication failed: {str(e)}')
            )
        
        
        token_data = AuthenticationService.get_token_response(user)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return Response({
            'success': True,
            'data': token_data,
            'message': _('Google authentication successful'),
        })

class TokenRefreshViewCustom(TokenRefreshView):

    @extend_schema(tags=['Authentication'], summary='Refresh JWT access token')
    def post(self, request, *args, **kwargs):
        # Check for refresh token in body first, then cookie
        if 'refresh' not in request.data:
            cookie_token = request.COOKIES.get('refresh_token')
            if cookie_token:
                request.data['refresh'] = cookie_token

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data = {
                'success': True,
                'data': response.data,
                'message': _('Token refreshed'),
            }
        return response

class LogoutView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Authentication'], summary='User logout')
    def post(self, request):
        # Blacklist refresh token from request body or cookie
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            refresh_token = request.COOKIES.get('refresh_token')

        try:
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        response = Response({
            'success': True,
            'data': {},
            'message': _('Logged out'),
        })

        # Clear the cookie
        response.delete_cookie('refresh_token', path='/api/v1/auth')

        return response
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
        user.password_reset_token_used = False
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
    

class TwoFactorRecoveryRequestView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Request 2FA recovery email',
        description='Send a recovery link to the user email to disable 2FA.'
    )
    def post(self, request):
        email = request.data.get('email', '').lower().strip()
        if not email:
            return Response({
                'success': False,
                'error': {'code': 'missing_email', 'message': _('Email is required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email, two_factor_enabled=True)
        except User.DoesNotExist:
            return Response({
                'success': True,
                'data': {'message': _('If an account with 2FA exists, a recovery link has been sent.')}
            })

        TwoFactorService.send_2fa_recovery_email(user)

        return Response({
            'success': True,
            'data': {'message': _('If an account with 2FA exists, a recovery link has been sent.')}
        })


class TwoFactorRecoveryConfirmView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Confirm 2FA recovery',
        description='Disable 2FA using the recovery token from email.'
    )
    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        uidb64 = request.data.get('uidb64', '')
        token = request.data.get('token', '')

        if not uidb64 or not token:
            return Response({
                'success': False,
                'error': {'code': 'missing_params', 'message': _('uidb64 and token are required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid, two_factor_enabled=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'success': False,
                'error': {'code': 'invalid_token', 'message': _('Invalid or expired recovery link.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({
                'success': False,
                'error': {'code': 'invalid_token', 'message': _('Invalid or expired recovery token.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        user.totp_secret = ''
        user.two_factor_enabled = False
        user.backup_codes = []
        user.save(update_fields=['totp_secret', 'two_factor_enabled', 'backup_codes'])

        logger.info(f"2FA recovered via email for user {user.email}")

        return Response({
            'success': True,
            'data': {'message': _('2FA has been disabled. You can now login without an authenticator code.')},
            'message': _('2FA recovery successful'),
        })


class TwoFactorDisableWithBackupView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Disable 2FA with backup code',
        description='Disable 2FA using one of the backup codes from setup.'
    )
    def post(self, request):
        email = request.data.get('email', '').lower().strip()
        backup_code = request.data.get('backup_code', '').strip()

        if not email or not backup_code:
            return Response({
                'success': False,
                'error': {'code': 'missing_params', 'message': _('email and backup_code are required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email, two_factor_enabled=True)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('No account found with 2FA enabled.')}
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            TwoFactorService.disable_with_backup_code(user, backup_code)
        except ValueError as e:
            return Response({
                'success': False,
                'error': {'code': 'invalid_code', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'data': {'message': _('2FA has been disabled using backup code.')},
            'message': _('2FA disabled successfully'),
        })

class ProfilePictureUploadView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Upload profile picture',
        description='Upload a profile picture. Max 5MB. Accepted formats: JPG, PNG, WebP.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'profile_picture': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Image file (JPG, PNG, WebP, max 5MB)'
                    }
                }
            }
        }
    )
    def post(self, request):
        if 'profile_picture' not in request.FILES:
            return Response({
                'success': False,
                'error': {
                    'code': 'missing_file',
                    'message': _('No file uploaded. Use key "profile_picture".')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['profile_picture']

        # Validate file size (5MB max)
        if file.size > 5 * 1024 * 1024:
            return Response({
                'success': False,
                'error': {
                    'code': 'file_too_large',
                    'message': _('File size must be under 5MB.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_format',
                    'message': _('Only JPG, PNG, and WebP images are accepted.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete old profile picture if exists
        if request.user.profile_picture:
            request.user.profile_picture.delete(save=False)

        request.user.profile_picture = file
        request.user.save(update_fields=['profile_picture'])

        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data,
            'message': _('Profile picture updated.'),
        })

    @extend_schema(
        tags=['Users'],
        summary='Remove profile picture',
        description='Remove current profile picture.'
    )
    def delete(self, request):
        if request.user.profile_picture:
            request.user.profile_picture.delete(save=False)
            request.user.profile_picture = None
            request.user.save(update_fields=['profile_picture'])

        return Response({
            'success': True,
            'data': {},
            'message': _('Profile picture removed.'),
        })

class PasswordResetConfirmView(APIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        tags=['Authentication'],
        summary='Confirm password reset',
        description='Set a new password using the reset token from email.'
    )
    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        # The token is passed alongside the uid in the format: <uid>/<token>/
        # or the frontend sends them separately
        uidb64 = request.data.get('uidb64', '')

        if not uidb64:
            return Response({
                'success': False,
                'error': {
                    'code': 'missing_uid',
                    'message': _('User ID (uidb64) is required.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_token',
                    'message': _('Invalid or expired reset link.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_token',
                    'message': _('Invalid or expired reset token.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if token was already used
        if user.password_reset_token_used:
            return Response({
                'success': False,
                'error': {
                    'code': 'token_used',
                    'message': _('This reset link has already been used. Please request a new one.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.password_reset_token_used = True
        user.save(update_fields=['password_reset_token_used'])

        logger.info(f"Password reset completed for user {user.email}")

        return Response({
            'success': True,
            'data': {
                'message': _('Password has been reset successfully. You can now login with your new password.')
            },
            'message': _('Password reset successful'),
        })

class PhoneNumberUpdateView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Add phone number',
        description='Add a phone number to your account and receive a verification code.'
    )
    def post(self, request):
        serializer = PhoneNumberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']

        # Check if user already has a verified phone
        if request.user.phone_verified:
            return Response({
                'success': False,
                'error': {
                    'code': 'already_verified',
                    'message': _('Phone number is already verified.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update phone number
        request.user.phone_number = phone_number
        request.user.phone_verified = False

        # Generate and send verification code
        from apps.core.utils import generate_otp
        otp = generate_otp()
        request.user.phone_verification_code = otp
        request.user.phone_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        request.user.save()

        # Send SMS
        AuthenticationService.send_verification_sms(request.user)

        return Response({
            'success': True,
            'data': {
                'phone_number': phone_number,
                'message': _('Phone number added. Verification code sent via SMS.'),
            },
            'message': _('Verification code sent.'),
        })

class ActiveSessionsView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='List active sessions',
        description='View all active login sessions with device info.'
    )
    def get(self, request):
        pass

        # Get recent successful logins (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        sessions = LoginHistory.objects.filter(
            user=request.user,
            login_successful=True,
            login_timestamp__gte=thirty_days_ago,
        ).order_by('-login_timestamp')[:20]

        current_ip = self._get_client_ip(request)
        current_ua = request.META.get('HTTP_USER_AGENT', '')

        data = []
        for session in sessions:
            is_current = (
                session.ip_address == current_ip and
                session.user_agent == current_ua
            )
            data.append({
                'session_id': str(session.uuid),
                'ip_address': self._mask_ip(session.ip_address),
                'device_type': session.device_type,
                'location_city': session.location_city or 'Unknown',
                'login_timestamp': session.login_timestamp.isoformat(),
                'is_current': is_current,
                'user_agent': session.user_agent[:100] if session.user_agent else '',
            })

        return Response({
            'success': True,
            'data': {
                'sessions': data,
                'active_count': len(data),
            },
        })

    @extend_schema(
        tags=['Users'],
        summary='Terminate session',
        description='Log out from a specific device/session.'
    )
    def delete(self, request, session_id):
        try:
            session = LoginHistory.objects.get(
                uuid=session_id,
                user=request.user,
                login_successful=True,
            )
        except LoginHistory.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Session not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        # Don't allow terminating current session
        current_ip = self._get_client_ip(request)
        if session.ip_address == current_ip:
            return Response({
                'success': False,
                'error': {
                    'code': 'current_session',
                    'message': _('Cannot terminate current session. Use logout instead.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        session.login_successful = False
        session.failure_reason = 'Terminated by user'
        session.save(update_fields=['login_successful', 'failure_reason'])

        return Response({
            'success': True,
            'data': {},
            'message': _('Session terminated.'),
        })

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _mask_ip(self, ip):
        """Mask last octet of IP for privacy."""
        if not ip:
            return 'Unknown'
        parts = ip.split('.')
        if len(parts) == 4:
            parts[-1] = '***'
            return '.'.join(parts)
        return ip


class AccountDeletionView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Request account deletion',
        description='Initiate account deletion with 30-day grace period.'
    )
    def post(self, request):
        password = request.data.get('password', '')
        confirmation = request.data.get('confirmation', '')

        if not request.user.check_password(password):
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_password',
                    'message': _('Password is incorrect.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if confirmation != 'DELETE':
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_confirmation',
                    'message': _('Type DELETE to confirm account deletion.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Set deletion schedule
        deletion_date = timezone.now() + timezone.timedelta(days=30)
        request.user.is_active = False
        request.user.notification_settings['account_deletion_scheduled'] = deletion_date.isoformat()
        request.user.save()

        # Send confirmation email
        try:
            from django.core.mail import send_mail
            send_mail(
                subject='Account Deletion Request - Sacco Bridge',
                message=f'Your account deletion has been scheduled for {deletion_date.strftime("%d %B %Y")}. '
                        f'Log in within 30 days to cancel this request.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        logger.info(f"Account deletion scheduled for user {request.user.email}")

        return Response({
            'success': True,
            'data': {
                'deletion_scheduled': deletion_date.isoformat(),
                'message': _('Account deletion scheduled. Log in within 30 days to cancel.'),
            },
            'message': _('Deletion request received.'),
        })

    @extend_schema(
        tags=['Users'],
        summary='Cancel account deletion',
        description='Cancel a pending account deletion request.'
    )
    def delete(self, request):
        if 'account_deletion_scheduled' not in (request.user.notification_settings or {}):
            return Response({
                'success': False,
                'error': {
                    'code': 'no_deletion_pending',
                    'message': _('No deletion request pending.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        request.user.is_active = True
        request.user.notification_settings.pop('account_deletion_scheduled', None)
        request.user.save()

        logger.info(f"Account deletion cancelled for user {request.user.email}")

        return Response({
            'success': True,
            'data': {'message': _('Deletion cancelled. Account reactivated.')},
            'message': _('Deletion cancelled.'),
        })


class AccountDeactivationView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Deactivate account',
        description='Temporarily deactivate your account. Log back in to reactivate.'
    )
    def post(self, request):
        password = request.data.get('password', '')

        if not request.user.check_password(password):
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_password',
                    'message': _('Password is incorrect.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        request.user.is_active = False
        request.user.notification_settings['account_deactivated'] = True
        request.user.notification_settings['deactivated_at'] = timezone.now().isoformat()
        request.user.save()

        # Blacklist all refresh tokens to force logout
        from rest_framework_simplejwt.tokens import OutstandingToken
        OutstandingToken.objects.filter(user=request.user).delete()

        logger.info(f"Account deactivated for user {request.user.email}")

        return Response({
            'success': True,
            'data': {
                'message': _('Account deactivated. You can reactivate by logging in again.'),
            },
            'message': _('Account deactivated.'),
        })

class DataExportView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Export user data',
        description='Download all personal data in JSON format (GDPR portability).'
    )
    def get(self, request):
        user = request.user

        # Gather all user data
        export_data = {
            'exported_at': timezone.now().isoformat(),
            'personal_info': {
                'id': str(user.id),
                'email': user.email,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_of_birth': str(user.date_of_birth) if user.date_of_birth else None,
                'date_joined': user.date_joined.isoformat(),
                'preferred_language': user.preferred_language,
            },
            'profile': {},
            'chamas': [],
            'investments': [],
            'settlements': [],
            'contributions': [],
            'loans': [],
            'login_history': [],
        }

        # Profile
        try:
            profile = user.profile
            export_data['profile'] = {
                'occupation': profile.occupation,
                'employer': profile.employer,
                'county': profile.county,
                'risk_tolerance': profile.risk_tolerance,
                'investment_experience': profile.investment_experience,
            }
        except Exception:
            pass

        # Chama memberships
        from apps.chamas.models import ChamaMember
        memberships = ChamaMember.objects.filter(user=user).select_related('chama')
        for m in memberships:
            export_data['chamas'].append({
                'chama_name': m.chama.name,
                'role': m.get_role_display(),
                'joined_at': m.joined_at.isoformat() if m.joined_at else None,
                'total_contributions': str(m.total_contributions),
                'current_balance': str(m.current_balance),
            })

        # Contributions
        from apps.chamas.models import Contribution
        contributions = Contribution.objects.filter(
            member__user=user
        ).select_related('chama').order_by('-created_at')[:50]
        for c in contributions:
            export_data['contributions'].append({
                'chama': c.chama.name,
                'amount': str(c.amount),
                'status': c.get_status_display(),
                'period_start': str(c.period_start),
                'period_end': str(c.period_end),
                'paid_at': c.paid_at.isoformat() if c.paid_at else None,
            })

        # Loans
        from apps.chamas.models import Loan
        loans = Loan.objects.filter(
            borrower__user=user
        ).select_related('chama').order_by('-created_at')
        for loan in loans:
            export_data['loans'].append({
                'chama': loan.chama.name,
                'principal': str(loan.principal),
                'status': loan.get_status_display(),
                'outstanding_balance': str(loan.outstanding_balance),
            })

        # Investments
        from apps.investments.models import SACCOMemberHolding
        holdings = SACCOMemberHolding.objects.filter(
            user=user
        ).select_related('sacco')
        for h in holdings:
            export_data['investments'].append({
                'sacco': h.sacco.name,
                'total_shares': str(h.total_shares),
                'verification_status': h.verification_status,
            })

        # Settlements
        from django.db import models

        from apps.transactions.models import SettlementIntent
        settlements = SettlementIntent.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).order_by('-created_at')[:50]
        for s in settlements:
            export_data['settlements'].append({
                'type': 'buyer' if s.buyer == user else 'seller',
                'amount': str(s.amount),
                'shares': str(s.share_quantity),
                'sacco': s.seller_sacco_name,
                'state': s.get_state_display(),
                'created_at': s.created_at.isoformat(),
            })

        # Login history
        history = LoginHistory.objects.filter(user=user).order_by('-login_timestamp')[:20]
        for h in history:
            export_data['login_history'].append({
                'timestamp': h.login_timestamp.isoformat(),
                'ip_address': h.ip_address,
                'device_type': h.device_type,
                'location': h.location_city,
            })

        return Response({
            'success': True,
            'data': export_data,
            'message': _('Data export complete.'),
        })

class AdminUserManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] List all users')
    def get(self, request):
        from apps.core.pagination import SmallPagination
        users = User.objects.filter(is_active=True).order_by('-date_joined')
        paginator = SmallPagination()
        page = paginator.paginate_queryset(users, request)

        data = []
        for user in page:
            data.append({
                'id': str(user.id),
                'email': user.email,
                'phone_number': user.phone_number,
                'full_name': user.get_full_name(),
                'email_verified': user.email_verified,
                'phone_verified': user.phone_verified,
                'id_verification_status': user.id_verification_status,
                'trust_score': str(user.trust_score),
                'is_active': user.is_active,
                'roles': list(user.user_roles.filter(is_active=True).values_list('role', flat=True)),
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            })

        return paginator.get_paginated_response(data)

    @extend_schema(tags=['Admin'], summary='[Admin] Verify user identity')
    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')

        if not user_id or not action:
            return Response({
                'success': False,
                'error': {'code': 'validation_error', 'message': _('user_id and action are required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('User not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        if action == 'verify_identity':
            user.id_verification_status = 'VERIFIED'
            user.save(update_fields=['id_verification_status'])
            message = _('User identity verified.')

        elif action == 'reject_identity':
            user.id_verification_status = 'REJECTED'
            user.save(update_fields=['id_verification_status'])
            message = _('User identity rejected.')

        elif action == 'suspend':
            user.is_active = False
            user.save(update_fields=['is_active'])
            message = _('User suspended.')

        elif action == 'activate':
            user.is_active = True
            user.save(update_fields=['is_active'])
            message = _('User activated.')

        elif action == 'add_role':
            role = request.data.get('role')
            if role:
                from apps.users.models import Role
                if role in dict(Role.choices):
                    user.add_role(role, assigned_by=request.user)
                    message = _(f'Role {role} added.')
                else:
                    return Response({
                        'success': False,
                        'error': {'code': 'invalid_role', 'message': _('Invalid role.')}
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'error': {'code': 'missing_role', 'message': _('Role is required.')}
                }, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'remove_role':
            role = request.data.get('role')
            if role:
                user.remove_role(role)
                message = _(f'Role {role} removed.')
            else:
                return Response({
                    'success': False,
                    'error': {'code': 'missing_role', 'message': _('Role is required.')}
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': False,
                'error': {'code': 'invalid_action', 'message': _('Invalid action.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Admin action '{action}' performed on user {user.email} by {request.user.email}")

        return Response({
            'success': True,
            'data': {
                'user_id': str(user.id),
                'action': action,
                'message': message,
            },
            'message': message,
        })

class AuditLogView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        tags=['Admin'],
        summary='View audit logs',
        description='Get audit trail for a specific object.',
        parameters=[
            OpenApiParameter(name='model', description='Model name', required=True, type=str),
            OpenApiParameter(name='object_id', description='Object UUID', required=True, type=str),
        ]
    )
    def get(self, request):
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType

        model_name = request.query_params.get('model')
        object_id = request.query_params.get('object_id')

        if not model_name or not object_id:
            return Response({
                'success': False,
                'error': {'code': 'missing_params', 'message': 'model and object_id are required.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the content type
            from django.db import models
            content_type = ContentType.objects.get(
                models.Q(app_label='chamas', model=model_name.lower()) |
                models.Q(app_label='investments', model=model_name.lower()) |
                models.Q(app_label='transactions', model=model_name.lower()) |
                models.Q(app_label='users', model=model_name.lower())
            )
        except ContentType.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'invalid_model', 'message': f'Model {model_name} not found.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        logs = LogEntry.objects.filter(
            content_type=content_type,
            object_pk=object_id,
        ).select_related('actor').order_by('-timestamp')[:50]

        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'action': log.get_action_display(),
                'actor': log.actor.get_full_name() if log.actor else 'System',
                'changes': log.changes,
                'timestamp': log.timestamp.isoformat(),
                'remote_addr': log.remote_addr,
            })

        return Response({
            'success': True,
            'data': {
                'model': model_name,
                'object_id': object_id,
                'entries': data,
                'total': logs.count(),
            },
        })


class TransactionLimitsView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Get transaction limits',
        description='View current transaction limits and remaining amounts.'
    )
    def get(self, request):
        from apps.core.limits import TransactionLimitService

        limits = TransactionLimitService.get_remaining_limits(request.user)

        return Response({
            'success': True,
            'data': limits,
        })

class AvailabilityCheckView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Check email/phone availability',
        description='Check if an email or phone number is already registered.'
    )
    def get(self, request):
        email = request.query_params.get('email', '').strip().lower()
        phone = request.query_params.get('phone', '').strip()

        if not email and not phone:
            return Response({
                'success': False,
                'error': {'code': 'missing_param', 'message': _('Provide email or phone parameter.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        result = {}

        if email:
            result['email'] = email
            result['email_available'] = not User.objects.filter(email__iexact=email).exists()

        if phone:
            import re
            phone = re.sub(r'\s+', '', phone)
            result['phone'] = phone
            result['phone_available'] = not User.objects.filter(phone_number=phone).exists()

        return Response({
            'success': True,
            'data': result,
        })

class PasswordStrengthView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Check password strength',
        description='Evaluate password strength and return feedback.'
    )
    def post(self, request):
        password = request.data.get('password', '')

        if not password:
            return Response({
                'success': False,
                'error': {'code': 'missing_password', 'message': _('Password is required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        strength = 0
        feedback = []

        # Length check
        if len(password) >= 12:
            strength += 25
        elif len(password) >= 8:
            strength += 15
            feedback.append(_('Use at least 12 characters for a stronger password.'))
        else:
            feedback.append(_('Password is too short. Use at least 8 characters.'))

        # Uppercase
        if any(c.isupper() for c in password):
            strength += 20
        else:
            feedback.append(_('Add uppercase letters.'))

        # Lowercase
        if any(c.islower() for c in password):
            strength += 20
        else:
            feedback.append(_('Add lowercase letters.'))

        # Numbers
        if any(c.isdigit() for c in password):
            strength += 20
        else:
            feedback.append(_('Add numbers.'))

        # Special characters
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`'
        if any(c in special_chars for c in password):
            strength += 15
        else:
            feedback.append(_('Add special characters for extra security.'))

        strength = min(100, strength)

        if strength >= 80:
            level = 'strong'
        elif strength >= 50:
            level = 'medium'
        else:
            level = 'weak'

        return Response({
            'success': True,
            'data': {
                'strength': strength,
                'level': level,
                'feedback': feedback if feedback else [_('Password is strong.')],
            },
        })

class DeletionRequestView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Admin'],
        summary='Request record deletion',
        description='Submit a deletion request for admin approval.'
    )
    def post(self, request):
        from django.contrib.contenttypes.models import ContentType

        from apps.core.models import DeletionRequest

        app_label = request.data.get('app_label')
        model_name = request.data.get('model_name')
        object_id = request.data.get('object_id')
        reason = request.data.get('reason', '')

        if not all([app_label, model_name, object_id]):
            return Response({
                'success': False,
                'error': {'code': 'missing_params', 'message': _('app_label, model_name, and object_id are required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'invalid_model', 'message': _('Model not found.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing pending request
        existing = DeletionRequest.objects.filter(
            requested_by=request.user,
            content_type=content_type,
            object_id=object_id,
            status='PENDING',
        ).exists()

        if existing:
            return Response({
                'success': False,
                'error': {'code': 'duplicate', 'message': _('A pending deletion request already exists.')}
            }, status=status.HTTP_409_CONFLICT)

        try:
            obj = content_type.get_object_for_this_type(id=object_id)
            object_repr = str(obj)[:255]
        except Exception:
            object_repr = f"{model_name}:{object_id}"

        deletion_request = DeletionRequest.objects.create(
            requested_by=request.user,
            content_type=content_type,
            object_id=object_id,
            object_repr=object_repr,
            reason=reason,
        )

        return Response({
            'success': True,
            'data': {
                'request_id': str(deletion_request.id),
                'status': deletion_request.status,
                'message': _('Deletion request submitted for admin review.'),
            },
            'message': _('Request submitted.'),
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['Admin'],
        summary='My deletion requests',
        description='View my deletion requests and their status.'
    )
    def get(self, request):
        from apps.core.models import DeletionRequest

        requests = DeletionRequest.objects.filter(
            requested_by=request.user
        ).order_by('-requested_at')[:20]

        data = []
        for req in requests:
            data.append({
                'id': str(req.id),
                'object_repr': req.object_repr,
                'reason': req.reason,
                'status': req.status,
                'review_notes': req.review_notes,
                'requested_at': req.requested_at.isoformat(),
                'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
            })

        return Response({
            'success': True,
            'data': data,
        })

class AdminDeletionReviewView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        tags=['Admin'],
        summary='List deletion requests',
        description='View all pending deletion requests.'
    )
    def get(self, request):
        from apps.core.models import DeletionRequest

        status_filter = request.query_params.get('status', 'PENDING')
        requests = DeletionRequest.objects.filter(
            status=status_filter
        ).select_related('requested_by').order_by('-requested_at')

        paginator = SmallPagination()
        page = paginator.paginate_queryset(requests, request)

        data = []
        for req in page:
            data.append({
                'id': str(req.id),
                'requested_by': req.requested_by.get_full_name(),
                'requested_by_email': req.requested_by.email,
                'object_repr': req.object_repr,
                'reason': req.reason,
                'status': req.status,
                'requested_at': req.requested_at.isoformat(),
            })

        return paginator.get_paginated_response(data)

    @extend_schema(
        tags=['Admin'],
        summary='Review deletion request',
        description='Approve or reject a deletion request.'
    )
    def post(self, request, pk=None):
        from apps.core.models import DeletionRequest

        try:
            deletion_request = DeletionRequest.objects.get(id=pk, status='PENDING')
        except DeletionRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Request not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action == 'approve':
            success = deletion_request.approve(request.user, notes)
            if success:
                # Notify user
                try:
                    from apps.notifications.models import (
                        NotificationCategory,
                        NotificationPriority,
                    )
                    from apps.notifications.services import NotificationService

                    NotificationService.create_notification(
                        user=deletion_request.requested_by,
                        category=NotificationCategory.SYSTEM,
                        title=_('Deletion Approved'),
                        body=_('Your request to delete "%(object)s" has been approved.') % {
                            'object': deletion_request.object_repr
                        },
                        priority=NotificationPriority.MEDIUM,
                    )
                except Exception:
                    pass

                return Response({
                    'success': True,
                    'data': {'status': 'APPROVED'},
                    'message': _('Deletion approved and executed.'),
                })
            else:
                return Response({
                    'success': False,
                    'error': {'code': 'delete_failed', 'message': _('Object could not be deleted.')}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif action == 'reject':
            deletion_request.reject(request.user, notes)

            try:
                from apps.notifications.models import (
                    NotificationCategory,
                    NotificationPriority,
                )
                from apps.notifications.services import NotificationService

                NotificationService.create_notification(
                    user=deletion_request.requested_by,
                    category=NotificationCategory.SYSTEM,
                    title=_('Deletion Rejected'),
                    body=_('Your request to delete "%(object)s" was rejected. Reason: %(reason)s') % {
                        'object': deletion_request.object_repr,
                        'reason': notes or _('No reason provided.'),
                    },
                    priority=NotificationPriority.MEDIUM,
                )
            except Exception:
                pass

            return Response({
                'success': True,
                'data': {'status': 'REJECTED'},
                'message': _('Deletion rejected.'),
            })

        return Response({
            'success': False,
            'error': {'code': 'invalid_action', 'message': _('Action must be approve or reject.')}
        }, status=status.HTTP_400_BAD_REQUEST)

class UnifiedAuditView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        tags=['Admin'],
        summary='Unified audit trail',
        description='Complete system audit combining all event sources.',
        parameters=[
            OpenApiParameter(name='user_id', description='Filter by user', type=str),
            OpenApiParameter(name='model', description='Filter by model name', type=str),
            OpenApiParameter(name='action', description='Filter by action type', type=str),
            OpenApiParameter(name='days', description='Last N days (default 7)', type=int),
            OpenApiParameter(name='export', description='Export as CSV', type=bool),
        ]
    )
    def get(self, request):
        from apps.activity.models import ActivityLog

        user_id = request.query_params.get('user_id')
        days = int(request.query_params.get('days', 7))
        export = request.query_params.get('export', '').lower() == 'true'

        cutoff = timezone.now() - timezone.timedelta(days=days)

        # Use database-level pagination on the primary source (ActivityLog)
        activities = ActivityLog.objects.filter(
            created_at__gte=cutoff
        ).select_related('user', 'chama', 'sacco')

        if user_id:
            activities = activities.filter(user_id=user_id)

        activities = activities.order_by('-created_at')

        # Export mode: load more records for CSV download
        if export:
            activities = activities[:500]
            events = []
            for a in activities:
                events.append({
                    'timestamp': a.created_at.isoformat(),
                    'source': 'ACTIVITY',
                    'user': a.user.get_full_name(),
                    'user_email': a.user.email,
                    'action': a.get_activity_type_display(),
                    'description': a.title,
                    'details': a.description,
                    'reference': str(a.reference_id) if a.reference_id else None,
                })

            import csv
            from django.http import HttpResponse

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="audit_trail.csv"'
            writer = csv.writer(response)
            writer.writerow(['Timestamp', 'Source', 'User', 'Email', 'Action', 'Description', 'Details', 'Reference'])
            for e in events:
                writer.writerow([
                    e['timestamp'], e['source'], e['user'], e['user_email'],
                    e['action'], e['description'], e['details'], e['reference'],
                ])
            return response

        # Normal paginated view
        paginator = SmallPagination()
        page = paginator.paginate_queryset(activities, request)

        events = []
        for a in page:
            events.append({
                'timestamp': a.created_at.isoformat(),
                'source': 'ACTIVITY',
                'user': a.user.get_full_name(),
                'user_email': a.user.email,
                'action': a.get_activity_type_display(),
                'description': a.title,
                'details': a.description,
                'reference': str(a.reference_id) if a.reference_id else None,
            })

        return paginator.get_paginated_response(events)

class CurrentUserView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='Get current user',
        description='Returns minimal user info for fast app initialization.'
    )
    def get(self, request):
        user = request.user

        return Response({
            'success': True,
            'data': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.get_full_name(),
                'initials': user.get_initials(),
                'roles': list(user.user_roles.filter(is_active=True).values_list('role', flat=True)),
                'email_verified': user.email_verified,
                'phone_verified': user.phone_verified,
                'two_factor_enabled': user.two_factor_enabled,
                'trust_score': str(user.trust_score),
                'preferred_language': user.preferred_language,
                'profile_picture': user.profile_picture.url if user.profile_picture else None,
            },
        })
class SilentRefreshView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Silent token refresh',
        description='Get a new access token using the refresh token from httpOnly cookie.'
    )
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({
                'success': False,
                'error': {
                    'code': 'no_refresh_token',
                    'message': _('No refresh token found. Please login again.'),
                }
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh.get('user_id')

            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id, is_active=True)

            # Generate new tokens
            new_access = refresh.access_token

            response = Response({
                'success': True,
                'data': {
                    'access_token': str(new_access),
                    'token_type': 'Bearer',
                    'expires_in': int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'full_name': user.get_full_name(),
                        'roles': list(user.user_roles.filter(is_active=True).values_list('role', flat=True)),
                    },
                },
                'message': _('Token refreshed'),
            })

            # Rotate refresh token if configured
            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
                refresh.set_jti()
                refresh.set_exp()
                new_refresh = RefreshToken.for_user(user)

                response.set_cookie(
                    key='refresh_token',
                    value=str(new_refresh),
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Strict',
                    max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
                    path='/api/v1/auth',
                )

            return response

        except Exception:
            response = Response({
                'success': False,
                'error': {
                    'code': 'invalid_token',
                    'message': _('Invalid or expired session. Please login again.'),
                }
            }, status=status.HTTP_401_UNAUTHORIZED)

            response.delete_cookie('refresh_token', path='/api/v1/auth')
            return response


class DashboardSummaryView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        summary='Dashboard summary',
        description='Returns all dashboard widgets in a single optimized call.'
    )
    def get(self, request):
        user = request.user
        from django.db import models as django_models

        # Chama summaries
        from apps.chamas.models import ChamaMember
        memberships = ChamaMember.objects.filter(
            user=user, is_active=True
        ).select_related('chama')

        chamas_data = []
        for m in memberships[:5]:
            chamas_data.append({
                'id': str(m.chama.id),
                'name': m.chama.name,
                'role': m.get_role_display(),
                'my_balance': str(m.current_balance),
                'total_savings': str(m.chama.total_savings),
                'member_count': m.chama.memberships.filter(is_active=True).count(),
                'health_score': str(m.chama.health_score) if m.chama.health_score else '0',
                'health_grade': m.chama.health_score_grade or 'N/A',
            })

        # Investment overview
        from apps.investments.models import SACCOMemberHolding
        holdings = SACCOMemberHolding.objects.filter(
            user=user, is_deleted=False
        ).select_related('sacco')

        total_investment_value = sum(
            h.total_shares * h.share_class.nominal_value for h in holdings
        )

        investments_data = {
            'total_value': str(total_investment_value),
            'sacco_count': holdings.values('sacco').distinct().count(),
            'holdings': [
                {
                    'id': str(h.id),
                    'sacco_name': h.sacco.name,
                    'shares': str(h.total_shares),
                    'available': str(h.available_shares),
                }
                for h in holdings[:5]
            ],
        }

        # Pending actions
        from apps.transactions.models import SettlementIntent, SettlementState
        pending_settlements = SettlementIntent.objects.filter(
            django_models.Q(buyer=user) | django_models.Q(seller=user),
            state__in=[
                'MATCH_PROPOSED', 'INTENT_LOCKED', 'BUYER_DEBIT_INITIATED',
                'BUYER_DEBIT_CONFIRMED', 'SELLER_CREDIT_INITIATED',
                'SELLER_CREDIT_CONFIRMED',
            ],
            is_deleted=False,
        ).count()

        from apps.chamas.models import Loan, LoanStatus
        pending_loans = Loan.objects.filter(
            borrower__user=user,
            status=LoanStatus.PENDING,
            is_deleted=False,
        ).count()

        from apps.investments.models import LiquidityRequest, LiquidityRequestStatus
        active_requests = LiquidityRequest.objects.filter(
            seller=user,
            status=LiquidityRequestStatus.ACTIVE,
            is_deleted=False,
        ).count()

        from apps.transactions.models import Dispute, DisputeStatus
        open_disputes = Dispute.objects.filter(
            raised_by=user,
            status=DisputeStatus.OPEN,
            is_deleted=False,
        ).count()

        pending_actions = {
            'pending_settlements': pending_settlements,
            'pending_loan_approvals': pending_loans,
            'active_liquidity_requests': active_requests,
            'open_disputes': open_disputes,
            'total_pending': pending_settlements + pending_loans + active_requests + open_disputes,
        }

        # Notification count
        from apps.notifications.services import NotificationService
        unread_notifications = NotificationService.get_unread_count(user)

        # Recent activity
        from apps.activity.models import ActivityLog
        recent_activity = ActivityLog.objects.filter(
            user=user
        ).select_related('chama', 'sacco').order_by('-created_at')[:5]

        activity_data = []
        for a in recent_activity:
            activity_data.append({
                'id': str(a.id),
                'type': a.activity_type,
                'type_display': a.get_activity_type_display(),
                'title': a.title,
                'chama_name': a.chama.name if a.chama else None,
                'created_at': a.created_at.isoformat(),
                'time_ago': self._time_ago(a.created_at),
            })

        return Response({
            'success': True,
            'data': {
                'user': {
                    'full_name': user.get_full_name(),
                    'trust_score': str(user.trust_score),
                },
                'chamas': chamas_data,
                'investments': investments_data,
                'pending_actions': pending_actions,
                'unread_notifications': unread_notifications,
                'recent_activity': activity_data,
            },
        })

    def _time_ago(self, dt):
        now = timezone.now()
        diff = now - dt

        if diff.days > 7:
            return dt.strftime('%d %b')
        elif diff.days > 0:
            return f'{diff.days}d ago'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600}h ago'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60}m ago'
        return 'Just now'