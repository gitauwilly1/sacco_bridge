from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.webhooks.views import WebhookDeliveryViewSet, WebhookSubscriptionViewSet

router = SimpleRouter()
router.register(r'subscriptions', WebhookSubscriptionViewSet, basename='webhook-subscription')
router.register(r'deliveries', WebhookDeliveryViewSet, basename='webhook-delivery')

urlpatterns = [
    path('', include(router.urls)),
]