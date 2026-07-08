import logging

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import SmallPagination
from apps.support.models import SupportMessage, SupportTicket, TicketPriority, TicketStatus
from apps.support.serializers import (
    SupportMessageSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
    TicketActionSerializer,
)
from apps.users.permissions import IsPlatformStaff

logger = logging.getLogger(__name__)


class MyTicketListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tickets = SupportTicket.objects.filter(user=request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            tickets = tickets.filter(status=status_filter)
        tickets = tickets.order_by('-updated_at')
        page = SmallPagination().paginate_queryset(tickets, request)
        serializer = SupportTicketListSerializer(page, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': tickets.count(),
        })


class MyTicketCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SupportTicketCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        return Response({
            'success': True,
            'data': SupportTicketDetailSerializer(ticket).data,
            'message': _('Ticket created.'),
        }, status=status.HTTP_201_CREATED)


class MyTicketDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(id=pk, user=request.user)
        except SupportTicket.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Ticket not found.')}
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = SupportTicketDetailSerializer(ticket)
        return Response({'success': True, 'data': serializer.data})


class MyTicketMessageCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(id=pk, user=request.user)
        except SupportTicket.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Ticket not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        message = request.data.get('message', '')
        if not message:
            return Response({
                'success': False,
                'error': {'code': 'missing_message', 'message': _('Message is required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        msg = SupportMessage.objects.create(
            ticket=ticket,
            author=request.user,
            message=message,
        )

        if ticket.status == 'WAITING_ON_USER':
            ticket.status = 'OPEN'
            ticket.save(update_fields=['status'])

        return Response({
            'success': True,
            'data': SupportMessageSerializer(msg).data,
        }, status=status.HTTP_201_CREATED)


class AdminTicketListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get(self, request):
        tickets = SupportTicket.objects.all()
        status_filter = request.query_params.get('status')
        priority_filter = request.query_params.get('priority')
        if status_filter:
            tickets = tickets.filter(status=status_filter)
        if priority_filter:
            tickets = tickets.filter(priority=priority_filter)
        tickets = tickets.order_by('-priority', '-updated_at')
        page = SmallPagination().paginate_queryset(tickets, request)
        serializer = SupportTicketListSerializer(page, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': tickets.count(),
        })


class AdminTicketDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(id=pk)
        except SupportTicket.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Ticket not found.')}
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = SupportTicketDetailSerializer(ticket)
        return Response({'success': True, 'data': serializer.data})

    def post(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(id=pk)
        except SupportTicket.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Ticket not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']

        if action == 'assign':
            from apps.users.models import User
            try:
                agent = User.objects.get(id=serializer.validated_data['user_id'])
            except User.DoesNotExist:
                return Response({
                    'success': False, 'error': {'code': 'not_found', 'message': _('User not found.')}
                }, status=status.HTTP_400_BAD_REQUEST)
            ticket.assigned_to = agent
            ticket.save(update_fields=['assigned_to'])
            msg = SupportMessage.objects.create(
                ticket=ticket, author=request.user, message=f"Assigned to {agent.get_full_name()}", is_internal=True
            )

        elif action == 'update_status':
            new_status = serializer.validated_data['status']
            if new_status == 'RESOLVED':
                ticket.resolved_at = timezone.now()
            elif new_status == 'CLOSED':
                ticket.closed_at = timezone.now()
            ticket.status = new_status
            ticket.save(update_fields=['status', 'resolved_at', 'closed_at'])
            msg = SupportMessage.objects.create(
                ticket=ticket, author=request.user, message=f"Status changed to {dict(TicketStatus.choices)[new_status]}", is_internal=True
            )

        elif action == 'add_note':
            note = serializer.validated_data.get('note', '')
            if note:
                msg = SupportMessage.objects.create(
                    ticket=ticket, author=request.user, message=note, is_internal=True
                )

        return Response({
            'success': True,
            'data': SupportTicketDetailSerializer(ticket).data,
            'message': _('Action applied.'),
        })
