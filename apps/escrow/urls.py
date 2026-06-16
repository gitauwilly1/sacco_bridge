from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.escrow.views import EscrowAccountViewSet, EscrowHoldListView, EscrowSummaryView, ReleaseHoldView

router = SimpleRouter()
router.register(r'accounts', EscrowAccountViewSet, basename='escrow-account')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', EscrowSummaryView.as_view(), name='escrow-summary'),
    path('held/', EscrowHoldListView.as_view(), name='escrow-held-list'),
    path('accounts/<uuid:escrow_id>/release/', ReleaseHoldView.as_view(), name='escrow-release-hold'),
]