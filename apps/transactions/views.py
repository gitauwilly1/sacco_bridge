import logging
from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import SoftDeleteMixin
from apps.core.pagination import SmallPagination
from apps.transactions.models import (
    Dispute,
    DisputeResolutionType,
    LedgerEntry,
    SettlementIntent,
    SettlementState,
)
from apps.transactions.serializers import (
    DisputeCreateSerializer,
    DisputeResolutionSerializer,
    DisputeSerializer,
    LedgerEntrySerializer,
    SettlementEventSerializer,
    SettlementIntentCreateSerializer,
    SettlementIntentSerializer,
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

    @action(detail=False, methods=['post'])
    def create_settlement(self, request):
        connection_id = request.data.get('connection_id')
        
        if connection_id:
            existing = SettlementIntent.objects.filter(
                connection_id=connection_id,
                state__in=['MATCH_PROPOSED', 'INTENT_LOCKED', 'BUYER_DEBIT_INITIATED', 
                           'BUYER_DEBIT_CONFIRMED', 'SELLER_CREDIT_INITIATED', 
                           'SELLER_CREDIT_CONFIRMED'],
                is_deleted=False,
            ).exists()
            
            if existing:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'duplicate_settlement',
                        'message': _('An active settlement already exists for this connection.')
                    }
                }, status=status.HTTP_409_CONFLICT)
        
        serializer = SettlementIntentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = serializer.save()
        
        return Response({
            'success': True,
            'data': SettlementIntentSerializer(settlement).data,
            'message': _('Settlement created.'),
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def validate_transaction(self, request):
        amount = request.data.get('amount')
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': {'code': 'invalid_amount', 'message': _('Invalid amount.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        requires_confirmation = amount > Decimal('100000.00')
        
        return Response({
            'success': True,
            'data': {
                'amount': str(amount),
                'requires_confirmation': requires_confirmation,
                'threshold': '100000.00',
                'message': _('Amounts above KSh 100,000 require additional confirmation.') if requires_confirmation else None,
            },
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        settlement = self.get_object()

        if settlement.state != 'REVERSED':
            return Response({
                'success': False,
                'error': {
                    'code': 'cannot_retry',
                    'message': _('Only reversed settlements can be retried.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if not settlement.connection:
            return Response({
                'success': False,
                'error': {
                    'code': 'no_connection',
                    'message': _('No connection found for this settlement.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check no active settlement exists for this connection
        active_exists = SettlementIntent.objects.filter(
            connection=settlement.connection,
            state__in=['MATCH_PROPOSED', 'INTENT_LOCKED', 'BUYER_DEBIT_INITIATED',
                       'BUYER_DEBIT_CONFIRMED', 'SELLER_CREDIT_INITIATED',
                       'SELLER_CREDIT_CONFIRMED', 'DISPUTED_MANUAL'],
            is_deleted=False,
        ).exists()

        if active_exists:
            return Response({
                'success': False,
                'error': {
                    'code': 'active_settlement_exists',
                    'message': _('An active settlement already exists for this connection.')
                }
            }, status=status.HTTP_409_CONFLICT)

        # Create new settlement from original
        new_settlement = SettlementService.create_settlement_intent(
            connection=settlement.connection,
            buyer=settlement.buyer,
            seller=settlement.seller,
            amount=settlement.amount,
            share_quantity=settlement.share_quantity,
            price_per_share=settlement.price_per_share,
            buyer_sacco_id=settlement.buyer_sacco_id,
            buyer_sacco_name=settlement.buyer_sacco_name,
            seller_sacco_id=settlement.seller_sacco_id,
            seller_sacco_name=settlement.seller_sacco_name,
        )

        logger.info(
            f"Settlement retry: {new_settlement.uuid} created from {settlement.uuid}"
        )

        return Response({
            'success': True,
            'data': SettlementIntentSerializer(new_settlement).data,
            'message': _('Retry settlement created.'),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        settlement = self.get_object()

        # Check user is involved
        if request.user != settlement.buyer and request.user != settlement.seller:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_involved',
                    'message': _('You are not a party to this settlement.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        # Only allow cancellation in early states
        cancellable_states = [
            'MATCH_PROPOSED', 'INTENT_LOCKED', 'BUYER_DEBIT_INITIATED'
        ]

        if settlement.state not in cancellable_states:
            return Response({
                'success': False,
                'error': {
                    'code': 'cannot_cancel',
                    'message': _('This settlement has progressed too far to cancel. Please raise a dispute instead.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Cancel the settlement
        settlement.state = SettlementState.REVERSED
        settlement.reversed_at = timezone.now()
        settlement.save(update_fields=['state', 'reversed_at'])

        # Release reserved shares
        if hasattr(settlement, 'connection') and settlement.connection:
            lr = settlement.connection.liquidity_request
            if lr and lr.holding:
                lr.holding.release_shares(lr.share_quantity)
                lr.status = 'CANCELLED'
                lr.save()

        logger.info(
            f"Settlement {settlement.uuid} cancelled by {request.user.email}"
        )

        return Response({
            'success': True,
            'data': SettlementIntentSerializer(settlement).data,
            'message': _('Settlement cancelled.'),
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        from django.db import models

        settlements = SettlementIntent.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user),
            is_deleted=False,
        )

        total_bought = settlements.filter(
            buyer=user, state='LEDGER_FINALIZED'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        total_sold = settlements.filter(
            seller=user, state='LEDGER_FINALIZED'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        pending = settlements.filter(
            state__in=['MATCH_PROPOSED', 'INTENT_LOCKED', 'BUYER_DEBIT_INITIATED',
                       'BUYER_DEBIT_CONFIRMED', 'SELLER_CREDIT_INITIATED',
                       'SELLER_CREDIT_CONFIRMED']
        ).count()

        disputed = settlements.filter(
            state='DISPUTED_MANUAL'
        ).count()

        return Response({
            'success': True,
            'data': {
                'total_bought': str(total_bought),
                'total_sold': str(total_sold),
                'total_volume': str(total_bought + total_sold),
                'pending_count': pending,
                'disputed_count': disputed,
                'completed_count': settlements.filter(state='LEDGER_FINALIZED').count(),
                'reversed_count': settlements.filter(state='REVERSED').count(),
            },
        })


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

        # Notify both parties of resolution
        try:
            from apps.notifications.models import (
                NotificationCategory,
                NotificationPriority,
            )
            from apps.notifications.services import NotificationService

            for user in [settlement.buyer, settlement.seller]:
                NotificationService.create_notification(
                    user=user,
                    category=NotificationCategory.DISPUTE,
                    title=_('Dispute Resolved'),
                    body=_('Dispute on transaction #%(ref)s has been resolved: %(notes)s.') % {
                        'ref': str(settlement.uuid)[:8],
                        'notes': notes or _('No additional notes.'),
                    },
                    priority=NotificationPriority.URGENT,
                    action_url=f'/transactions/settlements/{settlement.id}/',
                )
        except Exception as e:
            logger.error(f"Failed to send dispute resolution notification: {e}")

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


class RaiseDisputeView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Settlements'],
        summary='Raise a dispute',
        description='File a dispute on a settlement transaction. Optionally attach evidence.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'reason': {'type': 'string'},
                    'description': {'type': 'string'},
                    'evidence': {'type': 'string', 'format': 'binary'},
                }
            }
        }
    )
    def post(self, request, pk=None):
        try:
            settlement = SettlementIntent.objects.get(
                id=pk, is_deleted=False
            )
        except SettlementIntent.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Settlement not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        # Check user is involved
        if request.user != settlement.buyer and request.user != settlement.seller:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_involved',
                    'message': _('You are not a party to this settlement.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        # Check settlement state
        if settlement.state in ['LEDGER_FINALIZED', 'REVERSED', 'CLOSED_BY_TRUSTEE']:
            return Response({
                'success': False,
                'error': {
                    'code': 'settlement_terminal',
                    'message': _('Cannot dispute a finalized or reversed settlement.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check 30-minute cooling period
        elapsed = (timezone.now() - settlement.created_at).total_seconds()
        if elapsed < 1800:
            wait_minutes = int((1800 - elapsed) / 60) + 1
            return Response({
                'success': False,
                'error': {
                    'code': 'cooling_period',
                    'message': _('Please wait %(minutes)d more minutes before raising a dispute.') % {'minutes': wait_minutes}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing dispute
        if Dispute.objects.filter(settlement=settlement, raised_by=request.user).exists():
            return Response({
                'success': False,
                'error': {
                    'code': 'already_disputed',
                    'message': _('You have already raised a dispute on this settlement.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Handle evidence upload
        evidence = request.FILES.get('evidence')
        if evidence:
            if evidence.size > 10 * 1024 * 1024:  # 10MB limit
                return Response({
                    'success': False,
                    'error': {
                        'code': 'file_too_large',
                        'message': _('Evidence file must be under 10MB.')
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
            if evidence.content_type not in allowed_types:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'invalid_format',
                        'message': _('Only JPG, PNG, WebP, and PDF files are accepted.')
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        dispute = Dispute.objects.create(
            settlement=settlement,
            raised_by=request.user,
            reason=serializer.validated_data['reason'],
            description=serializer.validated_data.get('description', ''),
            evidence=evidence,
        )

        # Mark settlement as disputed
        settlement.state = SettlementState.DISPUTED_MANUAL
        settlement.dispute_opened_at = timezone.now()
        settlement.save(update_fields=['state', 'dispute_opened_at'])

        logger.info(
            f"Dispute raised by {request.user.email} on settlement {settlement.uuid}"
        )

        return Response({
            'success': True,
            'data': DisputeSerializer(dispute).data,
            'message': _('Dispute raised. Our team will investigate.'),
        }, status=status.HTTP_201_CREATED)

class MyDisputesView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Settlements'],
        summary='My disputes',
        description='List disputes raised by the authenticated user.'
    )
    def get(self, request):
        disputes = Dispute.objects.filter(
            raised_by=request.user, is_deleted=False
        ).select_related('settlement').order_by('-opened_at')

        paginator = SmallPagination()
        page = paginator.paginate_queryset(disputes, request)
        serializer = DisputeSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class DisputeDetailView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Settlements'],
        summary='Dispute details',
        description='Get details of a specific dispute.'
    )
    def get(self, request, pk=None):
        try:
            dispute = Dispute.objects.get(
                id=pk, raised_by=request.user, is_deleted=False
            )
        except Dispute.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Dispute not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = DisputeSerializer(dispute)
        return Response({
            'success': True,
            'data': serializer.data,
        })