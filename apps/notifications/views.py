import logging
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.pagination import SmallPagination
from apps.notifications.models import (
    Notification, UserDevice, NotificationPreference,
    NotificationTemplate, NotificationStatus,
)
from apps.notifications.serializers import (
    NotificationSerializer, UserDeviceSerializer,
    DeviceRegistrationSerializer, NotificationPreferenceSerializer,
    NotificationPreferenceBulkUpdateSerializer,
)
from apps.notifications.services import (
    FirebaseService, NotificationService
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List notifications'),
    retrieve=extend_schema(tags=['Notifications'], summary='Get notification'),
)
class NotificationViewSet(viewsets.ModelViewSet):

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_deleted=False
        )

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        count = NotificationService.mark_all_read(request.user)
        return Response({
            'success': True,
            'data': {'marked_read': count},
            'message': _('All notifications marked as read.'),
        })

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()

        if notification.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]:
            notification.mark_as_read()

        return Response({
            'success': True,
            'data': NotificationSerializer(notification).data,
            'message': _('Notification marked as read.'),
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({
            'success': True,
            'data': {'unread_count': count},
        })

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        Notification.objects.filter(
            user=request.user
        ).update(is_deleted=True)
        return Response({
            'success': True,
            'data': {},
            'message': _('All notifications cleared.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List registered devices'),
    create=extend_schema(tags=['Notifications'], summary='Register device for push'),
)
class DeviceViewSet(viewsets.ModelViewSet):

    serializer_class = UserDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserDevice.objects.filter(
            user=self.request.user,
            is_active=True
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return DeviceRegistrationSerializer
        return UserDeviceSerializer

    def perform_create(self, serializer):
        device = FirebaseService.register_device(
            user=self.request.user,
            fcm_token=serializer.validated_data['fcm_token'],
            platform=serializer.validated_data['platform'],
            device_name=serializer.validated_data.get('device_name', ''),
            device_model=serializer.validated_data.get('device_model', ''),
            app_version=serializer.validated_data.get('app_version', ''),
        )
        return device

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        device = self.get_object()
        FirebaseService.unregister_device(device.fcm_token)
        return Response({
            'success': True,
            'data': {},
            'message': _('Device deactivated.'),
        })

    @action(detail=False, methods=['post'])
    def test_push(self, request):
        """Send a test push notification to all active devices."""
        success, failure, _ = FirebaseService.send_push_notification(
            request.user,
            title='Test Notification',
            body='This is a test push notification from Sacco Bridge.',
        )

        return Response({
            'success': True,
            'data': {
                'devices_reached': success,
                'devices_failed': failure,
            },
            'message': _('Test notification sent.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List notification preferences'),
    create=extend_schema(tags=['Notifications'], summary='Update preferences'),
)
class NotificationPreferenceViewSet(viewsets.ModelViewSet):

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationPreference.objects.filter(
            user=self.request.user
        )

    @action(detail=False, methods=['put'])
    def bulk_update(self, request):
        serializer = NotificationPreferenceBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        preferences = serializer.validated_data['preferences']

        for pref in preferences:
            NotificationPreference.objects.update_or_create(
                user=request.user,
                category=pref.get('category', pref.get('category')),
                channel=pref.get('channel', pref.get('channel')),
                defaults={'enabled': pref.get('enabled', True)}
            )

        return Response({
            'success': True,
            'data': {},
            'message': _('Preferences updated.'),
        })