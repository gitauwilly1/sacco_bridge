import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.fraud.services import FraudDetectionService
from apps.transactions.models import SettlementIntent

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
            from apps.transactions.models import SettlementState
            
            updated = SettlementIntent.objects.filter(
                pk=instance.pk,
                state__in=['MATCH_PROPOSED', 'INTENT_LOCKED', 'BUYER_DEBIT_INITIATED'],
            ).update(
                state=SettlementState.DISPUTED_MANUAL,
                dispute_opened_at=timezone.now(),
            )
            
            if updated:
                instance.refresh_from_db()
                
                from apps.escrow.models import EscrowAccount
                escrow = EscrowAccount.objects.filter(
                    settlement=instance
                ).first()
                
                if escrow and escrow.status in ['CREATED', 'FUNDED']:
                    escrow.mark_held(
                        reason=f'Fraud detection: score {assessment.risk_score}',
                        trigger='FRAUD_DETECTION',
                    )
                
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