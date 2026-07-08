from django.urls import path

from apps.receipts.views import (
    ReceiptDetailView,
    ReceiptDownloadView,
    ReceiptListView,
    ReceiptQRView,
)

urlpatterns = [
    path('', ReceiptListView.as_view(), name='receipt-list'),
    path('<str:receipt_id>/', ReceiptDetailView.as_view(), name='receipt-detail'),
    path('<str:receipt_id>/download/', ReceiptDownloadView.as_view(), name='receipt-download'),
    path('<str:receipt_id>/qr/', ReceiptQRView.as_view(), name='receipt-qr'),
]