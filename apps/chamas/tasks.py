import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.chamas.tasks.send_contribution_reminders',
    bind=True,
    max_retries=1,
    default_retry_delay=3600,
)
def send_contribution_reminders(self):
    logger.info("Starting contribution reminder scan...")

    from apps.chamas.models import ChamaMember, Contribution, ContributionStatus
    from apps.notifications.services import NotificationService
    from apps.notifications.models import NotificationCategory, NotificationPriority

    try:
        today = timezone.now().date()
        reminder_count = 0
        overdue_count = 0

        # Find members with contributions due in the next 2 days
        upcoming_end = today + timezone.timedelta(days=2)

        upcoming_contributions = Contribution.objects.filter(
            status=ContributionStatus.PENDING,
            period_end__gte=today,
            period_end__lte=upcoming_end,
            is_deleted=False,
        ).select_related('member__user', 'chama')

        for contribution in upcoming_contributions:
            try:
                NotificationService.create_notification(
                    user=contribution.member.user,
                    category=NotificationCategory.CHAMA_CONTRIBUTION,
                    title='Contribution Due Soon',
                    body=(
                        f'Your contribution of KSh {contribution.amount} to '
                        f'{contribution.chama.name} is due by {contribution.period_end}.'
                    ),
                    priority=NotificationPriority.HIGH,
                    action_url=f'/chamas/{contribution.chama.id}/contributions/',
                )
                reminder_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder: {str(e)}")

        # Find overdue members
        overdue_members = ChamaMember.objects.filter(
            is_active=True,
            is_overdue=True,
        ).select_related('user', 'chama')

        for member in overdue_members:
            try:
                NotificationService.create_notification(
                    user=member.user,
                    category=NotificationCategory.CHAMA_CONTRIBUTION,
                    title='Contribution Overdue',
                    body=(
                        f'Your contribution of KSh {member.overdue_amount} to '
                        f'{member.chama.name} is overdue. Late fees may apply.'
                    ),
                    priority=NotificationPriority.URGENT,
                    action_url=f'/chamas/{member.chama.id}/contributions/',
                )
                overdue_count += 1
            except Exception as e:
                logger.error(f"Failed to send overdue notice: {str(e)}")

        logger.info(
            f"Contribution reminders complete: "
            f"{reminder_count} upcoming, {overdue_count} overdue"
        )

        return {
            'upcoming_reminders': reminder_count,
            'overdue_reminders': overdue_count,
        }

    except Exception as e:
        logger.error(f"Contribution reminders failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.chamas.tasks.send_loan_repayment_reminders',
    bind=True,
    max_retries=1,
    default_retry_delay=3600,
)
def send_loan_repayment_reminders(self):
    logger.info("Starting loan repayment reminder scan...")

    from apps.chamas.models import Loan, LoanStatus
    from apps.notifications.services import NotificationService
    from apps.notifications.models import NotificationCategory, NotificationPriority

    try:
        today = timezone.now().date()
        upcoming_due = today + timezone.timedelta(days=3)

        active_loans = Loan.objects.filter(
            status__in=[LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID],
            due_date__lte=upcoming_due,
            due_date__gte=today - timezone.timedelta(days=7),
            is_deleted=False,
        ).select_related('borrower__user', 'chama')

        reminder_count = 0

        for loan in active_loans:
            try:
                days_remaining = (loan.due_date - today).days

                if days_remaining <= 0:
                    title = 'Loan Payment Overdue'
                    body = (
                        f'Your loan repayment of KSh {loan.monthly_installment} '
                        f'to {loan.chama.name} is overdue. '
                        f'Outstanding balance: KSh {loan.outstanding_balance}.'
                    )
                    priority = NotificationPriority.URGENT
                elif days_remaining <= 3:
                    title = 'Loan Payment Due Soon'
                    body = (
                        f'Your loan repayment of KSh {loan.monthly_installment} '
                        f'to {loan.chama.name} is due in {days_remaining} days.'
                    )
                    priority = NotificationPriority.HIGH
                else:
                    continue

                NotificationService.create_notification(
                    user=loan.borrower.user,
                    category=NotificationCategory.CHAMA_LOAN,
                    title=title,
                    body=body,
                    priority=priority,
                    action_url=f'/chamas/{loan.chama.id}/loans/{loan.id}/',
                )
                reminder_count += 1

            except Exception as e:
                logger.error(f"Failed to send loan reminder: {str(e)}")

        logger.info(f"Loan repayment reminders complete: {reminder_count} sent")

        return {'reminders_sent': reminder_count}

    except Exception as e:
        logger.error(f"Loan repayment reminders failed: {str(e)}")
        raise self.retry(exc=e)