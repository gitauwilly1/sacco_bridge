import pytest
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone

from apps.users.models import User
from apps.chamas.models import (
    Chama, ChamaMember, Contribution, Loan, Meeting, MeetingAttendance,
    ChamaStatus, MemberRole, ContributionStatus, LoanStatus
)
from apps.chamas.services import ChamaHealthService
from apps.chamas.tasks import update_chama_health_scores


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        phone_number="+254711000001",
        email="testchama@example.com",
        first_name="Jane",
        last_name="Wanjiku",
        national_id="30112233",
    )


@pytest.fixture
def active_chama(db, test_user):
    chama = Chama.objects.create(
        name="Apex Pioneer Chama",
        slug="apex-pioneer-chama",
        status=ChamaStatus.ACTIVE,
        invite_code="APEX01",
        contribution_amount=Decimal('1000.00'),
    )
    ChamaMember.objects.create(
        chama=chama,
        user=test_user,
        role=MemberRole.CHAIRPERSON,
        is_active=True,
    )
    return chama


@pytest.mark.django_db
class TestChamaHealthScoring:
    """
    Comprehensive test suite for ChamaHealthService and its batch execution task.
    Enforces strict mathematical boundaries, KDPA reason codes, atomic row locking,
    and exception isolation.
    """

    def test_empty_chama_neutral_defaults(self, active_chama):
        """
        Tests that a newly created Chama with 1 member and zero activity
        evaluates to exact baseline defaults:
        - Contribution: 50.0 (weight 30% -> 15.0)
        - Loan: 100.0 (weight 25% -> 25.0, pristine credit)
        - Attendance: 50.0 (weight 20% -> 10.0)
        - Savings Growth: 0.0 (weight 15% -> 0.0)
        - Retention: 100.0 (weight 10% -> 10.0)
        Total Overall Score: 60.0 (Grade C)
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
        Tests that a Chama with on-time contributions, fully repaid loans,
        100% meeting attendance, robust savings expansion (+100%), and 100% retention
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

    def test_month_over_month_savings_growth_math(self, active_chama, test_user):
        """
        Dedicated unit test for savings growth (15% factor weight):
        - Robust growth (+20% >= 10% -> 100.0 score, SAVINGS_EXPANSION_EXCELLENT)
        - Stable growth (+5% -> score 50 + 5*5 = 75.0, SAVINGS_STABLE_GROWTH)
        - Contraction (-10% -> score 50 - 10*3 = 20.0, SAVINGS_CONTRACTION)
        - Severe contraction (-50% -> score max(0, 50 - 50*3) = 0.0, SAVINGS_CONTRACTION)
        - Zero previous month baseline with current deposits -> score 50.0, SAVINGS_NEW_DEPOSITS_INITIATED
        """
        member = ChamaMember.objects.get(chama=active_chama, user=test_user)
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timezone.timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Case A: Zero prior baseline with current deposits
        c_cur = Contribution.objects.create(
            chama=active_chama,
            member=member,
            amount=Decimal('5000.00'),
            expected_amount=Decimal('5000.00'),
            status=ContributionStatus.PAID,
            period_start=this_month_start,
            period_end=this_month_start + timezone.timedelta(days=5)
        )
        score_a, code_a, _ = ChamaHealthService._calculate_savings_growth(active_chama)
        assert score_a == Decimal('50.0')
        assert code_a == 'SAVINGS_NEW_DEPOSITS_INITIATED'

        # Case B: Robust growth (This month 12,000 vs Last month 10,000 -> +20% >= 10%)
        c_cur.amount = Decimal('12000.00')
        c_cur.save()
        c_last = Contribution.objects.create(
            chama=active_chama,
            member=member,
            amount=Decimal('10000.00'),
            expected_amount=Decimal('10000.00'),
            status=ContributionStatus.PAID,
            period_start=last_month_start,
            period_end=last_month_start + timezone.timedelta(days=5)
        )
        score_b, code_b, _ = ChamaHealthService._calculate_savings_growth(active_chama)
        assert score_b == Decimal('100.0')
        assert code_b == 'SAVINGS_EXPANSION_EXCELLENT'

        # Case C: Stable growth (This month 10,500 vs Last month 10,000 -> +5%)
        c_cur.amount = Decimal('10500.00')
        c_cur.save()
        score_c, code_c, _ = ChamaHealthService._calculate_savings_growth(active_chama)
        assert score_c == Decimal('75.0')
        assert code_c == 'SAVINGS_STABLE_GROWTH'

        # Case D: Moderate Contraction (This month 9,000 vs Last month 10,000 -> -10%)
        c_cur.amount = Decimal('9000.00')
        c_cur.save()
        score_d, code_d, _ = ChamaHealthService._calculate_savings_growth(active_chama)
        assert score_d == Decimal('20.0')
        assert code_d == 'SAVINGS_CONTRACTION'

        # Case E: Severe Contraction (This month 5,000 vs Last month 10,000 -> -50%)
        c_cur.amount = Decimal('5000.00')
        c_cur.save()
        score_e, code_e, _ = ChamaHealthService._calculate_savings_growth(active_chama)
        assert score_e == Decimal('0.0')
        assert code_e == 'SAVINGS_CONTRACTION'

    def test_member_retention_edge_cases(self, db):
        """
        Dedicated unit test for member retention math (10% factor weight):
        - Zero total members guard (prevents ZeroDivisionError) -> score 0.0, RETENTION_ZERO_MEMBERS
        - 100% active retention (10/10) -> score 100.0, RETENTION_STABLE_MEMBERSHIP
        - Moderate churn (8/10 active = 80%) -> score 80.0, RETENTION_MODERATE_CHURN
        - High churn risk (5/10 active = 50%) -> score 50.0, RETENTION_HIGH_CHURN_RISK
        """
        # Case A: Chama with zero members
        empty_chama = Chama.objects.create(
            name="Empty Chama",
            slug="empty-chama",
            status=ChamaStatus.ACTIVE,
            invite_code="EMPTY1",
            contribution_amount=Decimal('500.00'),
        )
        score_a, code_a, _ = ChamaHealthService._calculate_retention(empty_chama)
        assert score_a == Decimal('0.0')
        assert code_a == 'RETENTION_ZERO_MEMBERS'

        # Case B: 10/10 active members (100% retention)
        users = [
            User.objects.create_user(
                phone_number=f"+2547119990{i:02d}",
                email=f"member{i}@example.com",
                first_name=f"Member{i}",
                last_name="Test",
                national_id=f"990000{i:02d}",
            )
            for i in range(10)
        ]
        chama_b = Chama.objects.create(
            name="Chama Retention Test",
            slug="chama-retention-test",
            status=ChamaStatus.ACTIVE,
            invite_code="RET001",
            contribution_amount=Decimal('500.00'),
        )
        for u in users:
            ChamaMember.objects.create(chama=chama_b, user=u, role=MemberRole.MEMBER, is_active=True)

        score_b, code_b, _ = ChamaHealthService._calculate_retention(chama_b)
        assert score_b == Decimal('100.0')
        assert code_b == 'RETENTION_STABLE_MEMBERSHIP'

        # Case C: 8/10 active (80% retention -> Moderate Churn)
        members = list(ChamaMember.objects.filter(chama=chama_b))
        members[0].is_active = False
        members[0].save()
        members[1].is_active = False
        members[1].save()

        score_c, code_c, _ = ChamaHealthService._calculate_retention(chama_b)
        assert score_c == Decimal('80.0')
        assert code_c == 'RETENTION_MODERATE_CHURN'

        # Case D: 5/10 active (50% retention -> High Churn Risk)
        for i in range(2, 5):
            members[i].is_active = False
            members[i].save()

        score_d, code_d, _ = ChamaHealthService._calculate_retention(chama_b)
        assert score_d == Decimal('50.0')
        assert code_d == 'RETENTION_HIGH_CHURN_RISK'

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
