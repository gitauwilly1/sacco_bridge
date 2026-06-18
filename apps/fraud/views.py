from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from apps.fraud.models import TransactionRiskAssessment, DeviceFingerprint
from apps.fraud.serializers import RiskAssessmentSerializer
from apps.users.permissions import IsPlatformStaff


class RiskAssessmentViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = RiskAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get_queryset(self):
        return TransactionRiskAssessment.objects.all().order_by('-created_at')

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        assessment = self.get_object()

        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action not in ['approve', 'reject']:
            return Response({
                'success': False,
                'error': {'code': 'invalid_action', 'message': _('Action must be approve or reject.')}
            }, status=400)

        assessment.reviewed_by = request.user
        assessment.reviewed_at = __import__('django.utils.timezone').now()
        assessment.review_notes = notes

        if action == 'approve':
            assessment.applied_action = 'ALLOW'
        else:
            assessment.applied_action = 'BLOCK'

        assessment.save()

        return Response({
            'success': True,
            'data': RiskAssessmentSerializer(assessment).data,
            'message': _('Review recorded.'),
        })


class DeviceTrustViewSet(viewsets.ReadOnlyModelViewSet):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get_queryset(self):
        return DeviceFingerprint.objects.all().order_by('-last_seen')

    @action(detail=True, methods=['post'])
    def trust(self, request, pk=None):
        device = self.get_object()
        device.is_trusted = True
        device.save()
        return Response({'success': True, 'message': _('Device trusted.')})

    @action(detail=True, methods=['post'])
    def untrust(self, request, pk=None):
        device = self.get_object()
        device.is_trusted = False
        device.save()
        return Response({'success': True, 'message': _('Device untrusted.')})