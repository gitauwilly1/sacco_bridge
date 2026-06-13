from django.urls import path
from apps.scoring.views import MyCreditScoreView

urlpatterns = [
    path('my-score/', MyCreditScoreView.as_view(), name='my-credit-score'),
]