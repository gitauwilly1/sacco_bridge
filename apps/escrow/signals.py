import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='transactions.SettlementIntent')
def auto_manage_escrow(sender, instance, created, **kwargs):
    from apps.escrow.models import EscrowAccount, EscrowStatus
    from apps.escrow.services import EscrowService

    # Create escrow when settlement is initiated
    if created:
        EscrowService.create_escrow(
            settlement=instance,
            buyer=instance.buyer,
            seller=instance.seller,
            amount=instance.amount,
            platform_fee=instance.platform_fee,
        )
        return

    # Get or create escrow
    try:
        escrow = instance.escrow
    except EscrowAccount.DoesNotExist:
        escrow = EscrowService.create_escrow(
            settlement=instance,
            buyer=instance.buyer,
            seller=instance.seller,
            amount=instance.amount,
            platform_fee=instance.platform_fee,
        )

    # Fund escrow when buyer debit is confirmed
    if instance.state == 'BUYER_DEBIT_CONFIRMED' and escrow.status == EscrowStatus.CREATED:
        EscrowService.fund_escrow(escrow, instance.buyer_debit_ref)

    # Release escrow when settlement is finalized
    elif instance.state == 'LEDGER_FINALIZED' and escrow.status == EscrowStatus.FUNDED:
        EscrowService.release_escrow(escrow, instance.seller_credit_ref)

    # Refund escrow when settlement is reversed
    elif instance.state == 'REVERSED' and escrow.status in [EscrowStatus.FUNDED, EscrowStatus.DISPUTED]:
        EscrowService.refund_escrow(escrow, instance.buyer_reversal_ref)

    # Mark disputed
    elif instance.state == 'DISPUTED_MANUAL':
        escrow.mark_disputed()