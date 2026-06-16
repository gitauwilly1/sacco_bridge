from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.escrow.models import EscrowAccount
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