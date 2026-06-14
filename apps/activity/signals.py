import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.activity.models import ActivityLog, ActivityType

logger = logging.getLogger(__name__)


# CHAMA SIGNALS

@receiver(post_save, sender='chamas.Chama')
def log_chama_created(sender, instance, created, **kwargs):
    if created and instance.created_by:
        ActivityLog.log(
            user=instance.created_by,
            activity_type=ActivityType.CHAMA_CREATED,
            title=f'Created chama "{instance.name}"',
            description=f'A new {instance.get_chama_type_display()} has been formed.',
            chama=instance,
            reference_id=instance.id,
            reference_type='Chama',
        )


@receiver(post_save, sender='chamas.Contribution')
def log_contribution(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.member.user,
            activity_type=ActivityType.CONTRIBUTION_MADE,
            title=f'Contributed KSh {instance.amount:,.2f} to {instance.chama.name}',
            description=f'Payment via {instance.get_payment_method_display()}.',
            chama=instance.chama,
            reference_id=instance.id,
            reference_type='Contribution',
            metadata={'amount': str(instance.amount), 'status': instance.status},
        )


@receiver(post_save, sender='chamas.Loan')
def log_loan(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.borrower.user,
            activity_type=ActivityType.LOAN_APPLIED,
            title=f'Applied for loan of KSh {instance.principal:,.2f} from {instance.chama.name}',
            description=f'Purpose: {instance.purpose}. Duration: {instance.duration_months} months.',
            chama=instance.chama,
            reference_id=instance.id,
            reference_type='Loan',
            metadata={'principal': str(instance.principal), 'status': instance.status},
        )
    elif instance.status == 'APPROVED' and instance.approved_by:
        ActivityLog.log(
            user=instance.approved_by.user,
            activity_type=ActivityType.LOAN_APPROVED,
            title=f'Approved loan of KSh {instance.principal:,.2f} for {instance.borrower.user.get_full_name()}',
            chama=instance.chama,
            reference_id=instance.id,
            reference_type='Loan',
        )
    elif instance.status == 'DISBURSED':
        ActivityLog.log(
            user=instance.borrower.user,
            activity_type=ActivityType.LOAN_DISBURSED,
            title=f'Received loan disbursement of KSh {instance.principal:,.2f} from {instance.chama.name}',
            chama=instance.chama,
            reference_id=instance.id,
            reference_type='Loan',
            metadata={'principal': str(instance.principal)},
        )


@receiver(post_save, sender='chamas.LoanRepayment')
def log_loan_repayment(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.loan.borrower.user,
            activity_type=ActivityType.LOAN_REPAID,
            title=f'Repaid KSh {instance.amount:,.2f} on loan from {instance.loan.chama.name}',
            description=f'Remaining balance: KSh {instance.loan.outstanding_balance:,.2f}.',
            chama=instance.loan.chama,
            reference_id=instance.id,
            reference_type='LoanRepayment',
            metadata={'amount': str(instance.amount)},
        )


@receiver(post_save, sender='chamas.Meeting')
def log_meeting(sender, instance, created, **kwargs):
    if created and instance.organizer:
        ActivityLog.log(
            user=instance.organizer.user,
            activity_type=ActivityType.MEETING_SCHEDULED,
            title=f'Scheduled meeting: {instance.title}',
            description=f'{instance.date.strftime("%d %B %Y")} at {instance.start_time.strftime("%H:%M")}. Location: {instance.location}.',
            chama=instance.chama,
            reference_id=instance.id,
            reference_type='Meeting',
        )


# INVESTMENT SIGNALS

@receiver(post_save, sender='investments.LiquidityRequest')
def log_liquidity_request(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.seller,
            activity_type=ActivityType.LIQUIDITY_REQUESTED,
            title=f'Listed {instance.share_quantity} shares in {instance.sacco.name} for sale',
            description=f'Expected price: KSh {instance.expected_price_per_share:,.2f}/share.',
            sacco=instance.sacco,
            reference_id=instance.id,
            reference_type='LiquidityRequest',
            metadata={
                'share_quantity': str(instance.share_quantity),
                'expected_price': str(instance.expected_price_per_share),
            },
        )


@receiver(post_save, sender='investments.BuyerInterest')
def log_buyer_interest(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.buyer,
            activity_type=ActivityType.INTEREST_EXPRESSED,
            title=f'Expressed interest in {instance.liquidity_request.share_quantity} shares of {instance.liquidity_request.sacco.name}',
            sacco=instance.liquidity_request.sacco,
            reference_id=instance.id,
            reference_type='BuyerInterest',
        )


@receiver(post_save, sender='investments.Offer')
def log_offer(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.offered_by,
            activity_type=ActivityType.OFFER_MADE,
            title=f'Made offer: KSh {instance.price_per_share:,.2f}/share for {instance.quantity} shares',
            sacco=instance.connection.liquidity_request.sacco,
            reference_id=instance.id,
            reference_type='Offer',
            metadata={
                'price_per_share': str(instance.price_per_share),
                'quantity': str(instance.quantity),
            },
        )
    elif instance.status == 'ACCEPTED':
        ActivityLog.log(
            user=instance.connection.seller if instance.offered_by == instance.connection.buyer else instance.connection.buyer,
            activity_type=ActivityType.OFFER_ACCEPTED,
            title=f'Accepted offer: KSh {instance.price_per_share:,.2f}/share for {instance.quantity} shares',
            sacco=instance.connection.liquidity_request.sacco,
            reference_id=instance.id,
            reference_type='Offer',
            metadata={'total_amount': str(instance.total_amount)},
        )


# TRANSACTION SIGNALS

@receiver(post_save, sender='transactions.SettlementIntent')
def log_settlement(sender, instance, created, **kwargs):
    if created:
        ActivityLog.log(
            user=instance.buyer,
            activity_type=ActivityType.SETTLEMENT_INITIATED,
            title=f'Settlement initiated: {instance.share_quantity} shares in {instance.seller_sacco_name}',
            description=f'Amount: KSh {instance.amount:,.2f}.',
            sacco=None,
            reference_id=instance.uuid,
            reference_type='SettlementIntent',
            metadata={'amount': str(instance.amount), 'sacco_id': instance.seller_sacco_id},
        )
    elif instance.state == 'LEDGER_FINALIZED':
        ActivityLog.log(
            user=instance.buyer,
            activity_type=ActivityType.SETTLEMENT_COMPLETED,
            title=f'Settlement completed: {instance.share_quantity} shares transferred',
            description=f'Final amount: KSh {instance.amount:,.2f}.',
            reference_id=instance.uuid,
            reference_type='SettlementIntent',
            metadata={'amount': str(instance.amount), 'fee': str(instance.platform_fee)},
        )
        ActivityLog.log(
            user=instance.seller,
            activity_type=ActivityType.SETTLEMENT_COMPLETED,
            title=f'Share sale completed: KSh {instance.amount:,.2f} received',
            description=f'Sold {instance.share_quantity} shares in {instance.seller_sacco_name}.',
            reference_id=instance.uuid,
            reference_type='SettlementIntent',
            metadata={'amount': str(instance.amount)},
        )
    elif instance.state == 'DISPUTED_MANUAL':
        ActivityLog.log(
            user=instance.buyer,
            activity_type=ActivityType.SETTLEMENT_DISPUTED,
            title=f'Settlement disputed: Transaction #{str(instance.uuid)[:8]}',
            reference_id=instance.uuid,
            reference_type='SettlementIntent',
        )