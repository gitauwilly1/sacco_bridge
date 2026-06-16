from django.urls import path

from apps.scoring.views import MyCreditScoreView, OverrideUnderwritingView, UnderwritingView

urlpatterns = [
    path('my-score/', MyCreditScoreView.as_view(), name='my-credit-score'),
    path('underwriting/<uuid:loan_id>/', UnderwritingView.as_view(), name='loan-underwriting'),
    path('underwriting/<uuid:loan_id>/override/', OverrideUnderwritingView.as_view(), name='override-underwriting'),
]