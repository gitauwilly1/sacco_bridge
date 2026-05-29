from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions.views import (
    SettlementViewSet, DisputeViewSet, LedgerViewSet,
)

router = DefaultRouter()
router.register(r'settlements', SettlementViewSet, basename='settlement')
router.register(r'disputes', DisputeViewSet, basename='dispute')
router.register(r'ledger', LedgerViewSet, basename='ledger')

urlpatterns = [
    path('', include(router.urls)),
]