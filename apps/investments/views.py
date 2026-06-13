import logging
from django.db import transaction
from django.utils import timezone
from django.db import models as django_models
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.exceptions import (
    InsufficientFundsError, VerificationError, PermissionDeniedError
)
from apps.core.pagination import SmallPagination
from apps.core.mixins import SoftDeleteMixin
from apps.investments.models import (
    SACCO, SACCOShareClass, SACCOMemberHolding,
    LiquidityRequest, BuyerInterest, Connection, Offer,
    LiquidityRequestStatus, ConnectionStatus
)
from apps.investments.serializers import (
    SACCOSerializer, SACCOShareClassSerializer,
    SACCOMemberHoldingSerializer,
    LiquidityRequestSerializer, LiquidityRequestCreateSerializer,
    BuyerInterestSerializer, ConnectionSerializer, OfferSerializer,
)
from apps.users.permissions import (
    IsVerifiedUser, IsInvestorOrInstitutional, IsPlatformStaff
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=['Investments'], summary='List verified SACCOs'),
    retrieve=extend_schema(tags=['Investments'], summary='Get SACCO details'),
)
class SACCOViewSet(SoftDeleteMixin, viewsets.ReadOnlyModelViewSet):

    serializer_class = SACCOSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    pagination_class = SmallPagination
    search_fields = ['name', 'description', 'registration_number']
    ordering_fields = ['name', 'total_assets', 'dividend_rate', 'total_members']

    def get_queryset(self):
        return SACCO.objects.filter(
            status='ACTIVE',
            trading_halted=False,
            is_deleted=False
        )

    @action(detail=True, methods=['get'])
    def share_classes(self, request, pk=None):
        sacco = self.get_object()
        classes = sacco.share_classes.filter(is_deleted=False)
        serializer = SACCOShareClassSerializer(classes, many=True)
        return Response({'success': True, 'data': serializer.data})

