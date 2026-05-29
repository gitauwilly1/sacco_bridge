import logging
from django.db import transaction as db_transaction
from django.utils import timezone
from django.db import models as django_models
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.exceptions import (
    SettlementError, PermissionDeniedError, DuplicateRequestError
)
from apps.core.pagination import SmallPagination
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, DisputeRecord,
    DisputeEvent, LedgerEntry, SettlementState,
    DisputeResolutionType
)
from apps.transactions.serializers import (
    SettlementIntentSerializer, SettlementTimelineSerializer,
    DisputeRecordSerializer, DisputeResolutionSerializer,
    LedgerEntrySerializer,
)
from apps.users.permissions import IsPlatformStaff, IsVerifiedUser

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=['Settlements'], summary='List my settlements'),
    retrieve=extend_schema(tags=['Settlements'], summary='Get settlement details'),
)
class SettlementViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = SettlementIntentSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    pagination_class = SmallPagination

    def get_queryset(self):
        user = self.request.user
        if IsPlatformStaff().has_permission(self.request, None):
            return DisputeRecord.objects.all().order_by('-created_at')
        return DisputeRecord.objects.filter(
            django_models.Q(settlement_intent__buyer=user) |
            django_models.Q(settlement_intent__seller=user)
        ).order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        intent = self.get_object()
        timeline = SettlementTimelineSerializer.build_timeline(intent)
        return Response({
            'success': True,
            'data': timeline,
        })

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        intent = self.get_object()
        events = intent.events.order_by('timestamp')
        from apps.transactions.serializers import SettlementEventSerializer
        serializer = SettlementEventSerializer(events, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        intent = self.get_object()

        if intent.state != SettlementState.SETTLED:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_settled',
                    'message': _('Ledger entries are only available for settled transactions.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        entries = intent.ledger_entries.all()
        serializer = LedgerEntrySerializer(entries, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })


@extend_schema_view(
    list=extend_schema(tags=['Disputes'], summary='List disputes'),
    retrieve=extend_schema(tags=['Disputes'], summary='Get dispute details'),
)
class DisputeViewSet(viewsets.ModelViewSet):

    serializer_class = DisputeRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        user = self.request.user

        if IsPlatformStaff().has_permission(self.request, None):
            return DisputeRecord.objects.all().order_by('-created_at')

        return DisputeRecord.objects.filter(
            models.Q(settlement_intent__buyer=user) |
            models.Q(settlement_intent__seller=user)
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        if not IsPlatformStaff().has_permission(request, None):
            raise PermissionDeniedError()

        dispute = self.get_object()

        if dispute.status in ['RESOLVED', 'CLOSED']:
            return Response({
                'success': False,
                'error': {
                    'code': 'already_resolved',
                    'message': _('This dispute has already been resolved.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = DisputeResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolution_type = serializer.validated_data['resolution_type']
        notes = serializer.validated_data['resolution_notes']
        sacco_ref = serializer.validated_data.get('sacco_confirmation_ref', '')
        evidence = serializer.validated_data.get('external_evidence', {})

        dispute.resolution_type = resolution_type
        dispute.resolution_notes = notes
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.status = 'RESOLVED'
        dispute.save()

        DisputeEvent.objects.create(
            dispute=dispute,
            action=f'RESOLVED_{resolution_type}',
            description=notes,
            actor=request.user,
            evidence={
                'sacco_confirmation_ref': sacco_ref,
                **evidence,
            }
        )

        intent = dispute.settlement_intent

        if resolution_type == 'MANUAL_CREDIT_CONFIRMED':
            intent.transition_to(SettlementState.SELLER_CREDIT_CONFIRMED)
            intent.transition_to(SettlementState.LEDGER_FINALIZED)
            intent.transition_to(SettlementState.SETTLED)

        elif resolution_type == 'BUYER_REVERSAL_INITIATED':
            intent.transition_to(SettlementState.COMPENSATING)
            intent.reversal_transaction_id = sacco_ref
            intent.save()

        elif resolution_type == 'FORCE_SETTLED':
            intent.transition_to(SettlementState.SETTLED)

        elif resolution_type == 'ESCALATED_TO_TRUSTEE':
            dispute.status = 'AWAITING_TRUSTEE'
            dispute.trustee_case_number = sacco_ref
            dispute.save()

        logger.info(f"Dispute {dispute.dispute_reference} resolved by {request.user.email}")

        return Response({
            'success': True,
            'data': DisputeRecordSerializer(dispute).data,
            'message': _('Dispute resolved.'),
        })

    @action(detail=True, methods=['post'])
    def add_event(self, request, pk=None):
        if not IsPlatformStaff().has_permission(request, None):
            raise PermissionDeniedError()

        dispute = self.get_object()

        event = DisputeEvent.objects.create(
            dispute=dispute,
            action=request.data.get('action', 'NOTE_ADDED'),
            description=request.data.get('description', ''),
            actor=request.user,
            evidence=request.data.get('evidence', {}),
        )

        from apps.transactions.serializers import DisputeEventSerializer
        return Response({
            'success': True,
            'data': DisputeEventSerializer(event).data,
            'message': _('Event added to dispute.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Ledger'], summary='List my ledger entries'),
)
class LedgerViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        return LedgerEntry.objects.filter(
            party=self.request.user
        ).order_by('-created_at')