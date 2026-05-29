"""
URL configuration for the Analytics application.
"""

from django.urls import path
from apps.analytics.views import (
    PlatformDashboardView, UserDashboardView,
    ChamaAnalyticsView, SACCOMarketView,
    RefreshAnalyticsView,
)

urlpatterns = [
    path('dashboard/platform/', PlatformDashboardView.as_view(), name='analytics-platform'),
    path('dashboard/user/', UserDashboardView.as_view(), name='analytics-user'),
    path('chama/<uuid:chama_id>/', ChamaAnalyticsView.as_view(), name='analytics-chama'),
    path('sacco/<uuid:sacco_id>/', SACCOMarketView.as_view(), name='analytics-sacco'),
    path('refresh/', RefreshAnalyticsView.as_view(), name='analytics-refresh'),
]