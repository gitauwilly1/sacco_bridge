import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChamaHealthService:
    """
    Automated Chama Health & Reliability Evaluation Service.
    
    Business & Domain Weighting Architecture:
    -----------------------------------------
    1. Contribution Rate (30% / 0.30):
       Primary indicator of group financial discipline and liquidity predictability.
       Timely contributions ensure loan fund availability and rotating payout reliability.
       
    2. Loan Performance (25% / 0.25):
       Direct measure of portfolio credit risk. Defaulted or written-off loans impair
       collective chama capital and trigger contagion defaults among guarantors.
       
    3. Meeting Attendance (20% / 0.20):
       Evaluates social governance and cohesion over a 90-day window. Physical or virtual
       meeting attendance correlates strongly with dispute prevention and member accountability.
       
    4. Savings Growth (15% / 0.15):
       Month-over-month capital accumulation rate, measuring whether the chama is expanding
       or contracting its deposit base.
       
    5. Member Retention (10% / 0.10):
       Stability metric evaluating member churn and active participation vs total roster.
    
    KDPA & Fair Lending Compliance:
    -------------------------------
    In compliance with the Kenya Data Protection Act (KDPA 2019) automated processing
    and explainability guidelines, every health calculation outputs machine- and human-readable
    reason codes explaining the rationale behind sub-scores.
    """

    WEIGHTS = {
        'contribution_rate': Decimal('0.30'),
        'loan_performance': Decimal('0.25'),
        'meeting_attendance': Decimal('0.20'),
        'savings_growth': Decimal('0.15'),
        'member_retention': Decimal('0.10'),
    }

    @classmethod
    def calculate_health_score(cls, chama):
        scores = {}
        reason_codes = {}
        descriptions = {}

        # 1. Contribution Rate (30% weight)
        cr_score, cr_code, cr_desc = cls._calculate_contribution_rate(chama)
        scores['contribution_rate'] = cr_score
        reason_codes['contribution_rate'] = cr_code
        descriptions['contribution_rate'] = cr_desc

        # 2. Loan Performance (25% weight)
        lp_score, lp_code, lp_desc = cls._calculate_loan_performance(chama)
        scores['loan_performance'] = lp_score
        reason_codes['loan_performance'] = lp_code
        descriptions['loan_performance'] = lp_desc

        # 3. Meeting Attendance (20% weight)
        ma_score, ma_code, ma_desc = cls._calculate_attendance(chama)
        scores['meeting_attendance'] = ma_score
        reason_codes['meeting_attendance'] = ma_code
        descriptions['meeting_attendance'] = ma_desc

        # 4. Savings Growth (15% weight)
        sg_score, sg_code, sg_desc = cls._calculate_savings_growth(chama)
        scores['savings_growth'] = sg_score
        reason_codes['savings_growth'] = sg_code
        descriptions['savings_growth'] = sg_desc

        # 5. Member Retention (10% weight)
        mr_score, mr_code, mr_desc = cls._calculate_retention(chama)
        scores['member_retention'] = mr_score
        reason_codes['member_retention'] = mr_code
        descriptions['member_retention'] = mr_desc

        # Weighted total computation
        total = sum(
            scores[key] * cls.WEIGHTS[key] for key in cls.WEIGHTS
        )
        total_bounded = max(Decimal('0.0'), min(Decimal('100.0'), total))
        grade = cls._get_grade(total_bounded)

        breakdown = {
            k: {
                'score': str(scores[k].quantize(Decimal('0.1'))),
                'weight': str(cls.WEIGHTS[k]),
                'reason_code': reason_codes[k],
                'description': descriptions[k],
            }
            for k in cls.WEIGHTS
        }

        return {
            'score': total_bounded.quantize(Decimal('0.1')),
            'grade': grade,
            'breakdown': breakdown,
            'calculated_at': timezone.now().isoformat(),
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
            return Decimal('50.0'), 'CONTRIBUTION_INSUFFICIENT_HISTORY', 'No contribution records found in the last 30 days; baseline neutral score applied.'

        on_time = contributions.filter(status=ContributionStatus.PAID).count()
        late = contributions.filter(status=ContributionStatus.LATE).count()

        # On-time: 100% points, late: 50% points, missed/unpaid: 0 points
        effective = Decimal(str(on_time)) + (Decimal(str(late)) * Decimal('0.5'))
        rate = (effective / Decimal(str(total))) * Decimal('100')
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), rate))

        if final_score >= Decimal('90.0'):
            code = 'CONTRIBUTION_ON_TIME_OPTIMAL'
            desc = f"Excellent timely contribution compliance ({on_time}/{total} on-time)."
        elif final_score >= Decimal('60.0'):
            code = 'CONTRIBUTION_MODERATE_DELINQUENCY'
            desc = f"Moderate contribution delinquency detected ({late} late payments)."
        else:
            code = 'CONTRIBUTION_HIGH_DELINQUENCY'
            desc = f"High contribution default/missed rate ({total - on_time - late} unpaid)."

        return final_score, code, desc

    @classmethod
    def _calculate_loan_performance(cls, chama):
        from apps.chamas.models import Loan, LoanStatus

        loans = Loan.objects.filter(
            chama=chama,
            is_deleted=False,
        ).exclude(status__in=[LoanStatus.PENDING, LoanStatus.REJECTED])

        total = loans.count()
        if total == 0:
            return Decimal('100.0'), 'LOAN_NO_ACTIVE_DEBT', 'No active or historical loans in chama; pristine credit portfolio.'

        fully_repaid = loans.filter(status=LoanStatus.FULLY_REPAID).count()
        defaulted = loans.filter(status__in=[LoanStatus.DEFAULTED, LoanStatus.WRITTEN_OFF]).count()
        active = total - fully_repaid - defaulted

        # Repaid: 100%, Active: 70%, Defaulted: 0%
        score = (
            (Decimal(str(fully_repaid)) * Decimal('100')) +
            (Decimal(str(active)) * Decimal('70'))
        ) / Decimal(str(total))
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), score))

        if defaulted > 0:
            code = 'LOAN_DEFAULT_IMPAIRMENT'
            desc = f"Portfolio impaired: {defaulted} loan(s) in default or written off."
        elif fully_repaid == total:
            code = 'LOAN_PORTFOLIO_PERFECT_REPAYMENT'
            desc = f"100% full repayment rate across all {total} historical loans."
        else:
            code = 'LOAN_PORTFOLIO_PERFORMING'
            desc = f"Portfolio active and performing ({active} active loans, 0 defaults)."

        return final_score, code, desc

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
            return Decimal('50.0'), 'ATTENDANCE_NO_MEETINGS_CONVENED', 'No meetings scheduled in the past 90 days; baseline neutral score applied.'

        attendances = MeetingAttendance.objects.filter(
            meeting__in=meetings,
        )
        total_records = attendances.count()
        if total_records == 0:
            return Decimal('50.0'), 'ATTENDANCE_NO_RECORDS', 'Meeting attendance not tracked; baseline neutral score applied.'

        attended = attendances.filter(attended=True).count()
        rate = (Decimal(str(attended)) / Decimal(str(total_records))) * Decimal('100')
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), rate))

        if final_score >= Decimal('85.0'):
            code = 'ATTENDANCE_EXEMPLARY_ENGAGEMENT'
            desc = f"Strong meeting attendance ({rate.quantize(Decimal('0.1'))}% attendance rate)."
        elif final_score >= Decimal('60.0'):
            code = 'ATTENDANCE_ACCEPTABLE_ENGAGEMENT'
            desc = f"Moderate meeting attendance ({rate.quantize(Decimal('0.1'))}% attendance rate)."
        else:
            code = 'ATTENDANCE_POOR_ENGAGEMENT'
            desc = f"Low meeting attendance ({rate.quantize(Decimal('0.1'))}% attendance rate); quorum risk."

        return final_score, code, desc

    @classmethod
    def _calculate_savings_growth(cls, chama):
        from apps.chamas.models import Contribution, ContributionStatus

        today = timezone.now()
        this_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timezone.timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

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
            if this_month > Decimal('0'):
                return Decimal('50.0'), 'SAVINGS_NEW_DEPOSITS_INITIATED', 'New savings initiated this month with zero prior baseline.'
            return Decimal('0.0'), 'SAVINGS_ZERO_ACTIVITY', 'Zero savings deposits recorded in current and prior month.'

        growth = ((this_month - last_month) / last_month) * Decimal('100')

        if growth >= Decimal('10.0'):
            score = Decimal('100.0')
            code = 'SAVINGS_EXPANSION_EXCELLENT'
            desc = f"Robust month-over-month savings growth (+{growth.quantize(Decimal('0.1'))}%)."
        elif growth >= Decimal('0.0'):
            score = Decimal('50.0') + (growth * Decimal('5'))
            code = 'SAVINGS_STABLE_GROWTH'
            desc = f"Stable month-over-month savings growth (+{growth.quantize(Decimal('0.1'))}%)."
        else:
            score = max(Decimal('0.0'), Decimal('50.0') + (growth * Decimal('3')))
            code = 'SAVINGS_CONTRACTION'
            desc = f"Month-over-month deposit contraction ({growth.quantize(Decimal('0.1'))}%)."

        return min(Decimal('100.0'), max(Decimal('0.0'), score)), code, desc

    @classmethod
    def _calculate_retention(cls, chama):
        from apps.chamas.models import ChamaMember

        total = ChamaMember.objects.filter(chama=chama).count()
        if total == 0:
            return Decimal('0.0'), 'RETENTION_ZERO_MEMBERS', 'Chama has no registered members.'

        active = ChamaMember.objects.filter(chama=chama, is_active=True).count()
        rate = (Decimal(str(active)) / Decimal(str(total))) * Decimal('100')
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), rate))

        if final_score >= Decimal('90.0'):
            code = 'RETENTION_STABLE_MEMBERSHIP'
            desc = f"High membership retention ({active}/{total} active members)."
        elif final_score >= Decimal('70.0'):
            code = 'RETENTION_MODERATE_CHURN'
            desc = f"Moderate membership churn ({total - active} inactive members)."
        else:
            code = 'RETENTION_HIGH_CHURN_RISK'
            desc = f"High membership attrition ({active}/{total} active members)."

        return final_score, code, desc

    @classmethod
    def _get_grade(cls, score):
        if score >= Decimal('95.0'):
            return 'A+'
        elif score >= Decimal('85.0'):
            return 'A'
        elif score >= Decimal('75.0'):
            return 'B'
        elif score >= Decimal('60.0'):
            return 'C'
        elif score >= Decimal('40.0'):
            return 'D'
        else:
            return 'F'

    @classmethod
    def update_chama_health(cls, chama):
        """
        Calculates and atomically updates health metrics on the Chama instance
        with select_for_update row locking to prevent race conditions.
        """
        from apps.chamas.models import Chama

        with transaction.atomic():
            locked_chama = Chama.objects.select_for_update().get(pk=chama.pk)
            result = cls.calculate_health_score(locked_chama)

            locked_chama.health_score = result['score']
            locked_chama.health_score_grade = result['grade']
            locked_chama.health_score_breakdown = result['breakdown']
            locked_chama.health_score_updated_at = timezone.now()
            locked_chama.save(update_fields=[
                'health_score', 'health_score_grade',
                'health_score_breakdown', 'health_score_updated_at',
            ])

            logger.info(
                f"Health score atomically updated for {locked_chama.name}: {result['score']} ({result['grade']})"
            )
            return result
