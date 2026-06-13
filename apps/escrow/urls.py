from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.escrow.views import EscrowAccountViewSet, EscrowSummaryView

router = SimpleRouter()
router.register(r'accounts', EscrowAccountViewSet, basename='escrow-account')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', EscrowSummaryView.as_view(), name='escrow-summary'),
]