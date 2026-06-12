import logging
import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class ReCaptchaService:
    VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
    SCORE_THRESHOLD = 0.5  # Scores below this are likely bots

    @classmethod
    def verify(cls, token, action=None):
        # Skip verification in development if not configured
        if settings.DEBUG and not getattr(settings, 'RECAPTCHA_SECRET_KEY', None):
            logger.debug("reCAPTCHA bypassed in development")
            return {'success': True, 'error': None, 'score': 1.0}

        secret_key = getattr(settings, 'RECAPTCHA_SECRET_KEY', None)
        if not secret_key:
            logger.warning("reCAPTCHA secret key not configured")
            return {'success': True, 'error': None, 'score': 0.0}

        try:
            response = requests.post(cls.VERIFY_URL, data={
                'secret': secret_key,
                'response': token,
            }, timeout=5)

            result = response.json()

            if result.get('success'):
                score = result.get('score', 0.0)
                
                # Check action if specified
                if action and result.get('action') != action:
                    logger.warning(
                        f"reCAPTCHA action mismatch: expected {action}, "
                        f"got {result.get('action')}"
                    )

                # Check score threshold
                if score < cls.SCORE_THRESHOLD:
                    logger.warning(f"reCAPTCHA low score: {score}")
                    return {
                        'success': False,
                        'error': _('Suspicious activity detected. Please try again.'),
                        'score': score,
                    }

                return {'success': True, 'error': None, 'score': score}
            else:
                error_codes = result.get('error-codes', [])
                logger.error(f"reCAPTCHA verification failed: {error_codes}")
                return {
                    'success': False,
                    'error': _('reCAPTCHA verification failed. Please try again.'),
                    'score': 0.0,
                }

        except requests.RequestException as e:
            logger.error(f"reCAPTCHA request failed: {str(e)}")
            # Fail open in case of network issues
            return {'success': True, 'error': None, 'score': 0.0}