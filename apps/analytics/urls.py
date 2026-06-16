from django.urls import path

from apps.analytics.views import (
    AdminAnalyticsView,
    AdminExportCSVView,
    AdminHealthCheckView,
    AdminSettlementListView,
    AdminTransactionVolumeView,
    ChamaAnalyticsView,
    PlatformDashboardView,
    RefreshAnalyticsView,
    SACCOMarketView,
    UserDashboardView,
)

urlpatterns = [
    path('dashboard/platform/', PlatformDashboardView.as_view(), name='analytics-platform'),
    path('dashboard/user/', UserDashboardView.as_view(), name='analytics-user'),
    path('chama/<uuid:chama_id>/', ChamaAnalyticsView.as_view(), name='analytics-chama'),
    path('sacco/<uuid:sacco_id>/', SACCOMarketView.as_view(), name='analytics-sacco'),
    path('refresh/', RefreshAnalyticsView.as_view(), name='analytics-refresh'),
    # Admin analytics
    path('admin/overview/', AdminAnalyticsView.as_view(), name='admin-analytics-overview'),
    path('admin/settlements/', AdminSettlementListView.as_view(), name='admin-settlements'),
    path('admin/volume/', AdminTransactionVolumeView.as_view(), name='admin-volume'),
    path('admin/health/', AdminHealthCheckView.as_view(), name='admin-health'),
    path('admin/export/', AdminExportCSVView.as_view(), name='admin-export'),
]