import logging
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.receipts.models import Receipt
from apps.receipts.serializers import ReceiptSerializer

logger = logging.getLogger(__name__)


class ReceiptListView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Receipts'],
        summary='List my receipts',
        description='Get all receipts for the authenticated user.'
    )
    def get(self, request):
        receipts = Receipt.objects.filter(
            user=request.user,
            is_deleted=False
        ).order_by('-generated_at')[:50]

        serializer = ReceiptSerializer(receipts, many=True)

        return Response({
            'success': True,
            'data': serializer.data,
        })


class ReceiptDetailView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Receipts'],
        summary='Get receipt details',
        description='Get metadata for a specific receipt.'
    )
    def get(self, request, receipt_id):
        try:
            receipt = Receipt.objects.get(
                receipt_number=receipt_id,
                user=request.user
            )
        except Receipt.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('Receipt not found.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ReceiptSerializer(receipt)

        return Response({
            'success': True,
            'data': serializer.data,
        })


class ReceiptDownloadView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Receipts'],
        summary='Download receipt PDF',
        description='Download the PDF file for a specific receipt.'
    )
    def get(self, request, receipt_id):
        try:
            receipt = Receipt.objects.get(
                receipt_number=receipt_id,
                user=request.user
            )
        except Receipt.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('Receipt not found.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        if not receipt.pdf_file:
            return Response({
                'success': False,
                'error': {
                    'code': 'no_file',
                    'message': _('PDF file not available for this receipt.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        response = FileResponse(
            receipt.pdf_file.open('rb'),
            content_type='application/pdf',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="SaccoBridge_Receipt_{receipt.receipt_number}.pdf"'
        )
        return response