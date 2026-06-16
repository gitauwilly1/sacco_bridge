"""Escrow service for managing fund holds and releases."""

import logging
from decimal import Decimal

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