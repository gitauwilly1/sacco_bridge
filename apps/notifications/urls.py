from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications.views import (
    NotificationViewSet, DeviceViewSet, NotificationPreferenceViewSet,
)

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')

urlpatterns = [
    path('', include(router.urls)),
]