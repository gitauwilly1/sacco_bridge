from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.investments.views import (
    AdminSACCOViewSet,
    ConnectionViewSet,
    LiquidityRequestViewSet,
    OpportunityViewSet,
    SACCOHoldingViewSet,
    SACCOViewSet,
)

router = SimpleRouter()
router.register(r'saccos', SACCOViewSet, basename='sacco')
router.register(r'holdings', SACCOHoldingViewSet, basename='holding')
router.register(r'requests', LiquidityRequestViewSet, basename='liquidity-request')
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')
router.register(r'connections', ConnectionViewSet, basename='connection')
router.register(r'admin/saccos', AdminSACCOViewSet, basename='admin-sacco')

urlpatterns = [
    path('', include(router.urls)),
]