import uuid
from datetime import date, timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):

    class Meta:
        model = 'users.User'

    email = factory.Sequence(lambda n: f'user{n}@test.com')
    phone_number = factory.Sequence(lambda n: f'0712{n:06d}'[:12])
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email_verified = True
    phone_verified = True
    is_active = True
    password = factory.PostGenerationMethodCall('set_password', 'TestPass@2026')

    @factory.post_generation
    def roles(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for role in extracted:
                from apps.users.models import UserRole
                UserRole.objects.create(user=self, role=role)


class ChamaFactory(DjangoModelFactory):

    class Meta:
        model = 'chamas.Chama'

    name = factory.Sequence(lambda n: f'Test Chama {n}')
    chama_type = 'WELFARE_GROUP'
    contribution_amount = Decimal('1000.00')
    contribution_frequency = 'WEEKLY'
    max_members = 50
    loan_interest_rate = Decimal('10.00')
    max_loan_multiple = Decimal('3.00')
    max_loan_duration_months = 12
    payout_cycle_months = 12
    payout_method = 'EQUAL'
    late_fee_amount = Decimal('100.00')
    grace_period_days = 3
    status = 'ACTIVE'


class ChamaMemberFactory(DjangoModelFactory):
    """Factory for ChamaMember model."""

    class Meta:
        model = 'chamas.ChamaMember'

    chama = factory.SubFactory(ChamaFactory)
    user = factory.SubFactory(UserFactory)
    role = 'MEMBER'
    is_active = True


class ContributionFactory(DjangoModelFactory):

    class Meta:
        model = 'chamas.Contribution'

    chama = factory.SubFactory(ChamaFactory)
    member = factory.SubFactory(ChamaMemberFactory)
    amount = Decimal('1000.00')
    expected_amount = Decimal('1000.00')
    status = 'PAID'
    payment_method = 'MPESA'
    period_start = factory.LazyFunction(lambda: date.today() - timedelta(days=7))
    period_end = factory.LazyFunction(lambda: date.today())
    paid_at = factory.LazyFunction(timezone.now)


class LoanFactory(DjangoModelFactory):

    class Meta:
        model = 'chamas.Loan'

    chama = factory.SubFactory(ChamaFactory)
    borrower = factory.SubFactory(ChamaMemberFactory)
    principal = Decimal('10000.00')
    interest_rate = Decimal('10.00')
    duration_months = 6
    total_interest = Decimal('6000.00')
    total_repayable = Decimal('16000.00')
    monthly_installment = Decimal('2666.67')
    outstanding_balance = Decimal('16000.00')
    status = 'APPROVED'


class SACCOFactory(DjangoModelFactory):
    """Factory for SACCO model."""

    class Meta:
        model = 'investments.SACCO'

    name = factory.Sequence(lambda n: f'Test SACCO {n}')
    registration_number = factory.Sequence(lambda n: f'SACCO/REG/{n:03d}')
    sasra_tier = 'TIER_1'
    status = 'ACTIVE'
    total_assets = Decimal('1000000000.00')
    total_members = 1000
    dividend_rate = Decimal('12.00')
    dividend_year = 2025


class SettlementIntentFactory(DjangoModelFactory):

    class Meta:
        model = 'transactions.SettlementIntent'

    uuid = factory.LazyFunction(uuid.uuid4)
    idempotency_key = factory.LazyFunction(lambda: uuid.uuid4().hex)
    state = 'MATCH_PROPOSED'
    buyer = factory.SubFactory(UserFactory)
    seller = factory.SubFactory(UserFactory)
    buyer_sacco_id = 1
    buyer_sacco_name = 'Test SACCO'
    seller_sacco_id = 1
    seller_sacco_name = 'Test SACCO'
    amount = Decimal('50000.00')
    share_quantity = Decimal('200.0000')
    price_per_share = Decimal('250.00')
    platform_fee = Decimal('500.00')
    net_seller_amount = Decimal('49500.00')
    ttl_seconds = 300