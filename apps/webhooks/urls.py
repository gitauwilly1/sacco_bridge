from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.webhooks.views import WebhookSubscriptionViewSet, WebhookDeliveryViewSet

router = SimpleRouter()
router.register(r'subscriptions', WebhookSubscriptionViewSet, basename='webhook-subscription')
router.register(r'deliveries', WebhookDeliveryViewSet, basename='webhook-delivery')

urlpatterns = [
    path('', include(router.urls)),
]