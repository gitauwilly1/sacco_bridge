import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChamaHealthService:
    """
    Evaluates Chama overall health based on 5 weighted pillars:
    - Contribution Rate (30%)
    - Loan Performance (25% - Balance-Weighted PAR)
    - Meeting Attendance (20%)
    - Savings Growth (15%)
    - Member Retention (10%)
    
    Provides human-readable KDPA reason codes for every factor.
    """

    @classmethod
    def calculate_health_score(cls, chama):
        breakdown = {}

        # 1. Contribution Rate (30% weight)
        c_score, c_code, c_desc = cls._calculate_contribution_rate(chama)
        breakdown['contribution_rate'] = {
            'score': str(c_score),
            'weight': '0.30',
            'reason_code': c_code,
            'description': c_desc,
        }

        # 2. Loan Performance (25% weight - Principal Balance Weighted)
        l_score, l_code, l_desc = cls._calculate_loan_performance(chama)
        breakdown['loan_performance'] = {
            'score': str(l_score),
            'weight': '0.25',
            'reason_code': l_code,
            'description': l_desc,
        }

        # 3. Meeting Attendance (20% weight)
        a_score, a_code, a_desc = cls._calculate_attendance(chama)
        breakdown['meeting_attendance'] = {
            'score': str(a_score),
            'weight': '0.20',
            'reason_code': a_code,
            'description': a_desc,
        }

        # 4. Savings Growth (15% weight)
        s_score, s_code, s_desc = cls._calculate_savings_growth(chama)
        breakdown['savings_growth'] = {
            'score': str(s_score),
            'weight': '0.15',
            'reason_code': s_code,
            'description': s_desc,
        }

        # 5. Member Retention (10% weight)
        r_score, r_code, r_desc = cls._calculate_retention(chama)
        breakdown['member_retention'] = {
            'score': str(r_score),
            'weight': '0.10',
            'reason_code': r_code,
            'description': r_desc,
        }

        weighted_total = (
            (c_score * Decimal('0.30')) +
            (l_score * Decimal('0.25')) +
            (a_score * Decimal('0.20')) +
            (s_score * Decimal('0.15')) +
            (r_score * Decimal('0.10'))
        )

        overall_score = min(Decimal('100.0'), max(Decimal('0.0'), weighted_total)).quantize(Decimal('0.1'))
        grade = cls._get_grade(overall_score)

        return {
            'score': overall_score,
            'grade': grade,
            'breakdown': breakdown,
        }

    @classmethod
    def _calculate_contribution_rate(cls, chama):
        from apps.chamas.models import Contribution, ContributionStatus

        thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
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
        unpaid = total - on_time - late

        score = (
            (Decimal(str(on_time)) * Decimal('100')) +
            (Decimal(str(late)) * Decimal('50'))
        ) / Decimal(str(total))
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), score)).quantize(Decimal('0.1'))

        # Correct severity hierarchy:
        if final_score >= Decimal('90.0'):
            code = 'CONTRIBUTION_ON_TIME_OPTIMAL'
            desc = f"Optimal on-time contribution rate ({on_time}/{total} on-time deposits)."
        elif final_score >= Decimal('70.0'):
            code = 'CONTRIBUTION_ELEVATED_LATE_RATE'
            desc = f"Moderate collection efficiency ({late} late contributions recorded)."
        elif final_score >= Decimal('50.0'):
            code = 'CONTRIBUTION_HIGH_DELINQUENCY'
            desc = f"High contribution delinquency rate ({unpaid} unpaid/missed deposits)."
        else:
            code = 'CONTRIBUTION_CRITICAL_DEFAULT_RISK'
            desc = f"Critical contribution default risk ({unpaid} unpaid deposits, score {final_score}%)."

        return final_score, code, desc

    @classmethod
    def _calculate_loan_performance(cls, chama):
        """
        Calculates loan portfolio performance weighted by principal balance (PAR standard).
        A large default impacts score proportionally to capital at risk.
        """
        from apps.chamas.models import Loan, LoanStatus

        loans = Loan.objects.filter(
            chama=chama,
            is_deleted=False,
        ).exclude(status__in=[LoanStatus.PENDING, LoanStatus.REJECTED])

        total_count = loans.count()
        if total_count == 0:
            return Decimal('100.0'), 'LOAN_NO_ACTIVE_DEBT', 'No active or historical loans in chama; pristine credit portfolio.'

        total_principal = loans.aggregate(total=Sum('principal'))['total'] or Decimal('0')
        if total_principal == Decimal('0'):
            return Decimal('100.0'), 'LOAN_NO_ACTIVE_DEBT', 'Zero evaluated loan principal; pristine portfolio.'

        repaid_principal = loans.filter(status=LoanStatus.FULLY_REPAID).aggregate(total=Sum('principal'))['total'] or Decimal('0')
        defaulted_principal = loans.filter(status__in=[LoanStatus.DEFAULTED, LoanStatus.WRITTEN_OFF]).aggregate(total=Sum('principal'))['total'] or Decimal('0')
        active_principal = total_principal - repaid_principal - defaulted_principal

        # Principal-Weighted Scoring:
        # Repaid: 100%, Active performing: 70%, Defaulted: 0%
        weighted_sum = (
            (repaid_principal * Decimal('100')) +
            (active_principal * Decimal('70'))
        )
        score = weighted_sum / total_principal
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), score)).quantize(Decimal('0.1'))

        defaulted_count = loans.filter(status__in=[LoanStatus.DEFAULTED, LoanStatus.WRITTEN_OFF]).count()
        active_count = loans.filter(status__in=[LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID]).count()

        if defaulted_principal > Decimal('0'):
            default_ratio = ((defaulted_principal / total_principal) * Decimal('100')).quantize(Decimal('0.1'))
            if default_ratio >= Decimal('30.0'):
                code = 'LOAN_DEFAULT_IMPAIRMENT'
                desc = f"Critical portfolio impairment: KSh {defaulted_principal:,.2f} ({default_ratio}% of portfolio) in default ({defaulted_count} loan(s))."
            else:
                code = 'LOAN_PAR_WARNING'
                desc = f"Portfolio-at-Risk warning: KSh {defaulted_principal:,.2f} ({default_ratio}% of portfolio) in default ({defaulted_count} loan(s))."
        elif repaid_principal == total_principal:
            code = 'LOAN_PORTFOLIO_PERFECT_REPAYMENT'
            desc = f"100% full principal repayment (KSh {repaid_principal:,.2f} across all {total_count} loans)."
        else:
            code = 'LOAN_PORTFOLIO_PERFORMING'
            desc = f"Active performing portfolio: KSh {active_principal:,.2f} active principal ({active_count} loans, 0 defaults)."

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
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), rate)).quantize(Decimal('0.1'))

        if final_score >= Decimal('85.0'):
            code = 'ATTENDANCE_EXEMPLARY_ENGAGEMENT'
            desc = f"Exemplary meeting attendance ({rate.quantize(Decimal('0.1'))}% attendance rate)."
        elif final_score >= Decimal('60.0'):
            code = 'ATTENDANCE_SUBPAR_ENGAGEMENT'
            desc = f"Subpar meeting attendance ({rate.quantize(Decimal('0.1'))}% attendance rate)."
        else:
            code = 'ATTENDANCE_POOR_ENGAGEMENT'
            desc = f"Poor meeting attendance ({rate.quantize(Decimal('0.1'))}% attendance rate); quorum and governance risk."

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
                return Decimal('50.0'), 'SAVINGS_NEW_DEPOSITS_INITIATED', f"New savings initiated this month (KSh {this_month:,.2f}) with zero prior baseline."
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
            code = 'SAVINGS_DEPOSIT_CONTRACTION'
            desc = f"Month-over-month deposit contraction ({growth.quantize(Decimal('0.1'))}%)."

        return min(Decimal('100.0'), max(Decimal('0.0'), score)).quantize(Decimal('0.1')), code, desc

    @classmethod
    def _calculate_retention(cls, chama):
        from apps.chamas.models import ChamaMember

        total = ChamaMember.objects.filter(chama=chama).count()
        if total == 0:
            return Decimal('0.0'), 'RETENTION_ZERO_MEMBERS', 'Chama has no registered members.'

        active = ChamaMember.objects.filter(chama=chama, is_active=True).count()
        rate = (Decimal(str(active)) / Decimal(str(total))) * Decimal('100')
        final_score = min(Decimal('100.0'), max(Decimal('0.0'), rate)).quantize(Decimal('0.1'))

        if final_score >= Decimal('90.0'):
            code = 'RETENTION_STABLE_MEMBERSHIP'
            desc = f"Stable membership retention ({active}/{total} active members)."
        elif final_score >= Decimal('70.0'):
            code = 'RETENTION_MODERATE_CHURN'
            desc = f"Moderate membership churn ({total - active} inactive members)."
        else:
            code = 'RETENTION_ATTRITION_WARNING'
            desc = f"High membership attrition warning ({active}/{total} active members)."

        return final_score, code, desc

    @classmethod
    def _get_grade(cls, score):
        """
        Deterministic 10-point decile grading scale:
        - A+ : 90.0 - 100.0 (Prime Chama, Tier-1 Credit Eligible)
        - A  : 80.0 - 89.9  (Excellent Health, Standard Automated Credit Limits)
        - B  : 70.0 - 79.9  (Good Health, Standard Terms)
        - C  : 60.0 - 69.9  (Fair Health, Baseline New Group Rating)
        - D  : 50.0 - 59.9  (Vulnerable, Heightened Monitoring Required)
        - F  : < 50.0       (Distressed, Automated Lending Restrictions Enforced)
        """
        if score >= Decimal('90.0'):
            return 'A+'
        elif score >= Decimal('80.0'):
            return 'A'
        elif score >= Decimal('70.0'):
            return 'B'
        elif score >= Decimal('60.0'):
            return 'C'
        elif score >= Decimal('50.0'):
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
