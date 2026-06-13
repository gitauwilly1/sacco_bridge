import logging
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.exceptions import PermissionDeniedError
from apps.core.pagination import SmallPagination
from apps.core.mixins import SoftDeleteMixin
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, LedgerEntry,
    SettlementReversal, SettlementState, DisputeResolutionType
)
from apps.transactions.serializers import (
    SettlementIntentSerializer, SettlementIntentCreateSerializer,
    SettlementEventSerializer, LedgerEntrySerializer,
    SettlementReversalSerializer, DisputeResolutionSerializer,
)
from apps.transactions.services import SettlementService
from apps.users.permissions import IsPlatformStaff

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=['Settlements'], summary='List my settlements'),
    retrieve=extend_schema(tags=['Settlements'], summary='Get settlement details'),
)
class SettlementViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = SettlementIntentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination
    search_fields = ['buyer_sacco_name', 'seller_sacco_name', 'uuid']
    ordering_fields = ['created_at', 'amount', 'state', 'finalized_at']


    def get_queryset(self):
        user = self.request.user
        from django.db import models
        return SettlementIntent.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user),
            is_deleted=False
        ).select_related('buyer', 'seller').prefetch_related('events')

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        settlement = self.get_object()
        events = settlement.events.all().order_by('timestamp')
        serializer = SettlementEventSerializer(events, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        settlement = self.get_object()
        serializer = self.get_serializer(settlement)
        return Response({
            'success': True,
            'data': {'timeline': serializer.data.get('timeline', [])}
        })

    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        settlement = self.get_object()

        try:
            ledger = settlement.ledger_entry
            serializer = LedgerEntrySerializer(ledger)
            return Response({'success': True, 'data': serializer.data})
        except LedgerEntry.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('Ledger entry not available. Settlement may not be finalized.')
                }
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    list=extend_schema(tags=['Settlements'], summary='List disputed settlements'),
    retrieve=extend_schema(tags=['Settlements'], summary='Get dispute details'),
)
class DisputeViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = SettlementIntentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]
    pagination_class = SmallPagination
    search_fields = ['buyer_sacco_name', 'seller_sacco_name', 'uuid']
    ordering_fields = ['created_at', 'amount', 'dispute_opened_at']

    def get_queryset(self):
        return SettlementIntent.objects.filter(
            state=SettlementState.DISPUTED_MANUAL,
            is_deleted=False
        ).select_related('buyer', 'seller')

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        settlement = self.get_object()

        if settlement.state != SettlementState.DISPUTED_MANUAL:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_state',
                    'message': _('Only disputed settlements can be resolved.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = DisputeResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolution_type = serializer.validated_data['resolution_type']
        notes = serializer.validated_data.get('notes', '')

        if resolution_type == 'MANUAL_CREDIT_CONFIRMED':
            ref = serializer.validated_data.get('sacco_confirmation_ref', '')
            officer = serializer.validated_data.get('sacco_officer_name', '')

            settlement.dispute_resolution_type = DisputeResolutionType.MANUAL_CREDIT_CONFIRMED
            settlement.dispute_resolved_by = request.user
            settlement.dispute_resolved_at = timezone.now()
            settlement.internal_notes = (
                f"Confirmed by {officer}. Ref: {ref}. Notes: {notes}"
            )
            settlement.save()

            settlement.seller_credit_ref = ref
            settlement.save(update_fields=['seller_credit_ref'])

            SettlementService.finalize_settlement(settlement)

        elif resolution_type == 'BUYER_REVERSAL_INITIATED':
            settlement.dispute_resolution_type = DisputeResolutionType.BUYER_REVERSAL_INITIATED
            settlement.dispute_resolved_by = request.user
            settlement.dispute_resolved_at = timezone.now()
            settlement.internal_notes = notes
            settlement.save()

            SettlementService.initiate_compensation(settlement)

        elif resolution_type == 'ESCALATED_TO_TRUSTEE':
            SettlementService.escalate_to_trustee(settlement, request.user, notes)

        elif resolution_type == 'FORCE_MARKED_SETTLED':
            approval = serializer.validated_data.get('executive_approval_ref', '')
            if not approval:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'missing_approval',
                        'message': _('Executive approval reference required.')
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            settlement.dispute_resolution_type = DisputeResolutionType.FORCE_MARKED_SETTLED
            settlement.dispute_resolved_by = request.user
            settlement.dispute_resolved_at = timezone.now()
            settlement.internal_notes = f"Force settled. Approval: {approval}. Notes: {notes}"
            settlement.save()

            SettlementService.finalize_settlement(settlement)

        return Response({
            'success': True,
            'data': SettlementIntentSerializer(settlement).data,
            'message': _('Dispute resolved.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Settlements'], summary='List ledger entries'),
    retrieve=extend_schema(tags=['Settlements'], summary='Get ledger entry'),
)
class LedgerViewSet(SoftDeleteMixin, viewsets.ReadOnlyModelViewSet):

    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination
    search_fields = ['sacco_id']
    ordering_fields = ['recorded_at', 'total_amount', 'share_quantity']

    def get_queryset(self):
        user = self.request.user
        from django.db import models
        return LedgerEntry.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).order_by('-recorded_at')