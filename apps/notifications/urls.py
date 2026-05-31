from django.urls import path
from apps.notifications.views import (
    NotificationViewSet, DeviceViewSet,
    NotificationPreferenceViewSet,
)

urlpatterns = [
    # Notification CRUD
    path('', NotificationViewSet.as_view({'get': 'list'}), name='notification-list'),
    path('<uuid:pk>/', NotificationViewSet.as_view({'get': 'retrieve'}), name='notification-detail'),
    path('<uuid:pk>/mark_read/', NotificationViewSet.as_view({'post': 'mark_read'}), name='notification-mark-read'),
    path('mark_all_read/', NotificationViewSet.as_view({'post': 'mark_all_read'}), name='notification-mark-all-read'),
    path('unread_count/', NotificationViewSet.as_view({'get': 'unread_count'}), name='notification-unread-count'),

    # Device management
    path('devices/', DeviceViewSet.as_view({'get': 'list', 'post': 'create'}), name='device-list'),
    path('devices/<uuid:pk>/', DeviceViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='device-detail'),

    # Notification preferences
    path('preferences/', NotificationPreferenceViewSet.as_view({'get': 'list', 'post': 'create'}), name='preference-list'),
    path('preferences/<uuid:pk>/', NotificationPreferenceViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='preference-detail'),
]