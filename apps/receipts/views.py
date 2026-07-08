import io
import logging

from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

import qrcode

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
        receipt = self._get_receipt(receipt_id, request.user)
        if not receipt:
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

    def _get_receipt(self, receipt_id, user):
        try:
            return Receipt.objects.get(receipt_number=receipt_id, user=user)
        except Receipt.DoesNotExist:
            pass
        try:
            return Receipt.objects.get(settlement__uuid=receipt_id, user=user)
        except Receipt.DoesNotExist:
            pass
        try:
            return Receipt.objects.get(id=receipt_id, user=user)
        except (Receipt.DoesNotExist, ValueError):
            return None


class ReceiptDownloadView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Receipts'],
        summary='Download receipt PDF',
        description='Download the PDF file for a specific receipt.'
    )
    def get(self, request, receipt_id):
        receipt = ReceiptDetailView()._get_receipt(receipt_id, request.user)
        if not receipt:
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


class ReceiptQRView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Receipts'],
        summary='Get receipt QR code image',
        description='Get a PNG image of the QR code for a specific receipt.'
    )
    def get(self, request, receipt_id):
        receipt = ReceiptDetailView()._get_receipt(receipt_id, request.user)
        if not receipt:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('Receipt not found.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(f"https://saccobridge.co.ke/verify/{receipt.verification_code}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='#C67B5C', back_color='white')

        buf = io.BytesIO()
        qr_img.save(buf, format='PNG')
        buf.seek(0)

        return FileResponse(buf, content_type='image/png')