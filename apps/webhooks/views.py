from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from apps.webhooks.models import WebhookSubscription, WebhookDelivery
from apps.webhooks.serializers import (
    WebhookSubscriptionSerializer, WebhookDeliverySerializer,
)
from apps.webhooks.tasks import deliver_webhook
from apps.users.permissions import IsPlatformStaff


class WebhookSubscriptionViewSet(viewsets.ModelViewSet):

    serializer_class = WebhookSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get_queryset(self):
        return WebhookSubscription.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def regenerate_secret(self, request, pk=None):
        import uuid
        subscription = self.get_object()
        subscription.secret = str(uuid.uuid4())
        subscription.save(update_fields=['secret'])
        return Response({
            'success': True,
            'data': {'secret': subscription.secret},
            'message': _('Secret regenerated.'),
        })


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = WebhookDeliverySerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get_queryset(self):
        return WebhookDelivery.objects.all().order_by('-created_at')

    @action(detail=True, methods=['post'])
    def replay(self, request, pk=None):
        delivery = self.get_object()

        if delivery.status == 'SUCCESS':
            return Response({
                'success': False,
                'error': {'code': 'already_delivered', 'message': _('Already delivered.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        delivery.status = 'PENDING'
        delivery.attempt_count = 0
        delivery.save()

        deliver_webhook.delay(str(delivery.id))

        return Response({
            'success': True,
            'data': {},
            'message': _('Webhook queued for replay.'),
        })