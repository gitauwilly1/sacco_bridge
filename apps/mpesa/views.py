import ipaddress
import logging
from decimal import Decimal

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mpesa.models import (
    MpesaTransaction,
    MpesaTransactionStatus,
    MpesaTransactionType,
)
from apps.mpesa.serializers import (
    MpesaTransactionSerializer,
    StkPushRequestSerializer,
    StkPushResponseSerializer,
)
from apps.mpesa.services import MpesaService

logger = logging.getLogger(__name__)

# Safaricom Daraja Official IP Ranges (CIDR)
SAFARICOM_IP_RANGES = [
    ipaddress.ip_network('196.201.214.0/24'),
    ipaddress.ip_network('196.201.213.0/24'),
    ipaddress.ip_network('196.201.215.0/24'),
    ipaddress.ip_network('196.13.107.0/24'),
]

# Development / Loopback / Local IP Ranges
ALLOWED_DEV_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
]


def get_client_ip(request):
    """Extract client IP address handling proxies and direct connections."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '').strip()
    return ip


def is_authorized_safaricom_ip(ip_str):
    """Validate client IP against Safaricom CIDR blocks and configured dev allowlists."""
    if not ip_str:
        return False
    try:
        client_ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    # Check Safaricom production CIDRs
    for network in SAFARICOM_IP_RANGES:
        if client_ip in network:
            return True

    # If dev/test environment or explicit dev allowlist enabled
    allow_dev = getattr(settings, 'MPESA_ALLOW_DEV_IPS', getattr(settings, 'DEBUG', False))
    if allow_dev:
        for network in ALLOWED_DEV_NETWORKS:
            if client_ip in network:
                return True

    return False


def is_authorized_callback_secret(request, secret_key=None):
    """Validate shared secret token across URL path, query params, or header."""
    expected_secret = getattr(settings, 'MPESA_CALLBACK_SECRET', None)
    if not expected_secret:
        return True

    # 1. URL Path token
    if secret_key and secret_key == expected_secret:
        return True

    # 2. Query parameter (?token=... or ?secret=...)
    query_token = request.query_params.get('token') or request.query_params.get('secret')
    if query_token and query_token == expected_secret:
        return True

    # 3. HTTP Header (X-Callback-Secret or X-Mpesa-Token)
    header_token = request.headers.get('X-Callback-Secret') or request.headers.get('X-Mpesa-Token')
    if header_token and header_token == expected_secret:
        return True

    return False


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
def mpesa_callback(request, secret_key=None):
    """
    Safaricom M-Pesa STK Push Callback Endpoint.
    Enforces IP allowlisting and shared secret authentication.
    Rejections return silent 200 (ResultCode: 0) to avoid disclosing endpoint behavior to probers.
    """
    client_ip = get_client_ip(request)
    logger.info(f"M-Pesa callback received from {client_ip}")

    # 1. IP Allowlist Verification
    enforce_ip = getattr(settings, 'MPESA_ENFORCE_IP_ALLOWLIST', not getattr(settings, 'DEBUG', False))
    if enforce_ip and not is_authorized_safaricom_ip(client_ip):
        logger.warning(
            f"Unauthorized M-Pesa callback attempt from untrusted IP: {client_ip}. Silently rejecting."
        )
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Accepted'
        }, status=status.HTTP_200_OK)

    # 2. Shared Secret Verification (Defense in Depth)
    if not is_authorized_callback_secret(request, secret_key=secret_key):
        logger.warning(
            f"Unauthorized M-Pesa callback attempt: invalid/missing secret token. Silently rejecting."
        )
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Accepted'
        }, status=status.HTTP_200_OK)

    # Process verified callback payload
    result = MpesaService.process_callback(request.data)

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
