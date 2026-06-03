import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.core.tasks.cleanup_expired_data',
    bind=True,
)
def cleanup_expired_data(self):
    logger.info("Starting expired data cleanup...")

    from apps.users.models import User, LoginHistory

    try:
        # Clear expired verification codes
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        users_cleared = User.objects.filter(
            email_verification_expiry__lt=seven_days_ago
        ).exclude(
            email_verification_code=''
        ).update(
            email_verification_code='',
            email_verification_expiry=None,
        )

        phone_cleared = User.objects.filter(
            phone_verification_expiry__lt=seven_days_ago
        ).exclude(
            phone_verification_code=''
        ).update(
            phone_verification_code='',
            phone_verification_expiry=None,
        )

        # Clear old login history
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)
        logins_deleted, _ = LoginHistory.objects.filter(
            login_timestamp__lt=ninety_days_ago
        ).delete()

        logger.info(
            f"Cleanup complete: "
            f"{users_cleared} email codes cleared, "
            f"{phone_cleared} phone codes cleared, "
            f"{logins_deleted} login records deleted"
        )

        return {
            'email_codes_cleared': users_cleared,
            'phone_codes_cleared': phone_cleared,
            'login_records_deleted': logins_deleted,
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")