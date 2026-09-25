"""Tests for ReceiptPDFGenerator service and formatting/audit helpers."""
from decimal import Decimal
import pytest
from apps.core.tests.factories import UserFactory, ChamaFactory, ChamaMemberFactory, ContributionFactory
from apps.receipts.services import ReceiptPDFGenerator


@pytest.mark.django_db
class TestReceiptPDFGenerator:
    def test_format_kes_helper(self):
        assert ReceiptPDFGenerator._format_kes(Decimal("1250000.00")) == "KSh 1,250,000.00"
        assert ReceiptPDFGenerator._format_kes(Decimal("0.00")) == "KSh 0.00"
        assert ReceiptPDFGenerator._format_kes(Decimal("4500.50")) == "KSh 4,500.50"
        assert ReceiptPDFGenerator._format_kes(None) == "KSh 0.00"

    def test_generate_receipt_number_format_and_uniqueness(self):
        num1 = ReceiptPDFGenerator._generate_receipt_number()
        num2 = ReceiptPDFGenerator._generate_receipt_number()
        assert num1.startswith("RCP-")
        assert num2.startswith("RCP-")
        assert num1 != num2

    def test_generate_verification_code_sha256_length(self):
        code1 = ReceiptPDFGenerator._generate_verification_code("arg1", "arg2", 123)
        code2 = ReceiptPDFGenerator._generate_verification_code("arg1", "arg2", 123)
        assert len(code1) == 16
        assert code1 == code2

    def test_generate_contribution_receipt_pdf(self):
        user = UserFactory(first_name="Alice", last_name="Wanjiku")
        chama = ChamaFactory(name="Ufanisi Women Group")
        member = ChamaMemberFactory(user=user, chama=chama)
        contribution = ContributionFactory(member=member, chama=chama, amount=Decimal("5000.00"))

        receipt = ReceiptPDFGenerator.generate_contribution_receipt(
            contribution=contribution,
            user=user,
            chama_name=chama.name,
        )

        assert receipt is not None
        assert hasattr(receipt, 'pdf_file')
        assert receipt.receipt_number.startswith("RCP-")
