from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.transactions.views import (
    DisputeDetailView,
    DisputeViewSet,
    LedgerViewSet,
    MyDisputesView,
    RaiseDisputeView,
    SettlementViewSet,
)

router = SimpleRouter()
router.register(r'settlements', SettlementViewSet, basename='settlement')
router.register(r'disputes', DisputeViewSet, basename='dispute')
router.register(r'ledger', LedgerViewSet, basename='ledger')

urlpatterns = [
    path('', include(router.urls)),
    path('settlements/<uuid:pk>/dispute/', RaiseDisputeView.as_view(), name='settlement-raise-dispute'),
    path('disputes/mine/', MyDisputesView.as_view(), name='my-disputes'),
    path('disputes/<uuid:pk>/', DisputeDetailView.as_view(), name='dispute-detail'),
]