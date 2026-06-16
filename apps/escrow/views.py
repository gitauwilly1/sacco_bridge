from apps.core.pagination import SmallPagination
from apps.users.permissions import IsPlatformStaff
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.escrow.models import EscrowAccount, EscrowStatus
from apps.escrow.serializers import EscrowAccountSerializer
from apps.escrow.services import EscrowService


class EscrowAccountViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = EscrowAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        from django.db import models
        return EscrowAccount.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).order_by('-created_at')


class EscrowSummaryView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Escrow'],
        summary='Get escrow summary',
        description='View total held, received, and active escrows.'
    )
    def get(self, request):
        summary = EscrowService.get_escrow_summary(request.user)
        return Response({
            'success': True,
            'data': summary,
        })

class ReleaseHoldView(APIView):
    
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        tags=['Escrow'],
        summary='Release held funds',
        description='Admin releases funds held for risk review.'
    )
    def post(self, request, escrow_id):
        try:
            escrow = EscrowAccount.objects.get(
                id=escrow_id,
                status__in=[EscrowStatus.HELD, EscrowStatus.HELD_PARTIAL],
            )
        except EscrowAccount.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Held escrow not found.')}
            }, status=404)

        action = request.data.get('action', 'release')
        notes = request.data.get('notes', '')
        amount = request.data.get('amount')

        if action == 'release':
            escrow.release_hold(released_by=request.user)
            message = _('Full amount released.')

        elif action == 'partial_release' and amount:
            from decimal import Decimal
            release_amount = Decimal(str(amount))

            if release_amount > escrow.hold_amount:
                return Response({
                    'success': False,
                    'error': {'code': 'exceeds_hold', 'message': _('Release amount exceeds held amount.')}
                }, status=400)

            escrow.progressive_release(release_amount, released_by=request.user)
            message = _(f'KSh {release_amount:,.2f} released. Remaining held: KSh {escrow.hold_amount - escrow.released_amount:,.2f}.')

        elif action == 'refund':
            escrow.mark_refunded(refund_ref=notes)
            message = _('Funds refunded to buyer.')

        else:
            return Response({
                'success': False,
                'error': {'code': 'invalid_action', 'message': _('Invalid action.')}
            }, status=400)

        return Response({
            'success': True,
            'data': EscrowAccountSerializer(escrow).data,
            'message': message,
        })


class EscrowHoldListView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        tags=['Escrow'],
        summary='List held escrows',
        description='View all escrows currently on hold.'
    )
    def get(self, request):
        held = EscrowAccount.objects.filter(
            status__in=[EscrowStatus.HELD, EscrowStatus.HELD_PARTIAL],
        ).select_related('buyer', 'seller', 'settlement').order_by('-created_at')

        paginator = SmallPagination()
        page = paginator.paginate_queryset(held, request)
        serializer = EscrowAccountSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)