import logging
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.mpesa.models import MpesaTransaction, MpesaTransactionStatus, MpesaTransactionType
from apps.mpesa.serializers import (
    StkPushRequestSerializer, StkPushResponseSerializer,
    MpesaTransactionSerializer
)
from apps.mpesa.services import MpesaService

logger = logging.getLogger(__name__)


class StkPushView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['M-Pesa'],
        summary='Initiate STK Push payment',
        description='Send an M-Pesa payment request to the user phone.',
        request=StkPushRequestSerializer,
        responses={200: StkPushResponseSerializer}
    )
    def post(self, request):
        serializer = StkPushRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = MpesaService.format_phone_number(
            serializer.validated_data['phone_number']
        )
        amount = serializer.validated_data['amount']
        transaction_type = serializer.validated_data.get(
            'transaction_type', MpesaTransactionType.CHAMA_CONTRIBUTION
        )
        account_reference = serializer.validated_data.get('account_reference', 'SaccoBridge')
        transaction_desc = serializer.validated_data.get(
            'transaction_description', 'Payment'
        )

        # Create transaction record
        transaction = MpesaTransaction.objects.create(
            user=request.user,
            chama_id=serializer.validated_data.get('chama_id'),
            contribution_id=serializer.validated_data.get('contribution_id'),
            transaction_type=transaction_type,
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_description=transaction_desc,
            stk_request_data={
                'phone_number': phone_number,
                'amount': str(amount),
                'account_reference': account_reference,
                'transaction_desc': transaction_desc,
            }
        )

        # Initiate STK Push
        result = MpesaService.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
        )

        if result['success']:
            response_data = result['data']
            transaction.mark_initiated(
                merchant_request_id=response_data.get('MerchantRequestID', ''),
                checkout_request_id=response_data.get('CheckoutRequestID', ''),
                response_data=response_data,
            )

            return Response({
                'success': True,
                'data': {
                    'transaction_id': str(transaction.transaction_id),
                    'checkout_request_id': transaction.checkout_request_id,
                    'status': transaction.status,
                    'message': _('STK Push sent. Check your phone to complete payment.'),
                },
                'message': _('Payment request sent.'),
            })
        else:
            transaction.mark_failed(result.get('error', 'STK Push failed'))
            return Response({
                'success': False,
                'error': {
                    'code': 'stk_push_failed',
                    'message': result.get('error', 'Failed to initiate payment.'),
                }
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def mpesa_callback(request):
    logger.info(f"M-Pesa callback received: {request.data}")

    result = MpesaService.process_callback(request.data)

    if result['success']:
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Accepted'
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Accepted'
        }, status=status.HTTP_200_OK)


class MpesaTransactionView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['M-Pesa'],
        summary='List M-Pesa transactions',
        description='View your M-Pesa payment history.'
    )
    def get(self, request):
        transactions = MpesaTransaction.objects.filter(
            user=request.user,
            is_deleted=False
        ).order_by('-created_at')[:50]

        serializer = MpesaTransactionSerializer(transactions, many=True)

        return Response({
            'success': True,
            'data': serializer.data,
        })


class MpesaTransactionDetailView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['M-Pesa'],
        summary='Get M-Pesa transaction details',
        description='View details of a specific M-Pesa transaction.'
    )
    def get(self, request, transaction_id):
        try:
            transaction = MpesaTransaction.objects.get(
                transaction_id=transaction_id,
                user=request.user
            )
        except MpesaTransaction.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('Transaction not found.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = MpesaTransactionSerializer(transaction)

        return Response({
            'success': True,
            'data': serializer.data,
        })