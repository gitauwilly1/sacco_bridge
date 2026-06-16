import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.fraud.services import FraudDetectionService

logger = logging.getLogger(__name__)


@receiver(post_save, sender='transactions.SettlementIntent')
def assess_settlement(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        assessment = FraudDetectionService.assess_transaction(
            user=instance.buyer,
            transaction_type='SETTLEMENT',
            transaction_ref=str(instance.uuid),
            amount=instance.amount,
            ip_address=instance.buyer.last_login_ip,
        )

        # Apply recommended action
        assessment.applied_action = assessment.recommended_action

        if assessment.recommended_action == FraudDetectionService.FraudAction.BLOCK:
            logger.warning(
                f"Settlement {instance.uuid} BLOCKED by fraud detection "
                f"(score={assessment.risk_score})"
            )
        elif assessment.recommended_action == FraudAction.HOLD:
            instance.state = 'DISPUTED_MANUAL'
            instance.save()
            
            # Also hold escrow if it exists
            try:
                from apps.escrow.models import EscrowAccount
                escrow = EscrowAccount.objects.get(settlement=instance)
                escrow.mark_held(
                    reason=f'Fraud detection: score {assessment.risk_score}',
                    trigger='FRAUD_DETECTION',
                )
            except Exception:
                pass  # Escrow may not exist yet
            
            logger.warning(
                f"Settlement {instance.uuid} HELD for review "
                f"(score={assessment.risk_score})"
            )
        assessment.save()

    except Exception as e:
        logger.error(f"Fraud assessment failed for settlement {instance.uuid}: {e}")


@receiver(post_save, sender='chamas.Loan')
def assess_loan(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        FraudDetectionService.assess_transaction(
            user=instance.borrower.user,
            transaction_type='LOAN',
            transaction_ref=str(instance.id),
            amount=instance.principal,
            ip_address=instance.borrower.user.last_login_ip,
        )
    except Exception as e:
        logger.error(f"Fraud assessment failed for loan {instance.id}: {e}")