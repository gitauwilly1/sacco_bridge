from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.legal.views import (
    LatestTermsView, LatestPrivacyView,
    AcceptDocumentView, AcceptanceStatusView,
    LegalDocumentViewSet,
)

router = SimpleRouter()
router.register(r'admin', LegalDocumentViewSet, basename='legal-admin')

urlpatterns = [
    path('', include(router.urls)),
    path('terms/', LatestTermsView.as_view(), name='legal-terms'),
    path('privacy/', LatestPrivacyView.as_view(), name='legal-privacy'),
    path('accept/', AcceptDocumentView.as_view(), name='legal-accept'),
    path('status/', AcceptanceStatusView.as_view(), name='legal-status'),
]