@extend_schema_view(
    list=extend_schema(tags=['Admin'], summary='[Admin] List all SACCOs'),
    create=extend_schema(tags=['Admin'], summary='[Admin] Create SACCO'),
    retrieve=extend_schema(tags=['Admin'], summary='[Admin] Get SACCO details'),
    update=extend_schema(tags=['Admin'], summary='[Admin] Update SACCO'),
    partial_update=extend_schema(tags=['Admin'], summary='[Admin] Partial update SACCO'),
    destroy=extend_schema(tags=['Admin'], summary='[Admin] Delete SACCO'),
)
class AdminSACCOViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = SACCOSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]
    pagination_class = SmallPagination
    search_fields = ['name', 'description', 'registration_number', 'sasra_tier']
    ordering_fields = ['name', 'total_assets', 'dividend_rate', 'status', 'created_at']

    def get_queryset(self):
        return SACCO.objects.filter(is_deleted=False)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        sacco = self.get_object()
        sacco.status = 'ACTIVE'
        sacco.verified_by = request.user
        sacco.verified_at = timezone.now()
        sacco.save(update_fields=['status', 'verified_by', 'verified_at'])
        return Response({
            'success': True,
            'data': SACCOSerializer(sacco).data,
            'message': _('SACCO verified successfully.')
        })

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        sacco = self.get_object()
        sacco.status = 'SUSPENDED'
        sacco.trading_halted = True
        sacco.halt_reason = request.data.get('reason', 'Suspended by administrator')
        sacco.save(update_fields=['status', 'trading_halted', 'halt_reason'])
        return Response({
            'success': True,
            'data': SACCOSerializer(sacco).data,
            'message': _('SACCO suspended.')
        })

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        sacco = self.get_object()
        sacco.status = 'ACTIVE'
        sacco.trading_halted = False
        sacco.halt_reason = ''
        sacco.save(update_fields=['status', 'trading_halted', 'halt_reason'])
        return Response({
            'success': True,
            'data': SACCOSerializer(sacco).data,
            'message': _('SACCO reactivated.')
        })
    
    @action(detail=True, methods=['post'])
    def upload_logo(self, request, pk=None):
        sacco = self.get_object()

        if 'logo' not in request.FILES:
            return Response({
                'success': False,
                'error': {
                    'code': 'missing_file',
                    'message': _('No file uploaded. Use key "logo".')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['logo']

        if file.size > 2 * 1024 * 1024:
            return Response({
                'success': False,
                'error': {
                    'code': 'file_too_large',
                    'message': _('Logo must be under 2MB.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/svg+xml']
        if file.content_type not in allowed_types:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_format',
                    'message': _('Only JPG, PNG, WebP, and SVG images are accepted.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if sacco.logo:
            sacco.logo.delete(save=False)

        sacco.logo = file
        sacco.save(update_fields=['logo'])

        serializer = SACCOSerializer(sacco)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': _('Logo uploaded.'),
        })

@extend_schema_view(
    list=extend_schema(tags=['Investments'], summary='List my SACCO holdings'),
    retrieve=extend_schema(tags=['Investments'], summary='Get holding details'),
)
class SACCOHoldingViewSet(SoftDeleteMixin, viewsets.ReadOnlyModelViewSet):

    serializer_class = SACCOMemberHoldingSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['sacco__name']
    ordering_fields = ['total_shares', 'created_at']

    def get_queryset(self):
        return SACCOMemberHolding.objects.filter(
            user=self.request.user,
            is_deleted=False
        )


@extend_schema_view(
    list=extend_schema(tags=['Investments'], summary='List my liquidity requests'),
    create=extend_schema(tags=['Investments'], summary='Create liquidity request'),
    retrieve=extend_schema(tags=['Investments'], summary='Get request details'),
)
class LiquidityRequestViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = LiquidityRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    pagination_class = SmallPagination
    search_fields = ['sacco__name', 'notes']
    ordering_fields = ['created_at', 'share_quantity', 'expected_price_per_share', 'urgency', 'status']

    def get_queryset(self):
        return LiquidityRequest.objects.filter(
            seller=self.request.user,
            is_deleted=False
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return LiquidityRequestCreateSerializer
        return LiquidityRequestSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            holding = serializer.validated_data['holding']

            if holding.user != self.request.user:
                raise PermissionDeniedError(_('This holding does not belong to you.'))

            quantity = serializer.validated_data['share_quantity']
            holding.reserve_shares(quantity)

            liquidity_request = serializer.save(seller=self.request.user)
            logger.info(f"Liquidity request created: {liquidity_request.id}")

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        liquidity_request = self.get_object()

        if liquidity_request.status not in [
            LiquidityRequestStatus.ACTIVE,
            LiquidityRequestStatus.MATCHED
        ]:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_state',
                    'message': _('Only active requests can be cancelled.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        liquidity_request.status = LiquidityRequestStatus.CANCELLED
        liquidity_request.save()

        if liquidity_request.holding:
            liquidity_request.holding.release_shares(
                liquidity_request.share_quantity
            )

        return Response({
            'success': True,
            'data': {},
            'message': _('Liquidity request cancelled. Shares released.')
        })


@extend_schema_view(
    list=extend_schema(tags=['Investments'], summary='Browse active liquidity requests'),
    retrieve=extend_schema(tags=['Investments'], summary='Get request details'),
)
class OpportunityViewSet(SoftDeleteMixin, viewsets.ReadOnlyModelViewSet):

    serializer_class = LiquidityRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    pagination_class = SmallPagination
    search_fields = ['sacco__name', 'notes']
    ordering_fields = ['created_at', 'share_quantity', 'expected_price_per_share', 'urgency']

    def get_queryset(self):
        # Get SACCOs where the current user has verified holdings
        user_saccos = SACCOMemberHolding.objects.filter(
            user=self.request.user,
            verification_status='VERIFIED',
            is_deleted=False,
        ).values_list('sacco_id', flat=True)

        return LiquidityRequest.objects.filter(
            status=LiquidityRequestStatus.ACTIVE,
            sacco_id__in=user_saccos,
            sacco__trading_halted=False,
            is_deleted=False,
        ).exclude(seller=self.request.user)

    @action(detail=True, methods=['post'])
    def express_interest(self, request, pk=None):
        liquidity_request = self.get_object()

        if liquidity_request.status != LiquidityRequestStatus.ACTIVE:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_state',
                    'message': _('This request is no longer active.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify buyer is a member of the same SACCO
        is_member = SACCOMemberHolding.objects.filter(
            user=request.user,
            sacco=liquidity_request.sacco,
            verification_status='VERIFIED',
            is_deleted=False,
        ).exists()

        if not is_member:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_a_member',
                    'message': _('You must be a verified member of {sacco} to express interest.').format(
                        sacco=liquidity_request.sacco.name
                    )
                }
            }, status=status.HTTP_403_FORBIDDEN)

        interest, created = BuyerInterest.objects.get_or_create(
            liquidity_request=liquidity_request,
            buyer=request.user,
            defaults={
                'buyer_message': request.data.get('message', ''),
            }
        )

        if not created:
            return Response({
                'success': False,
                'error': {
                    'code': 'already_expressed',
                    'message': _('You have already expressed interest.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        liquidity_request.status = LiquidityRequestStatus.MATCHED
        liquidity_request.save()

        logger.info(f"Buyer {request.user.email} expressed interest in request {liquidity_request.id}")

        return Response({
            'success': True,
            'data': BuyerInterestSerializer(interest).data,
            'message': _('Interest expressed. Seller will be notified.'),
        })

@extend_schema_view(
    list=extend_schema(tags=['Investments'], summary='List my connections'),
    retrieve=extend_schema(tags=['Investments'], summary='Get connection details'),
)
class ConnectionViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    search_fields = ['liquidity_request__sacco__name']
    ordering_fields = ['created_at', 'status', 'total_amount']

    def get_queryset(self):
        user = self.request.user
        return Connection.objects.filter(
            django_models.Q(seller=user) | django_models.Q(buyer=user),
            is_deleted=False
        )

    @action(detail=True, methods=['post'])
    def make_offer(self, request, pk=None):
        connection = self.get_object()

        if connection.status not in [
            ConnectionStatus.CONNECTED,
            ConnectionStatus.OFFER_COUNTERED,
            ConnectionStatus.OFFER_DECLINED,
        ]:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_state',
                    'message': _('Cannot make offer in current connection state.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if request.user != connection.buyer and request.user != connection.seller:
            raise PermissionDeniedError()

        # Verify buyer is still a verified member of the SACCO
        if request.user == connection.buyer:
            is_member = SACCOMemberHolding.objects.filter(
                user=request.user,
                sacco=connection.liquidity_request.sacco,
                verification_status='VERIFIED',
                is_deleted=False,
            ).exists()

            if not is_member:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'membership_required',
                        'message': _('You must maintain verified membership in {sacco} to make an offer.').format(
                            sacco=connection.liquidity_request.sacco.name
                        )
                    }
                }, status=status.HTTP_403_FORBIDDEN)

        offer = Offer.objects.create(
            connection=connection,
            offered_by=request.user,
            price_per_share=request.data['price_per_share'],
            quantity=request.data.get('quantity', connection.liquidity_request.share_quantity),
            message=request.data.get('message', ''),
        )

        connection.status = ConnectionStatus.OFFER_MADE
        connection.save()

        return Response({
            'success': True,
            'data': OfferSerializer(offer).data,
            'message': _('Offer submitted.'),
        })
    
    @action(detail=True, methods=['post'], url_path='offers/(?P<offer_pk>[^/.]+)/accept')
    def accept_offer(self, request, pk=None, offer_pk=None):
        connection = self.get_object()

        try:
            offer = connection.offers.get(id=offer_pk)
        except Offer.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Offer not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        if offer.offered_by == request.user:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_action',
                    'message': _('Cannot accept your own offer.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        offer.accept()

        logger.info(f"Offer {offer.id} accepted. Connection {connection.id} ready for settlement.")

        return Response({
            'success': True,
            'data': ConnectionSerializer(connection).data,
            'message': _('Offer accepted. Proceeding to settlement.'),
        })

    @action(detail=True, methods=['post'], url_path='offers/(?P<offer_pk>[^/.]+)/decline')
    def decline_offer(self, request, pk=None, offer_pk=None):
        connection = self.get_object()

        try:
            offer = connection.offers.get(id=offer_pk)
        except Offer.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Offer not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        offer.decline()
        connection.status = ConnectionStatus.OFFER_DECLINED
        connection.save()

        return Response({
            'success': True,
            'data': {},
            'message': _('Offer declined.'),
        })

    @action(detail=True, methods=['post'], url_path='offers/(?P<offer_pk>[^/.]+)/counter')
    def counter_offer(self, request, pk=None, offer_pk=None):
        connection = self.get_object()

        try:
            offer = connection.offers.get(id=offer_pk)
        except Offer.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Offer not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        new_price = request.data.get('price_per_share')
        if not new_price:
            return Response({
                'success': False,
                'error': {'code': 'missing_price', 'message': _('New price is required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        counter = offer.counter(
            new_price_per_share=new_price,
            new_quantity=request.data.get('quantity'),
            message=request.data.get('message', ''),
        )

        return Response({
            'success': True,
            'data': OfferSerializer(counter).data,
            'message': _('Counter offer submitted.'),
        })