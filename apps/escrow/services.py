"""Escrow service for managing fund holds and releases."""

import logging
from decimal import Decimal
from time import timezone

from django.db import models

from apps.escrow.models import EscrowAccount, EscrowStatus

logger = logging.getLogger(__name__)


class EscrowService:

    @classmethod
    def create_escrow(cls, settlement, buyer, seller, amount, platform_fee=Decimal('0.00')):
        escrow = EscrowAccount.objects.create(
            settlement=settlement,
            buyer=buyer,
            seller=seller,
            amount=amount,
            platform_fee=platform_fee,
            status=EscrowStatus.CREATED,
        )
        logger.info(f"Escrow created: {escrow.id} for settlement {settlement.uuid}")
        return escrow

    @classmethod
    def fund_escrow(cls, escrow, buyer_ref=''):
        if escrow.status != EscrowStatus.CREATED:
            raise ValueError(f"Cannot fund escrow in {escrow.status} state.")
        escrow.mark_funded(buyer_ref)
        logger.info(f"Escrow {escrow.id} funded: KSh {escrow.amount}")

    @classmethod
    def release_escrow(cls, escrow, seller_ref=''):
        if escrow.status != EscrowStatus.FUNDED:
            raise ValueError(f"Cannot release escrow in {escrow.status} state.")
        escrow.mark_released(seller_ref)
        logger.info(f"Escrow {escrow.id} released to seller")

    @classmethod
    def refund_escrow(cls, escrow, refund_ref=''):
        if escrow.status not in [EscrowStatus.FUNDED, EscrowStatus.DISPUTED]:
            raise ValueError(f"Cannot refund escrow in {escrow.status} state.")
        escrow.mark_refunded(refund_ref)
        logger.info(f"Escrow {escrow.id} refunded to buyer")

    @classmethod
    def cancel_escrow(cls, escrow, reason=''):
        if escrow.status not in [EscrowStatus.CREATED, EscrowStatus.FUNDED, EscrowStatus.HELD]:
            raise ValueError(f"Cannot cancel escrow in {escrow.status} state.")
        
        escrow.status = EscrowStatus.CANCELLED
        escrow.hold_reason = reason or 'Liquidity request cancelled'
        escrow.completed_at = timezone.now()
        escrow.save()
        
        logger.info(f"Escrow {escrow.id} cancelled: {reason}")
        return escrow

    @classmethod
    def get_escrow_summary(cls, user):
        as_buyer = EscrowAccount.objects.filter(buyer=user)
        as_seller = EscrowAccount.objects.filter(seller=user)

        return {
            'total_held': str(
                as_buyer.filter(status=EscrowStatus.FUNDED).aggregate(
                    total=models.Sum('amount')
                )['total'] or Decimal('0.00')
            ),
            'total_received': str(
                as_seller.filter(status=EscrowStatus.RELEASED).aggregate(
                    total=models.Sum('amount')
                )['total'] or Decimal('0.00')
            ),
            'active_escrows': as_buyer.filter(
                status__in=[EscrowStatus.CREATED, EscrowStatus.FUNDED]
            ).count() + as_seller.filter(
                status__in=[EscrowStatus.CREATED, EscrowStatus.FUNDED]
            ).count(),
        }
    
    @classmethod
    def should_hold(cls, escrow):
        from apps.fraud.models import TransactionRiskAssessment, RiskLevel

        # Check fraud assessment
        assessment = TransactionRiskAssessment.objects.filter(
            transaction_reference=str(escrow.settlement.uuid)
        ).first()

        if assessment:
            if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return True, assessment.risk_level, 'Fraud detection flagged'

        # Large transaction hold
        from django.conf import settings
        large_threshold = Decimal('100000.00')
        if escrow.amount >= large_threshold:
            return True, 'LARGE_AMOUNT', f'Amount KSh {escrow.amount:,.2f} exceeds threshold'

        # First transaction hold
        previous_escrows = EscrowAccount.objects.filter(
            buyer=escrow.buyer,
            status=EscrowStatus.RELEASED,
        ).count()

        if previous_escrows == 0:
            return True, 'FIRST_TRANSACTION', 'First transaction requires review'

        return False, None, None

    @classmethod
    def apply_hold_if_needed(cls, escrow):
        should_hold, trigger, reason = cls.should_hold(escrow)

        if should_hold:
            escrow.mark_held(reason=reason, trigger=trigger)
            logger.info(f"Escrow {escrow.id} held: {reason}")
            return True

        return False