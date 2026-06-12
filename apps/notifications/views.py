from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils.translation import gettext_lazy as _

from apps.core.pagination import SmallPagination
from apps.core.mixins import SoftDeleteMixin
from apps.notifications.models import (
    Notification, UserDevice, NotificationPreference,
    NotificationCategory
)
from apps.notifications.serializers import (
    NotificationSerializer, UserDeviceSerializer,
    NotificationPreferenceSerializer,
)
from apps.notifications.services import NotificationService


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List notifications'),
    retrieve=extend_schema(tags=['Notifications'], summary='Get notification'),
)
class NotificationViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

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
        NotificationService.mark_all_read(request.user)
        return Response({
            'success': True,
            'data': {'unread_count': 0},
            'message': _('All notifications marked as read.'),
        })

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
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


class DeviceViewSet(viewsets.ModelViewSet):

    serializer_class = UserDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserDevice.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        firebase_token = serializer.validated_data.get('firebase_token')
        UserDevice.objects.filter(firebase_token=firebase_token).delete()
        serializer.save(user=self.request.user)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)