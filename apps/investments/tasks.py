import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.investments.tasks.check_stale_disclosures',
    bind=True,
    max_retries=1,
    default_retry_delay=3600,
)
def check_stale_disclosures(self):
    logger.info("Starting SACCO disclosure staleness check...")

    from apps.investments.models import SACCO

    try:
        saccos = SACCO.objects.filter(
            status='ACTIVE',
            is_deleted=False,
        )

        halted_count = 0
        warned_count = 0

        for sacco in saccos:
            # Check disclosure status
            if sacco.disclosure_due_date:
                days_until_due = (
                    sacco.disclosure_due_date - timezone.now().date()
                ).days

                if days_until_due <= 0:
                    # Past due - halt trading
                    if not sacco.trading_halted:
                        sacco.trading_halted = True
                        sacco.halt_reason = (
                            'Trading halted: Financial disclosures are past due. '
                            'Updated disclosures required to resume trading.'
                        )
                        sacco.save(update_fields=['trading_halted', 'halt_reason'])
                        halted_count += 1
                        logger.warning(
                            f"Trading halted for {sacco.name}: "
                            f"disclosures {abs(days_until_due)} days overdue"
                        )

                elif days_until_due <= 30:
                    # Due within 30 days - log warning
                    warned_count += 1
                    logger.info(
                        f"{sacco.name} disclosures due in {days_until_due} days"
                    )

        logger.info(
            f"Disclosure check complete: "
            f"{halted_count} halted, {warned_count} due soon"
        )

        return {
            'total_checked': saccos.count(),
            'halted': halted_count,
            'due_soon': warned_count,
        }

    except Exception as e:
        logger.error(f"Disclosure check failed: {str(e)}")
        raise self.retry(exc=e)