from django.urls import path

from apps.reports.views import (
    ReportDownloadView,
    ReportRequestView,
    ReportStatusView,
)

urlpatterns = [
    path('', ReportRequestView.as_view(), name='report-list'),
    path('<uuid:report_id>/status/', ReportStatusView.as_view(), name='report-status'),
    path('<uuid:report_id>/download/', ReportDownloadView.as_view(), name='report-download'),
]