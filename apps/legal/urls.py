from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.legal.views import (
    LatestTermsView, LatestPrivacyView,
    AcceptDocumentView, AcceptanceStatusView,
    LegalDocumentViewSet, SignatureVerifyView, 
    SignatureRequestView, SignatureConfirmView
)

router = SimpleRouter()
router.register(r'admin', LegalDocumentViewSet, basename='legal-admin')

urlpatterns = [
    path('', include(router.urls)),
    path('terms/', LatestTermsView.as_view(), name='legal-terms'),
    path('privacy/', LatestPrivacyView.as_view(), name='legal-privacy'),
    path('accept/', AcceptDocumentView.as_view(), name='legal-accept'),
    path('status/', AcceptanceStatusView.as_view(), name='legal-status'),
    path('sign/request/', SignatureRequestView.as_view(), name='legal-sign-request'),
    path('sign/confirm/', SignatureConfirmView.as_view(), name='legal-sign-confirm'),
    path('sign/verify/<str:certificate_hash>/', SignatureVerifyView.as_view(), name='legal-sign-verify'),
]