from django.urls import path
from apps.receipts.views import (
    ReceiptListView, ReceiptDetailView, ReceiptDownloadView,
)

urlpatterns = [
    path('', ReceiptListView.as_view(), name='receipt-list'),
    path('<str:receipt_id>/', ReceiptDetailView.as_view(), name='receipt-detail'),
    path('<str:receipt_id>/download/', ReceiptDownloadView.as_view(), name='receipt-download'),
]