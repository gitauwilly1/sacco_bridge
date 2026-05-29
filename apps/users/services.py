import logging
import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.utils import generate_otp, encrypt_data, decrypt_data
from apps.users.models import User

logger = logging.getLogger(__name__)


class AuthenticationService:

    @staticmethod
    def generate_tokens_for_user(user):
        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['full_name'] = user.get_full_name()
        refresh['roles'] = list(user.user_roles.filter(is_active=True).values_list('role', flat=True))

        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'Bearer',
            'expires_in': int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        }

    @staticmethod
    def get_token_response(user):
        tokens = AuthenticationService.generate_tokens_for_user(user)
        tokens['user'] = {
            'id': str(user.id),
            'email': user.email,
            'phone_number': user.phone_number,
            'full_name': user.get_full_name(),
            'initials': user.get_initials(),
            'roles': list(user.user_roles.filter(is_active=True).values_list('role', flat=True)),
            'email_verified': user.email_verified,
            'phone_verified': user.phone_verified,
            'two_factor_enabled': user.two_factor_enabled,
            'two_factor_required': user.two_factor_enabled,
            'trust_score': str(user.trust_score),
            'profile_picture': user.profile_picture.url if user.profile_picture else None,
        }
        return tokens

    @staticmethod
    def send_verification_email(user):
        otp = generate_otp()
        user.email_verification_code = otp
        user.email_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.save(update_fields=['email_verification_code', 'email_verification_expiry'])

        subject = _('Verify your email address - Sacco Bridge')
        html_message = render_to_string('emails/verify_email.html', {'user': user, 'otp': otp, 'expiry_hours': 24})

        try:
            send_mail(subject=subject, message='', from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[user.email], html_message=html_message, fail_silently=False)
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            raise

    @staticmethod
    def send_verification_sms(user):
        otp = generate_otp()
        user.phone_verification_code = otp
        user.phone_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.save(update_fields=['phone_verification_code', 'phone_verification_expiry'])
        logger.info(f"Verification SMS queued for {user.phone_number}")
        return otp

    @staticmethod
    def send_password_reset_email(user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        subject = _('Reset your password - Sacco Bridge')
        html_message = render_to_string('emails/reset_password.html', {'user': user, 'reset_url': reset_url, 'expiry_hours': 24})

        try:
            send_mail(subject=subject, message='', from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[user.email], html_message=html_message, fail_silently=False)
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            raise


class TwoFactorService:

    @staticmethod
    def generate_totp_secret():
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(user, secret):
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user.email, issuer_name='Sacco Bridge')

    @staticmethod
    def generate_qr_code(provisioning_uri):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage, fill_color='#C67B5C', back_color='white')
        return img.to_string()

    @staticmethod
    def verify_totp(secret, code):
        if not secret:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    @staticmethod
    def enable_two_factor(user, secret, verification_code):
        if not TwoFactorService.verify_totp(secret, verification_code):
            raise ValueError(_('Invalid verification code.'))
        user.totp_secret = encrypt_data(secret)
        user.two_factor_enabled = True
        user.save(update_fields=['totp_secret', 'two_factor_enabled'])
        logger.info(f"2FA enabled for user {user.email}")

    @staticmethod
    def disable_two_factor(user, verification_code):
        secret = decrypt_data(user.totp_secret)
        if not TwoFactorService.verify_totp(secret, verification_code):
            raise ValueError(_('Invalid verification code.'))
        user.totp_secret = ''
        user.two_factor_enabled = False
        user.save(update_fields=['totp_secret', 'two_factor_enabled'])
        logger.info(f"2FA disabled for user {user.email}")


class GoogleAuthService:

    @staticmethod
    def get_or_create_user(google_data):
        email = google_data.get('email', '').lower().strip()
        if not email:
            raise ValueError(_('Email not provided by Google.'))

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': google_data.get('given_name', ''),
                'last_name': google_data.get('family_name', ''),
                'email_verified': google_data.get('email_verified', False),
                'phone_number': '',
            }
        )

        if created:
            from apps.users.models import UserProfile
            UserProfile.objects.create(user=user)
            logger.info(f"New user created via Google Auth: {email}")
        else:
            if not user.email_verified and google_data.get('email_verified'):
                user.email_verified = True
                user.save(update_fields=['email_verified'])

        return user, created