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

from apps.core.utils import decrypt_data, encrypt_data, generate_otp
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
        # Rate limit check
        if user.email_last_verification_sent:
            elapsed = (timezone.now() - user.email_last_verification_sent).total_seconds()
            if elapsed < 60:
                wait = int(60 - elapsed)
                raise ValueError(
                    _('Please wait %(seconds)d seconds before requesting another code.') % {'seconds': wait}
                )

        # Attempt limit check
        if user.email_verification_attempts >= 5:
            raise ValueError(
                _('Too many attempts. Please contact support.')
            )

        # Generate and save OTP
        otp = generate_otp()
        user.email_verification_code = otp
        user.email_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.email_verification_attempts += 1
        user.email_last_verification_sent = timezone.now()
        user.save(update_fields=[
            'email_verification_code', 'email_verification_expiry',
            'email_verification_attempts', 'email_last_verification_sent'
        ])

        subject = 'Your Sacco Bridge Verification Code'
        html_message = render_to_string('emails/verify_email.html', {
            'user': user,
            'otp': otp,
            'expiry_hours': 24,
        })

        # Send email
        try:
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            # Fallback: print to console in development
            if settings.DEBUG:
                print(f"\n{'='*60}")
                print(f"EMAIL OTP for {user.email}: {otp}")
                print(f"{'='*60}\n")
            raise
        
    @staticmethod
    def send_verification_sms(user):
        # Rate limit check
        if user.phone_last_verification_sent:
            elapsed = (timezone.now() - user.phone_last_verification_sent).total_seconds()
            if elapsed < 60:
                wait = int(60 - elapsed)
                raise ValueError(
                    _('Please wait %(seconds)d seconds before requesting another code.') % {'seconds': wait}
                )

        # Attempt limit check
        if user.phone_verification_attempts >= 5:
            raise ValueError(
                _('Too many attempts. Please contact support.')
            )

        # Generate OTP
        otp = generate_otp()
        user.phone_verification_code = otp
        user.phone_verification_expiry = timezone.now() + timezone.timedelta(hours=24)
        user.phone_verification_attempts += 1
        user.phone_last_verification_sent = timezone.now()
        user.save(update_fields=[
            'phone_verification_code', 'phone_verification_expiry',
            'phone_verification_attempts', 'phone_last_verification_sent'
        ])

        # Format message
        message = (
            f"Your Sacco Bridge verification code is: {otp}. "
            f"Valid for 24 hours. Do not share this code."
        )

        # Format phone number
        phone = user.phone_number
        if phone and phone.startswith('0'):
            phone = '+254' + phone[1:]
        elif phone and not phone.startswith('+'):
            phone = '+254' + phone

        # Try Africa's Talking
        sms_sent = False
        try:
            import africastalking

            africastalking.initialize(
                settings.AFRICASTALKING_USERNAME,
                settings.AFRICASTALKING_API_KEY
            )
            sms = africastalking.SMS
            
            response = sms.send(message, [phone])
            logger.info(f"SMS response: {response}")

            # Check if SMS was actually sent
            recipients = response.get('SMSMessageData', {}).get('Recipients', [])
            if recipients:
                status = recipients[0].get('status')
                if status == 'Success':
                    sms_sent = True
                    logger.info(f"SMS sent successfully to {phone}")
                else:
                    logger.warning(f"SMS failed with status: {status}")
            else:
                logger.warning("No recipient data in SMS response")

        except Exception as e:
            logger.warning(f"Africa's Talking SMS error: {str(e)}")

        # Fallback for development
        if not sms_sent:
            logger.info("=" * 60)
            logger.info(f"SMS OTP for {user.phone_number}: {otp}")
            logger.info("=" * 60)
            print(f"\n{'='*60}")
            print(f"SMS OTP for {user.phone_number}: {otp}")
            print(f"{'='*60}\n")

        return otp
        
    @staticmethod
    def send_password_reset_email(user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            subject = _('Reset your password - Sacco Bridge')
            html_message = render_to_string('emails/reset_password.html', {
                'user': user,
                'reset_url': reset_url,
                'expiry_hours': 24,
            })

            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            # Don't re-raise - password reset should not expose email delivery failures

    @staticmethod
    def send_verification_sms_for_invite(phone_number, chama_name, inviter_name, invite_code):
        message = (
            f"{inviter_name} has invited you to join {chama_name} on Sacco Bridge. "
            f"Download the app and use invite code: {invite_code}"
        )

        # Format phone number
        phone = phone_number
        if phone.startswith('0'):
            phone = '+254' + phone[1:]
        elif not phone.startswith('+'):
            phone = '+254' + phone

        try:
            import africastalking
            africastalking.initialize(
                settings.AFRICASTALKING_USERNAME,
                settings.AFRICASTALKING_API_KEY
            )
            sms = africastalking.SMS
            response = sms.send(message, [phone])
            logger.info(f"Invite SMS sent to {phone}: {response}")
        except Exception as e:
            logger.warning(f"Failed to send invite SMS: {e}")
            if settings.DEBUG:
                print(f"\n{'='*60}")
                print(f"INVITE SMS to {phone_number}: {message}")
                print(f"{'='*60}\n")

    @staticmethod
    def send_verification_sms_for_signature(user, otp, document_title):
        message = (
            f"Your Sacco Bridge signature code for '{document_title}' is: {otp}. "
            f"Valid for 10 minutes. Do not share this code."
        )

        phone = user.phone_number
        if phone and phone.startswith('0'):
            phone = '+254' + phone[1:]

        if phone:
            try:
                import africastalking
                africastalking.initialize(
                    settings.AFRICASTALKING_USERNAME,
                    settings.AFRICASTALKING_API_KEY
                )
                sms = africastalking.SMS
                sms.send(message, [phone])
            except Exception:
                if settings.DEBUG:
                    print(f"\nSIGNATURE OTP for {user.phone_number}: {otp}\n")

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
    def generate_backup_codes():
        import hashlib
        import secrets
        
        codes = []
        plain_codes = []
        
        for _ in range(8):
            code = secrets.token_hex(4).upper()[:8]
            plain_codes.append(code)
            hashed = hashlib.sha256(code.encode()).hexdigest()
            codes.append(hashed)
        
        return codes, plain_codes

    @staticmethod
    def verify_backup_code(user, code):
        import hashlib
        hashed = hashlib.sha256(code.encode()).hexdigest()
        
        if hashed in user.backup_codes:
            user.backup_codes.remove(hashed)
            user.save(update_fields=['backup_codes'])
            return True
        return False

    @staticmethod
    def enable_two_factor(user, secret, verification_code):
        if not TwoFactorService.verify_totp(secret, verification_code):
            raise ValueError(_('Invalid verification code.'))
        
        user.totp_secret = encrypt_data(secret)
        user.two_factor_enabled = True
        
        # Generate backup codes
        hashed_codes, plain_codes = TwoFactorService.generate_backup_codes()
        user.backup_codes = hashed_codes
        user.save(update_fields=['totp_secret', 'two_factor_enabled', 'backup_codes'])
        
        logger.info(f"2FA enabled for user {user.email}")
        return plain_codes

    @staticmethod
    def disable_two_factor(user, verification_code):
        secret = decrypt_data(user.totp_secret)
        if not TwoFactorService.verify_totp(secret, verification_code):
            raise ValueError(_('Invalid verification code.'))
        user.totp_secret = ''
        user.two_factor_enabled = False
        user.backup_codes = []
        user.save(update_fields=['totp_secret', 'two_factor_enabled', 'backup_codes'])
        logger.info(f"2FA disabled for user {user.email}")

    @staticmethod
    def disable_with_backup_code(user, backup_code):
        """Disable 2FA using a backup code."""
        if not TwoFactorService.verify_backup_code(user, backup_code):
            raise ValueError(_('Invalid backup code.'))
        user.totp_secret = ''
        user.two_factor_enabled = False
        user.backup_codes = []
        user.save(update_fields=['totp_secret', 'two_factor_enabled', 'backup_codes'])
        logger.info(f"2FA disabled via backup code for user {user.email}")

    @staticmethod
    def admin_reset_2fa(user, admin_user):
        user.totp_secret = ''
        user.two_factor_enabled = False
        user.backup_codes = []
        user.save(update_fields=['totp_secret', 'two_factor_enabled', 'backup_codes'])
        logger.info(f"2FA reset by admin {admin_user.email} for user {user.email}")

    @staticmethod
    def send_2fa_recovery_email(user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            recovery_url = f"{settings.FRONTEND_URL}/recover-2fa/{uid}/{token}/"

            subject = _('2FA Recovery - Sacco Bridge')
            html_message = render_to_string('emails/recover_2fa.html', {
                'user': user,
                'recovery_url': recovery_url,
                'expiry_hours': 1,
            })

            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"2FA recovery email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send 2FA recovery email: {str(e)}")

class GoogleAuthService:

    @staticmethod
    def get_or_create_user(google_data):
        email = google_data.get('email', '').lower().strip()
        if not email:
            raise ValueError(_('Email not provided by Google.'))

        # Try to find existing user by email first
        try:
            user = User.objects.get(email=email)
            created = False
            
            # Update email verified status if needed
            if not user.email_verified and google_data.get('email_verified'):
                user.email_verified = True
                user.save(update_fields=['email_verified'])
            
            logger.info(f"Existing user logged in via Google Auth: {email}")
            
        except User.DoesNotExist:
            # Create new user with NULL phone number
            user = User.objects.create_user(
                email=email,
                first_name=google_data.get('given_name', ''),
                last_name=google_data.get('family_name', ''),
                email_verified=google_data.get('email_verified', False),
                phone_number=None,
            )
            created = True
            logger.info(f"New user created via Google Auth: {email}")

        return user, created