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
    PasswordResetConfirmSerializer, UserRegistrationSerializer, UserLoginSerializer,
    EmailVerificationSerializer, PhoneVerificationSerializer,
    ResendVerificationSerializer, GoogleAuthSerializer,
    TwoFactorSetupSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, UserProfileDetailSerializer,
    LoginHistorySerializer, PhoneNumberUpdateSerializer,
)
from apps.users.services import AuthenticationService, TwoFactorService, GoogleAuthService
from apps.users.permissions import IsPlatformStaff

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
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

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
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str

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
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str

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

        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.save()

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