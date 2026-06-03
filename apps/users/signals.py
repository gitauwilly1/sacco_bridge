import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.users.models import User, UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        logger.info(f"UserProfile created for user {instance.email}")


@receiver(pre_save, sender=User)
def track_email_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            if old_instance.email != instance.email:
                logger.info(f"User {instance.pk} email changing from {old_instance.email} to {instance.email}")
                instance.email_verified = False
        except User.DoesNotExist:
            pass