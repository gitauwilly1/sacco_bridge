import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.scoring.underwriting import UnderwritingService

logger = logging.getLogger(__name__)


@receiver(post_save, sender='chamas.Loan')
def auto_underwrite_loan(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        UnderwritingService.evaluate_loan(instance)
    except Exception as e:
        logger.error(f"Auto-underwriting failed for loan {instance.id}: {e}")