from django.urls import path

from apps.mpesa.views import (
    MpesaTransactionDetailView,
    MpesaTransactionView,
    StkPushView,
    mpesa_callback,
)

urlpatterns = [
    path('stk-push/', StkPushView.as_view(), name='mpesa-stk-push'),
    path('callback/', mpesa_callback, name='mpesa-callback'),
    path('transactions/', MpesaTransactionView.as_view(), name='mpesa-transactions'),
    path('transactions/<uuid:transaction_id>/', MpesaTransactionDetailView.as_view(), name='mpesa-transaction-detail'),
]