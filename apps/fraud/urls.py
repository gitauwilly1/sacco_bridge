from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.fraud.views import RiskAssessmentViewSet, DeviceTrustViewSet

router = SimpleRouter()
router.register(r'assessments', RiskAssessmentViewSet, basename='fraud-assessment')
router.register(r'devices', DeviceTrustViewSet, basename='fraud-device')

urlpatterns = [
    path('', include(router.urls)),
]