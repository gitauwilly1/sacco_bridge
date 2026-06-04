import os
import io
import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
import qrcode
from PIL import Image as PILImage

from apps.receipts.models import Receipt, ReceiptType

logger = logging.getLogger(__name__)

# Brand colors
TERRACOTTA = HexColor('#C67B5C')
DEEP_CLAY = HexColor('#8B4513')
LIGHT_SAND = HexColor('#F5E6D3')
COOL_SLATE = HexColor('#3D405B')
SUCCESS_GREEN = HexColor('#2D8B4E')
BORDER_GRAY = HexColor('#E0E0E0')
TEXT_DARK = HexColor('#1A1A2E')
TEXT_MEDIUM = HexColor('#4A4A5A')


class ReceiptPDFGenerator:

    @classmethod
    def generate_settlement_receipt(cls, settlement, user, receipt_type, party_name):
        receipt_number = cls._generate_receipt_number()
        verification_code = cls._generate_verification_code(
            str(settlement.uuid), str(user.id)
        )

        is_buyer = receipt_type == ReceiptType.SETTLEMENT_BUY

        title = "Share Purchase Receipt" if is_buyer else "Share Sale Receipt"
        description = (
            f"{'Purchase' if is_buyer else 'Sale'} of "
            f"{settlement.share_quantity} shares in {settlement.seller_sacco_name}"
        )

        # Build receipt data
        receipt_data = {
            'receipt_number': receipt_number,
            'date': settlement.finalized_at.strftime('%d %B %Y') if settlement.finalized_at else timezone.now().strftime('%d %B %Y'),
            'time': settlement.finalized_at.strftime('%H:%M') if settlement.finalized_at else timezone.now().strftime('%H:%M'),
            'title': title,
            'user_name': user.get_full_name(),
            'user_email': user.email,
            'user_phone': user.phone_number,
            'party_name': party_name,
            'sacco_name': settlement.seller_sacco_name,
            'shares': str(settlement.share_quantity),
            'price_per_share': cls._format_kes(settlement.price_per_share),
            'total_amount': cls._format_kes(settlement.amount),
            'platform_fee': cls._format_kes(settlement.platform_fee),
            'net_amount': cls._format_kes(settlement.net_seller_amount if settlement.net_seller_amount else settlement.amount - settlement.platform_fee),
            'transaction_ref': str(settlement.uuid)[:8].upper(),
            'description': description,
            'verification_code': verification_code,
        }

        # Generate PDF
        pdf_content = cls._build_pdf(receipt_data, verification_code)

        # Create receipt record
        receipt = Receipt.objects.create(
            receipt_number=receipt_number,
            receipt_type=receipt_type,
            user=user,
            settlement=settlement,
            amount=settlement.amount,
            description=description,
            party_name=party_name,
            verification_code=verification_code,
        )

        # Save PDF file
        filename = f"receipt_{receipt_number}.pdf"
        try:
            receipt.pdf_file.save(filename, ContentFile(pdf_content), save=True)
            logger.info(f"Settlement receipt PDF saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save settlement receipt PDF {filename}: {str(e)}", exc_info=True)
        logger.info(f"Receipt generated: {receipt_number} for user {user.email}")

        return receipt

    @classmethod
    def generate_contribution_receipt(cls, contribution, user, chama_name):
        receipt_number = cls._generate_receipt_number()
        verification_code = cls._generate_verification_code(
            str(contribution.id), str(user.id)
        )

        receipt_data = {
            'receipt_number': receipt_number,
            'date': contribution.paid_at.strftime('%d %B %Y') if contribution.paid_at else timezone.now().strftime('%d %B %Y'),
            'time': contribution.paid_at.strftime('%H:%M') if contribution.paid_at else timezone.now().strftime('%H:%M'),
            'title': 'Contribution Receipt',
            'user_name': user.get_full_name(),
            'user_email': user.email,
            'user_phone': user.phone_number,
            'party_name': chama_name,
            'sacco_name': '',
            'shares': '',
            'price_per_share': '',
            'total_amount': cls._format_kes(contribution.amount),
            'platform_fee': 'KSh 0.00',
            'net_amount': cls._format_kes(contribution.amount),
            'transaction_ref': str(contribution.id)[:8].upper(),
            'description': f'Contribution to {chama_name}',
            'verification_code': verification_code,
        }

        pdf_content = cls._build_pdf(receipt_data, verification_code)

        receipt = Receipt.objects.create(
            receipt_number=receipt_number,
            receipt_type=ReceiptType.CHAMA_CONTRIBUTION,
            user=user,
            contribution=contribution,
            amount=contribution.amount,
            description=f'Contribution to {chama_name}',
            party_name=chama_name,
            verification_code=verification_code,
        )

        filename = f"receipt_{receipt_number}.pdf"
        try:
            receipt.pdf_file.save(filename, ContentFile(pdf_content), save=True)
            logger.info(f"Contribution receipt PDF saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save contribution receipt PDF {filename}: {str(e)}", exc_info=True)
        logger.info(f"Contribution receipt generated: {receipt_number}")

        return receipt

    @classmethod
    def generate_loan_repayment_receipt(cls, repayment, user, chama_name):
        receipt_number = cls._generate_receipt_number()
        verification_code = cls._generate_verification_code(
            str(repayment.id), str(user.id)
        )

        receipt_data = {
            'receipt_number': receipt_number,
            'date': repayment.paid_at.strftime('%d %B %Y'),
            'time': repayment.paid_at.strftime('%H:%M'),
            'title': 'Loan Repayment Receipt',
            'user_name': user.get_full_name(),
            'user_email': user.email,
            'user_phone': user.phone_number,
            'party_name': chama_name,
            'sacco_name': '',
            'shares': '',
            'price_per_share': '',
            'total_amount': cls._format_kes(repayment.amount),
            'platform_fee': 'KSh 0.00',
            'net_amount': cls._format_kes(repayment.amount),
            'transaction_ref': str(repayment.id)[:8].upper(),
            'description': f'Loan repayment to {chama_name}',
            'verification_code': verification_code,
        }

        pdf_content = cls._build_pdf(receipt_data, verification_code)

        receipt = Receipt.objects.create(
            receipt_number=receipt_number,
            receipt_type=ReceiptType.LOAN_REPAYMENT,
            user=user,
            loan_repayment=repayment,
            amount=repayment.amount,
            description=f'Loan repayment to {chama_name}',
            party_name=chama_name,
            verification_code=verification_code,
        )

        filename = f"receipt_{receipt_number}.pdf"
        try:
            receipt.pdf_file.save(filename, ContentFile(pdf_content), save=True)
            logger.info(f"Loan repayment receipt PDF saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save loan repayment receipt PDF {filename}: {str(e)}", exc_info=True)

        logger.info(f"Loan repayment receipt generated: {receipt_number}")

        return receipt

    @classmethod
    def _build_pdf(cls, data, verification_code):
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A5,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'ReceiptTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=DEEP_CLAY,
            alignment=TA_CENTER,
            spaceAfter=2*mm,
        )

        receipt_no_style = ParagraphStyle(
            'ReceiptNo',
            parent=styles['Normal'],
            fontSize=9,
            textColor=TEXT_MEDIUM,
            alignment=TA_CENTER,
            spaceAfter=6*mm,
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=11,
            textColor=TERRACOTTA,
            spaceBefore=5*mm,
            spaceAfter=3*mm,
        )

        normal_style = ParagraphStyle(
            'ReceiptNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=TEXT_DARK,
            leading=14,
        )

        small_style = ParagraphStyle(
            'ReceiptSmall',
            parent=styles['Normal'],
            fontSize=8,
            textColor=TEXT_MEDIUM,
            alignment=TA_CENTER,
        )

        elements = []

        # Header
        elements.append(Paragraph("SACCO BRIDGE", title_style))
        elements.append(Paragraph(f"Receipt No: {data['receipt_number']}", receipt_no_style))
        elements.append(Paragraph(data['title'], ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=COOL_SLATE,
            alignment=TA_CENTER,
            spaceAfter=6*mm,
        )))

        # Separator line
        elements.append(cls._create_separator())

        # Transaction details
        elements.append(Paragraph("TRANSACTION DETAILS", section_style))

        detail_data = [
            ['Date:', data['date']],
            ['Time:', data['time']],
            ['Reference:', data['transaction_ref']],
            ['Description:', data['description']],
        ]

        if data['sacco_name']:
            detail_data.append(['SACCO:', data['sacco_name']])
        if data['shares']:
            detail_data.append(['Shares:', data['shares']])
        if data['price_per_share']:
            detail_data.append(['Price/Share:', data['price_per_share']])

        detail_table = Table(detail_data, colWidths=[35*mm, 85*mm])
        detail_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), TEXT_MEDIUM),
            ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(detail_table)
        elements.append(Spacer(1, 3*mm))

        # Amount summary
        elements.append(Paragraph("AMOUNT SUMMARY", section_style))

        amount_data = [
            ['Total Amount:', data['total_amount']],
            ['Platform Fee:', data['platform_fee']],
            ['Net Amount:', data['net_amount']],
        ]

        amount_table = Table(amount_data, colWidths=[35*mm, 85*mm])
        amount_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), TEXT_MEDIUM),
            ('TEXTCOLOR', (1, 0), (1, -1), DEEP_CLAY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, -1), (-1, -1), 1, TERRACOTTA),
        ]))
        elements.append(amount_table)
        elements.append(Spacer(1, 3*mm))

        # Parties
        elements.append(Paragraph("PARTIES", section_style))

        party_data = [
            ['Issued To:', data['user_name']],
            ['Email:', data['user_email']],
            ['Phone:', data['user_phone']],
            ['', ''],
            ['Counterparty:', data['party_name']],
        ]

        party_table = Table(party_data, colWidths=[35*mm, 85*mm])
        party_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), TEXT_MEDIUM),
            ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(party_table)

        # QR Code for verification
        elements.append(Spacer(1, 5*mm))
        qr_image = cls._generate_qr_code(verification_code)
        elements.append(qr_image)
        elements.append(Paragraph(
            "Scan to verify this receipt on Sacco Bridge",
            small_style
        ))

        # Footer
        elements.append(Spacer(1, 6*mm))
        elements.append(cls._create_separator())
        elements.append(Paragraph(
            "Sacco Bridge - Your Circle. Guaranteed.",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=TEXT_MEDIUM,
                alignment=TA_CENTER,
            )
        ))
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}",
            small_style
        ))

        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    @classmethod
    def _create_separator(cls):
        d = Drawing(120*mm, 1)
        d.add(Rect(0, 0, 120*mm, 0.5, fillColor=BORDER_GRAY, strokeColor=None))
        return d

    @classmethod
    def _generate_qr_code(cls, verification_code):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=3,
            border=2,
        )
        qr.add_data(f"https://saccobridge.co.ke/verify/{verification_code}")
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color='#C67B5C', back_color='white')

        # Convert to bytes for ReportLab
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        img = Image(img_buffer, width=25*mm, height=25*mm)
        return img

    @classmethod
    def _generate_receipt_number(cls):
        now = timezone.now()
        date_part = now.strftime('%Y%m%d')
        random_part = os.urandom(3).hex().upper()
        return f"RCP-{date_part}-{random_part}"

    @classmethod
    def _generate_verification_code(cls, *args):
        combined = '|'.join(str(arg) for arg in args)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    @classmethod
    def _format_kes(cls, amount):
        if amount is None:
            return 'KSh 0.00'
        amount = Decimal(str(amount))
        parts = f"{amount:,.2f}".split('.')
        return f"KSh {parts[0]}.{parts[1]}"