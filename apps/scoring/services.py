import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg

logger = logging.getLogger(__name__)


class CreditScoringService:

    MAX_SCORE = 850

    @classmethod
    def calculate_score(cls, user, chama):
        from apps.chamas.models import ChamaMember

        try:
            member = ChamaMember.objects.get(user=user, chama=chama, is_active=True)
        except ChamaMember.DoesNotExist:
            return None

        contribution = cls._calculate_contribution(member)
        repayment = cls._calculate_repayment(member)
        attendance = cls._calculate_attendance(member)
        savings = cls._calculate_savings(member)
        trust = cls._calculate_trust(user)

        total = contribution + repayment + attendance + savings + trust

        from apps.scoring.models import CreditScore

        return {
            'score': total,
            'grade': CreditScore.get_grade(total),
            'contribution_score': contribution,
            'repayment_score': repayment,
            'attendance_score': attendance,
            'savings_score': savings,
            'trust_score': trust,
        }

    @classmethod
    def _calculate_contribution(cls, member):
        from apps.chamas.models import Contribution, ContributionStatus

        last_12_weeks = timezone.now() - timezone.timedelta(weeks=12)
        contributions = Contribution.objects.filter(
            member=member,
            period_start__gte=last_12_weeks,
            is_deleted=False,
        )

        total = contributions.count()
        if total == 0:
            return 50

        on_time = contributions.filter(status=ContributionStatus.PAID).count()
        late = contributions.filter(status=ContributionStatus.LATE).count()

        rate = ((on_time * 1.0) + (late * 0.5)) / total
        return min(250, int(rate * 250))

    @classmethod
    def _calculate_repayment(cls, member):
        from apps.chamas.models import Loan, LoanStatus

        loans = Loan.objects.filter(
            borrower=member,
            is_deleted=False,
        ).exclude(status__in=[LoanStatus.PENDING, LoanStatus.REJECTED])

        total = loans.count()
        if total == 0:
            return 125  # Neutral - no loan history

        fully_repaid = loans.filter(status=LoanStatus.FULLY_REPAID).count()
        defaulted = loans.filter(
            status__in=[LoanStatus.DEFAULTED, LoanStatus.WRITTEN_OFF]
        ).count()

        if total == 0:
            return 125

        score = int(
            ((fully_repaid * 250) + ((total - fully_repaid - defaulted) * 175)) / total
        )
        return min(250, max(0, score))

    @classmethod
    def _calculate_attendance(cls, member):
        from apps.chamas.models import Meeting, MeetingAttendance

        last_6_months = timezone.now() - timezone.timedelta(days=180)
        meetings = Meeting.objects.filter(
            chama=member.chama,
            date__gte=last_6_months,
            is_deleted=False,
        )

        total_meetings = meetings.count()
        if total_meetings == 0:
            return 75

        attended = MeetingAttendance.objects.filter(
            meeting__in=meetings,
            member=member,
            attended=True,
        ).count()

        rate = attended / total_meetings
        return min(150, int(rate * 150))

    @classmethod
    def _calculate_savings(cls, member):
        if member.total_contributions == 0:
            return 0

        # Ratio of current balance to total contributions
        ratio = float(member.current_balance / member.total_contributions)
        return min(100, int(ratio * 100))

    @classmethod
    def _calculate_trust(cls, user):
        trust = float(user.trust_score or 0)
        return min(100, int((trust / 5.0) * 100))