import pytest
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
from apps.users.models import User
from apps.chamas.models import (
    Chama, ChamaMember, MemberRole, ChamaStatus,
    Contribution, ContributionStatus,
    Loan, LoanStatus,
    Meeting, MeetingAttendance
)
from apps.chamas.services import ChamaHealthService
from apps.chamas.tasks import update_chama_health_scores


@pytest.fixture
def test_user(db):
    return User.objects.create(
        email="chama_tester@saccobridge.org",
        phone_number="+254712345678",
        first_name="Willy",
        last_name="Gitau",
        is_active=True
    )


@pytest.fixture
def active_chama(db, test_user):
    chama = Chama.objects.create(
        name="Apex Pioneer Chama",
        slug="apex-pioneer-chama",
        status=ChamaStatus.ACTIVE,
        invite_code="APEX001",
        contribution_amount=Decimal("1000.00"),
    )
    ChamaMember.objects.create(
        chama=chama,
        user=test_user,
        role=MemberRole.CHAIRPERSON,
        is_active=True
    )
    return chama


@pytest.mark.django_db(transaction=True)
class TestChamaHealthScoring:

    def test_empty_chama_neutral_defaults(self, active_chama):
        """
        Tests that a brand new chama with 1 active member but no transactions receives
        mathematically exact neutral default scores and proper KDPA reason codes.
        Weights: Contribution(0.30)*50 + Loan(0.25)*100 + Attendance(0.20)*50 + Savings(0.15)*0 + Retention(0.10)*100
        Expected: 15.0 + 25.0 + 10.0 + 0.0 + 10.0 = 60.0 (Grade C)
        """
        result = ChamaHealthService.calculate_health_score(active_chama)

        assert result['score'] == Decimal('60.0')
        assert result['grade'] == 'C'

        breakdown = result['breakdown']
        assert breakdown['contribution_rate']['score'] == '50.0'
        assert breakdown['contribution_rate']['reason_code'] == 'CONTRIBUTION_INSUFFICIENT_HISTORY'
        assert breakdown['loan_performance']['score'] == '100.0'
        assert breakdown['loan_performance']['reason_code'] == 'LOAN_NO_ACTIVE_DEBT'
        assert breakdown['meeting_attendance']['score'] == '50.0'
        assert breakdown['meeting_attendance']['reason_code'] == 'ATTENDANCE_NO_MEETINGS_CONVENED'
        assert breakdown['savings_growth']['score'] == '0.0'
        assert breakdown['savings_growth']['reason_code'] == 'SAVINGS_ZERO_ACTIVITY'
        assert breakdown['member_retention']['score'] == '100.0'
        assert breakdown['member_retention']['reason_code'] == 'RETENTION_STABLE_MEMBERSHIP'

    def test_perfect_health_chama(self, active_chama, test_user):
        """
        Tests that a chama with 100% on-time contributions, perfect loan repayments,
        100% meeting attendance, >10% savings growth, and 100% member retention
        achieves an A+ score of 100.0.
        """
        member = ChamaMember.objects.get(chama=active_chama, user=test_user)
        now = timezone.now()

        # 1. On-time contributions
        for i in range(5):
            p_start = now - timezone.timedelta(days=i * 5)
            Contribution.objects.create(
                chama=active_chama,
                member=member,
                amount=Decimal('1000.00'),
                expected_amount=Decimal('1000.00'),
                status=ContributionStatus.PAID,
                period_start=p_start,
                period_end=p_start + timezone.timedelta(days=4)
            )

        # 2. Perfect loan performance
        Loan.objects.create(
            chama=active_chama,
            borrower=member,
            principal=Decimal('5000.00'),
            interest_rate=Decimal('10.00'),
            duration_months=3,
            status=LoanStatus.FULLY_REPAID,
            due_date=(now - timezone.timedelta(days=10)).date()
        )

        # 3. 100% Meeting attendance
        meeting = Meeting.objects.create(
            chama=active_chama,
            date=(now - timezone.timedelta(days=10)).date(),
            start_time=now.time(),
            title="Monthly Governance Meeting"
        )
        MeetingAttendance.objects.create(
            meeting=meeting,
            member=member,
            attended=True
        )

        # 4. Savings growth: This month 10,000 vs Last month 5,000 (+100% >= 10%)
        last_m_start = (now.replace(day=1) - timezone.timedelta(days=5)).replace(day=1)
        Contribution.objects.create(
            chama=active_chama,
            member=member,
            amount=Decimal('5000.00'),
            expected_amount=Decimal('5000.00'),
            status=ContributionStatus.PAID,
            period_start=last_m_start,
            period_end=last_m_start + timezone.timedelta(days=7)
        )
        this_m_start = now.replace(day=1)
        Contribution.objects.create(
            chama=active_chama,
            member=member,
            amount=Decimal('10000.00'),
            expected_amount=Decimal('10000.00'),
            status=ContributionStatus.PAID,
            period_start=this_m_start,
            period_end=this_m_start + timezone.timedelta(days=7)
        )

        result = ChamaHealthService.calculate_health_score(active_chama)

        assert result['score'] == Decimal('100.0')
        assert result['grade'] == 'A+'
        assert result['breakdown']['contribution_rate']['reason_code'] == 'CONTRIBUTION_ON_TIME_OPTIMAL'
        assert result['breakdown']['loan_performance']['reason_code'] == 'LOAN_PORTFOLIO_PERFECT_REPAYMENT'
        assert result['breakdown']['meeting_attendance']['reason_code'] == 'ATTENDANCE_EXEMPLARY_ENGAGEMENT'
        assert result['breakdown']['savings_growth']['reason_code'] == 'SAVINGS_EXPANSION_EXCELLENT'

    def test_distressed_chama_with_defaults(self, active_chama, test_user):
        """
        Tests that defaulted loans and late/missed contributions correctly degrade
        the score to a failing/warning grade (D or F).
        """
        member = ChamaMember.objects.get(chama=active_chama, user=test_user)
        now = timezone.now()

        # Missed and late contributions
        p1 = now - timezone.timedelta(days=10)
        Contribution.objects.create(
            chama=active_chama,
            member=member,
            amount=Decimal('0.00'),
            expected_amount=Decimal('1000.00'),
            status=ContributionStatus.MISSED,
            period_start=p1,
            period_end=p1 + timezone.timedelta(days=7)
        )
        p2 = now - timezone.timedelta(days=15)
        Contribution.objects.create(
            chama=active_chama,
            member=member,
            amount=Decimal('1000.00'),
            expected_amount=Decimal('1000.00'),
            status=ContributionStatus.LATE,
            period_start=p2,
            period_end=p2 + timezone.timedelta(days=7)
        )

        # Defaulted loans
        Loan.objects.create(
            chama=active_chama,
            borrower=member,
            principal=Decimal('10000.00'),
            interest_rate=Decimal('12.00'),
            duration_months=6,
            status=LoanStatus.DEFAULTED,
            due_date=(now - timezone.timedelta(days=35)).date()
        )

        # 0% meeting attendance
        meeting = Meeting.objects.create(
            chama=active_chama,
            date=(now - timezone.timedelta(days=20)).date(),
            start_time=now.time(),
            title="Emergency Review"
        )
        MeetingAttendance.objects.create(
            meeting=meeting,
            member=member,
            attended=False
        )

        result = ChamaHealthService.calculate_health_score(active_chama)

        assert result['score'] < Decimal('40.0')
        assert result['grade'] == 'F'
        assert result['breakdown']['loan_performance']['reason_code'] == 'LOAN_DEFAULT_IMPAIRMENT'
        assert result['breakdown']['loan_performance']['score'] == '0.0'
        assert result['breakdown']['meeting_attendance']['reason_code'] == 'ATTENDANCE_POOR_ENGAGEMENT'

    def test_atomic_persistence_and_database_isolation(self, active_chama):
        """
        Verifies that update_chama_health() performs an atomic update with row locking
        and correctly persists score, grade, breakdown, and timestamp to the DB.
        """
        assert active_chama.health_score == Decimal('0.0')
        assert active_chama.health_score_grade == ''
        assert active_chama.health_score_updated_at is None

        result = ChamaHealthService.update_chama_health(active_chama)

        active_chama.refresh_from_db()
        assert active_chama.health_score == Decimal('60.0')
        assert active_chama.health_score_grade == 'C'
        assert active_chama.health_score_updated_at is not None
        assert 'contribution_rate' in active_chama.health_score_breakdown
        assert active_chama.health_score_breakdown['contribution_rate']['reason_code'] == 'CONTRIBUTION_INSUFFICIENT_HISTORY'

    def test_celery_task_batch_execution_with_failure_isolation(self, db, test_user):
        """
        Verifies that update_chama_health_scores Celery task processes all active chamas,
        isolates individual exceptions without aborting, and reports accurate batch statistics.
        """
        chama1 = Chama.objects.create(name="Chama 1", slug="chama-1", status=ChamaStatus.ACTIVE, invite_code="C1", contribution_amount=Decimal('1000.00'))
        ChamaMember.objects.create(chama=chama1, user=test_user, role=MemberRole.MEMBER, is_active=True)

        chama2 = Chama.objects.create(name="Chama 2", slug="chama-2", status=ChamaStatus.ACTIVE, invite_code="C2", contribution_amount=Decimal('1000.00'))
        ChamaMember.objects.create(chama=chama2, user=test_user, role=MemberRole.MEMBER, is_active=True)

        chama3 = Chama.objects.create(name="Chama 3", slug="chama-3", status=ChamaStatus.ACTIVE, invite_code="C3", contribution_amount=Decimal('1000.00'))
        ChamaMember.objects.create(chama=chama3, user=test_user, role=MemberRole.MEMBER, is_active=True)

        # Inactive chama should be ignored by batch
        Chama.objects.create(name="Inactive Chama", slug="chama-inactive", status=ChamaStatus.SUSPENDED, invite_code="C4", contribution_amount=Decimal('1000.00'))

        original_update = ChamaHealthService.update_chama_health

        def mock_update(chama):
            if chama.id == chama2.id:
                raise ValueError("Simulated database lock error for Chama 2")
            return original_update(chama)

        with patch.object(ChamaHealthService, 'update_chama_health', side_effect=mock_update):
            task_result = update_chama_health_scores()

        assert task_result['total_eligible'] == 3
        assert task_result['updated'] == 2
        assert task_result['failed'] == 1

        chama1.refresh_from_db()
        chama3.refresh_from_db()
        assert chama1.health_score == Decimal('60.0')
        assert chama3.health_score == Decimal('60.0')
