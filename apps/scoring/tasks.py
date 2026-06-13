import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.scoring.tasks.update_credit_scores',
    bind=True,
    max_retries=1,
)
def update_credit_scores(self):
    from apps.chamas.models import ChamaMember
    from apps.scoring.models import CreditScore
    from apps.scoring.services import CreditScoringService

    logger.info("Starting credit score update...")

    members = ChamaMember.objects.filter(is_active=True).select_related('user', 'chama')
    updated = 0

    for member in members:
        try:
            result = CreditScoringService.calculate_score(member.user, member.chama)
            if result:
                CreditScore.objects.create(
                    user=member.user,
                    chama=member.chama,
                    score=result['score'],
                    grade=result['grade'],
                    contribution_score=result['contribution_score'],
                    repayment_score=result['repayment_score'],
                    attendance_score=result['attendance_score'],
                    savings_score=result['savings_score'],
                    trust_score=result['trust_score'],
                    valid_until=timezone.now() + timezone.timedelta(days=30),
                )
                updated += 1
        except Exception as e:
            logger.error(f"Score failed for member {member.id}: {e}")

    logger.info(f"Credit scores updated for {updated} members")
    return {'updated': updated}