import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction as db_transaction

from apps.transactions.models import (
    SettlementIntent, SettlementState, SettlementEventTrigger
)
from apps.transactions.services import RecoveryService, SettlementService

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.transactions.tasks.recover_stuck_settlements',
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def recover_stuck_settlements(self):
    logger.info("Starting settlement recovery scan...")

    try:
        stuck_settlements = RecoveryService.find_stuck_settlements()

        recovered_count = 0
        escalated_count = 0

        for intent in stuck_settlements:
            try:
                recovered = RecoveryService.attempt_recovery(intent)

                if recovered:
                    recovered_count += 1
                    logger.info(
                        f"Settlement {intent.uuid} recovery attempt "
                        f"{intent.retry_count}/{intent.max_retries}"
                    )
                else:
                    escalated_count += 1
                    logger.warning(
                        f"Settlement {intent.uuid} escalated to manual review "
                        f"after {intent.retry_count} failed attempts"
                    )

            except Exception as e:
                logger.error(
                    f"Error recovering settlement {intent.uuid}: {str(e)}"
                )

        logger.info(
            f"Settlement recovery complete: "
            f"{recovered_count} recovered, {escalated_count} escalated"
        )

        return {
            'recovered': recovered_count,
            'escalated': escalated_count,
            'total': len(stuck_settlements),
        }

    except Exception as e:
        logger.error(f"Settlement recovery scan failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.transactions.tasks.expire_stale_intents',
    bind=True,
)
def expire_stale_intents(self):
    logger.info("Starting stale intent expiration...")

    now = timezone.now()
    expired_count = 0

    # Only expire intents before the point of no return
    safe_states = [
        SettlementState.MATCH_PROPOSED,
        SettlementState.INTENT_LOCKED,
        SettlementState.BUYER_DEBIT_INITIATED,
    ]

    stale_intents = SettlementIntent.objects.filter(
        state__in=safe_states,
        expires_at__lt=now,
        is_deleted=False,
    )

    for intent in stale_intents:
        try:
            with db_transaction.atomic():
                intent.transition_to(
                    SettlementState.REVERSED,
                    SettlementEventTrigger.TTL_EXPIRED,
                    metadata={'expired_at': str(now)}
                )
                expired_count += 1
                logger.info(f"Expired stale intent: {intent.uuid}")

        except Exception as e:
            logger.error(f"Error expiring intent {intent.uuid}: {str(e)}")

    logger.info(f"Expired {expired_count} stale settlement intents")

    return {'expired_count': expired_count}