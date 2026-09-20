import uuid
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.tests.factories import UserFactory
from apps.support.models import (
    SupportMessage,
    SupportTicket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


@pytest.mark.django_db
class TestSupportSubsystem:

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.staff_user = UserFactory(roles=['PLATFORM_ADMIN'])
        self.staff_user.is_staff = True
        self.staff_user.save()

    def test_user_can_create_ticket(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'title': 'Payment Issue on STK Push',
            'description': 'I attempted an M-Pesa deposit of KSh 1000 but the receipt did not credit.',
            'category': TicketCategory.PAYMENT,
        }
        url = reverse('my-ticket-create')
        response = self.client.post(url, payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        ticket_id = response.data['data']['id']

        ticket = SupportTicket.objects.get(id=ticket_id)
        assert ticket.user == self.user
        assert ticket.title == 'Payment Issue on STK Push'
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.MEDIUM

    def test_user_can_list_own_tickets(self):
        self.client.force_authenticate(user=self.user)
        t1 = SupportTicket.objects.create(
            user=self.user,
            title='Ticket 1',
            description='Issue 1',
            status=TicketStatus.OPEN
        )
        t2 = SupportTicket.objects.create(
            user=self.user,
            title='Ticket 2',
            description='Issue 2',
            status=TicketStatus.RESOLVED
        )
        # Other user's ticket (should not appear)
        SupportTicket.objects.create(
            user=self.other_user,
            title='Other Ticket',
            description='Other Issue'
        )

        url = reverse('my-tickets')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        titles = [t['title'] for t in response.data['data']]
        assert 'Ticket 1' in titles
        assert 'Ticket 2' in titles
        assert 'Other Ticket' not in titles

    def test_user_can_add_message_to_ticket(self):
        self.client.force_authenticate(user=self.user)
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='Login Problem',
            description='Cannot reset password.'
        )

        url = reverse('my-ticket-message', kwargs={'pk': ticket.id})
        response = self.client.post(url, {'message': 'Here is more info: error code 403.'}, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True

        message = SupportMessage.objects.filter(ticket=ticket).first()
        assert message is not None
        assert message.message == 'Here is more info: error code 403.'
        assert message.author == self.user

    def test_other_user_cannot_access_private_ticket(self):
        self.client.force_authenticate(user=self.other_user)
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='Private Financial Ticket',
            description='Confidential account inquiry.'
        )

        url = reverse('my-ticket-detail', kwargs={'pk': ticket.id})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_admin_can_triage_and_resolve_ticket(self):
        self.client.force_authenticate(user=self.staff_user)
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='Escrow Dispute Query',
            description='Need manual escrow release review.',
            status=TicketStatus.OPEN
        )

        # 1. Staff lists all tickets
        list_url = reverse('admin-tickets')
        response = self.client.get(list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

        # 2. Staff assigns ticket
        detail_url = reverse('admin-ticket-detail', kwargs={'pk': ticket.id})
        assign_payload = {
            'action': 'assign',
            'user_id': str(self.staff_user.id),
        }
        assign_res = self.client.post(detail_url, assign_payload, format='json')
        assert assign_res.status_code == status.HTTP_200_OK

        # 3. Staff updates ticket status
        update_payload = {
            'action': 'update_status',
            'status': TicketStatus.RESOLVED,
        }
        update_res = self.client.post(detail_url, update_payload, format='json')
        assert update_res.status_code == status.HTTP_200_OK

        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.RESOLVED
        assert ticket.assigned_to == self.staff_user
        assert ticket.resolved_at is not None
