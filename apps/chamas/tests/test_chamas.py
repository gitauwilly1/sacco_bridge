from decimal import Decimal
import uuid
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.tests.factories import (
    ChamaFactory,
    ChamaMemberFactory,
    LoanFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestChamaCRUD:

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(email='chamatest@test.com')
        self.client.force_authenticate(user=self.user)
        self.chama_url = reverse('chama-list')

    def test_create_chama(self):
        data = {
            'name': 'Test Chama',
            'chama_type': 'WELFARE_GROUP',
            'contribution_amount': '1000.00',
            'contribution_frequency': 'WEEKLY',
            'max_members': 30,
            'loan_interest_rate': '10.00',
            'max_loan_multiple': '3.00',
            'max_loan_duration_months': 12,
            'payout_cycle_months': 12,
            'payout_method': 'EQUAL',
            'late_fee_amount': '100.00',
            'grace_period_days': 3,
        }
        response = self.client.post(
            self.chama_url, data, format='json',
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_201_CREATED
        # DRF ModelViewSet returns serializer data directly
        assert response.data['name'] == 'Test Chama'

    def test_list_user_chamas(self):
        chama = ChamaFactory()
        ChamaMemberFactory(chama=chama, user=self.user, role='CHAIRPERSON')

        response = self.client.get(self.chama_url)
        assert response.status_code == status.HTTP_200_OK

    def test_get_chama_detail(self):
        chama = ChamaFactory()
        ChamaMemberFactory(chama=chama, user=self.user)

        url = reverse('chama-detail', kwargs={'pk': chama.id})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # DRF returns serializer data directly for retrieve
        assert response.data['name'] == chama.name


@pytest.mark.django_db
class TestContributions:

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.chama = ChamaFactory()
        self.member = ChamaMemberFactory(
            chama=self.chama,
            user=self.user,
            role='TREASURER'
        )

    def test_record_contribution(self):
        url = reverse('chama-contributions', kwargs={'chama_pk': self.chama.id})
        data = {
            'chama': str(self.chama.id),
            'member': str(self.member.id),
            'amount': '1000.00',
            'payment_method': 'MPESA',
            'payment_reference': 'TXN-TEST',
            'period_start': '2026-06-01',
            'period_end': '2026-06-07',
            'notes': 'Test',
        }
        response = self.client.post(
            url, data, format='json',
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_bulk_contribution(self):
        member2 = ChamaMemberFactory(
            chama=self.chama,
            user=UserFactory(email='member2@test.com')
        )

        url = reverse('chama-contributions-bulk', kwargs={'chama_pk': self.chama.id})
        data = {
            'period_start': '2026-06-01',
            'period_end': '2026-06-07',
            'contributions': [
                {
                    'member_id': str(self.member.id),
                    'amount': 1000.00,
                    'payment_method': 'CASH',
                },
                {
                    'member_id': str(member2.id),
                    'amount': 1000.00,
                    'payment_method': 'MPESA',
                    'payment_reference': 'BULK-002',
                },
            ]
        }
        response = self.client.post(
            url, data, format='json',
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['success_count'] == 2


@pytest.mark.django_db
class TestLoans:

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.chama = ChamaFactory()
        # User is the CHAIRPERSON of this chama (membership role)
        self.member = ChamaMemberFactory(
            chama=self.chama,
            user=self.user,
            role='CHAIRPERSON',
            total_contributions=Decimal('30000.00'),
        )

    def test_apply_loan(self):
        url = reverse('chama-loans', kwargs={'chama_pk': self.chama.id})
        data = {
            'chama': str(self.chama.id),
            'borrower': str(self.member.id),
            'principal': '5000.00',
            'duration_months': 3,
            'purpose': 'Test loan',
        }
        response = self.client.post(
            url, data, format='json',
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_approve_loan(self):
        # Create loan with the setup member as borrower in the setup chama
        loan = LoanFactory(
            chama=self.chama,
            borrower=self.member,
            status='PENDING'
        )
        url = reverse('chama-loan-approve', kwargs={
            'chama_pk': self.chama.id,
            'pk': loan.id,
        })
        response = self.client.post(
            url,
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_200_OK

    def test_disburse_loan(self):
        loan = LoanFactory(
            chama=self.chama,
            borrower=self.member,
            status='APPROVED'
        )
        url = reverse('chama-loan-disburse', kwargs={
            'chama_pk': self.chama.id,
            'pk': loan.id,
        })
        response = self.client.post(
            url,
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_200_OK

    def test_repay_loan(self):
        loan = LoanFactory(
            chama=self.chama,
            borrower=self.member,
            status='DISBURSED',
            outstanding_balance=Decimal('16000.00'),
        )
        url = reverse('chama-loan-repay', kwargs={
            'chama_pk': self.chama.id,
            'pk': loan.id,
        })
        data = {
            'amount': '2000.00',
            'payment_method': 'MPESA',
            'payment_reference': 'REP-TEST',
        }
        response = self.client.post(
            url, data, format='json',
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPermissions:

    def setup_method(self):
        self.client = APIClient()

    def test_unverified_user_blocked_from_investments(self):
        user = UserFactory(email_verified=False, phone_verified=False)
        self.client.force_authenticate(user=user)

        url = reverse('sacco-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error']['code'] == 'permission_denied'

    def test_verified_user_accesses_investments(self):
        user = UserFactory(email_verified=True, phone_verified=True)
        self.client.force_authenticate(user=user)

        url = reverse('sacco-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_non_member_blocked_from_bulk_contributions(self):
        user = UserFactory()
        self.client.force_authenticate(user=user)
        chama = ChamaFactory()
        # User is NOT added as a member of this chama

        url = reverse('chama-contributions-bulk', kwargs={'chama_pk': chama.id})
        data = {
            'period_start': '2026-06-01',
            'period_end': '2026-06-07',
            'contributions': [
                {'member_id': '00000000-0000-0000-0000-000000000000', 'amount': 100}
            ]
        }
        response = self.client.post(
            url, data, format='json',
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_platform_staff_bypass_verification(self):
        from apps.users.models import Role as GlobalRole
        from apps.users.models import UserRole
        
        user = UserFactory(email_verified=False, phone_verified=False)
        UserRole.objects.create(user=user, role=GlobalRole.PLATFORM_ADMIN)
        self.client.force_authenticate(user=user)

        url = reverse('sacco-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK