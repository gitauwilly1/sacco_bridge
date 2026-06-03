from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.investments.views import (
    SACCOViewSet, SACCOHoldingViewSet,
    LiquidityRequestViewSet, OpportunityViewSet,
    ConnectionViewSet,
)

router = SimpleRouter()
router.register(r'saccos', SACCOViewSet, basename='sacco')
router.register(r'holdings', SACCOHoldingViewSet, basename='holding')
router.register(r'requests', LiquidityRequestViewSet, basename='liquidity-request')
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')
router.register(r'connections', ConnectionViewSet, basename='connection')

urlpatterns = [
    path('', include(router.urls)),
]