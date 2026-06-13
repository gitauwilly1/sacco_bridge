import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q

logger = logging.getLogger(__name__)


class ChamaHealthService:

    @classmethod
    def calculate_health_score(cls, chama):
        scores = {}

        # 1. Contribution Rate (30 points)
        scores['contribution_rate'] = cls._calculate_contribution_rate(chama)

        # 2. Loan Performance (25 points)
        scores['loan_performance'] = cls._calculate_loan_performance(chama)

        # 3. Meeting Attendance (20 points)
        scores['meeting_attendance'] = cls._calculate_attendance(chama)

        # 4. Savings Growth (15 points)
        scores['savings_growth'] = cls._calculate_savings_growth(chama)

        # 5. Member Retention (10 points)
        scores['member_retention'] = cls._calculate_retention(chama)

        # Weighted total
        weights = {
            'contribution_rate': Decimal('0.30'),
            'loan_performance': Decimal('0.25'),
            'meeting_attendance': Decimal('0.20'),
            'savings_growth': Decimal('0.15'),
            'member_retention': Decimal('0.10'),
        }

        total = sum(
            scores[key] * weights[key] for key in weights
        )

        grade = cls._get_grade(total)

        return {
            'score': total.quantize(Decimal('0.1')),
            'grade': grade,
            'breakdown': {k: str(v.quantize(Decimal('0.1'))) for k, v in scores.items()},
        }

    @classmethod
    def _calculate_contribution_rate(cls, chama):
        from apps.chamas.models import Contribution, ContributionStatus

        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

        contributions = Contribution.objects.filter(
            chama=chama,
            period_start__gte=thirty_days_ago,
            is_deleted=False,
        )

        total = contributions.count()
        if total == 0:
            return Decimal('50.0')

        on_time = contributions.filter(status=ContributionStatus.PAID).count()
        late = contributions.filter(status=ContributionStatus.LATE).count()

        # On-time: full points, late: half points, missed: zero
        effective = on_time + (late * Decimal('0.5'))
        rate = (Decimal(str(effective)) / Decimal(str(total))) * Decimal('100')

        return min(Decimal('100'), rate)

    @classmethod
    def _calculate_loan_performance(cls, chama):
        from apps.chamas.models import Loan, LoanStatus

        loans = Loan.objects.filter(
            chama=chama,
            is_deleted=False,
        ).exclude(status__in=[LoanStatus.PENDING, LoanStatus.REJECTED])

        total = loans.count()
        if total == 0:
            return Decimal('100.0')

        fully_repaid = loans.filter(status=LoanStatus.FULLY_REPAID).count()
        defaulted = loans.filter(status__in=[LoanStatus.DEFAULTED, LoanStatus.WRITTEN_OFF]).count()

        # Repaid: full points, active: 70%, defaulted: 0
        active = total - fully_repaid - defaulted
        score = (
            (Decimal(str(fully_repaid)) * Decimal('100')) +
            (Decimal(str(active)) * Decimal('70'))
        ) / Decimal(str(total))

        return min(Decimal('100'), score)

    @classmethod
    def _calculate_attendance(cls, chama):
        from apps.chamas.models import Meeting, MeetingAttendance

        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)

        meetings = Meeting.objects.filter(
            chama=chama,
            date__gte=ninety_days_ago,
            is_deleted=False,
        )

        total_meetings = meetings.count()
        if total_meetings == 0:
            return Decimal('50.0')

        attendances = MeetingAttendance.objects.filter(
            meeting__in=meetings,
        )

        total_records = attendances.count()
        if total_records == 0:
            return Decimal('50.0')

        attended = attendances.filter(attended=True).count()
        rate = (Decimal(str(attended)) / Decimal(str(total_records))) * Decimal('100')

        return min(Decimal('100'), rate)

    @classmethod
    def _calculate_savings_growth(cls, chama):
        from apps.chamas.models import Contribution, ContributionStatus

        # This month vs last month
        today = timezone.now()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timezone.timedelta(days=1)).replace(day=1)

        this_month = Contribution.objects.filter(
            chama=chama,
            status=ContributionStatus.PAID,
            period_start__gte=this_month_start,
            is_deleted=False,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        last_month = Contribution.objects.filter(
            chama=chama,
            status=ContributionStatus.PAID,
            period_start__gte=last_month_start,
            period_start__lt=this_month_start,
            is_deleted=False,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        if last_month == Decimal('0'):
            return Decimal('50.0') if this_month > Decimal('0') else Decimal('0')

        growth = ((this_month - last_month) / last_month) * Decimal('100')

        # Growth above 10% = 100 points, 0% = 50 points, negative = scaled
        if growth >= Decimal('10'):
            return Decimal('100.0')
        elif growth >= Decimal('0'):
            return Decimal('50.0') + (growth * Decimal('5'))
        else:
            return max(Decimal('0'), Decimal('50.0') + (growth * Decimal('3')))

    @classmethod
    def _calculate_retention(cls, chama):
        from apps.chamas.models import ChamaMember

        total = ChamaMember.objects.filter(chama=chama).count()
        if total == 0:
            return Decimal('0')

        active = ChamaMember.objects.filter(chama=chama, is_active=True).count()
        rate = (Decimal(str(active)) / Decimal(str(total))) * Decimal('100')

        return rate

    @classmethod
    def _get_grade(cls, score):
        if score >= Decimal('95'):
            return 'A+'
        elif score >= Decimal('85'):
            return 'A'
        elif score >= Decimal('75'):
            return 'B'
        elif score >= Decimal('60'):
            return 'C'
        elif score >= Decimal('40'):
            return 'D'
        else:
            return 'F'

    @classmethod
    def update_chama_health(cls, chama):
        result = cls.calculate_health_score(chama)

        chama.health_score = result['score']
        chama.health_score_grade = result['grade']
        chama.health_score_breakdown = result['breakdown']
        chama.health_score_updated_at = timezone.now()
        chama.save(update_fields=[
            'health_score', 'health_score_grade',
            'health_score_breakdown', 'health_score_updated_at',
        ])

        logger.info(
            f"Health score for {chama.name}: {result['score']} ({result['grade']})"
        )
        return result