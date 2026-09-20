import uuid
from decimal import Decimal
import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.tests.factories import (
    ChamaFactory,
    ChamaMemberFactory,
    ContributionFactory,
    SettlementIntentFactory,
    UserFactory,
)
from apps.escrow.models import EscrowAccount, EscrowStatus
from apps.mpesa.models import (
    MpesaTransaction,
    MpesaTransactionStatus,
    MpesaTransactionType,
)
from apps.mpesa.services import MpesaService
from apps.transactions.models import (
    Dispute,
    DisputeReason,
    DisputeStatus,
    SettlementState,
)


def create_stk_callback_payload(checkout_request_id, result_code=0, result_desc="The service request is processed successfully.", receipt="NLJ7RT61SV", amount=1000, phone="254712345678"):
    if result_code == 0:
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": f"MR_{uuid.uuid4().hex[:8]}",
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": 0,
                    "ResultDesc": result_desc,
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": amount},
                            {"Name": "MpesaReceiptNumber", "Value": receipt},
                            {"Name": "TransactionDate", "Value": 20260920120000},
                            {"Name": "PhoneNumber", "Value": phone}
                        ]
                    }
                }
            }
        }
    else:
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": f"MR_{uuid.uuid4().hex[:8]}",
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": result_code,
                    "ResultDesc": result_desc
                }
            }
        }


@pytest.mark.django_db
class TestMpesaCallbackProcessing:

    def setup_method(self):
        self.user = UserFactory()
        self.chama = ChamaFactory()
        self.member = ChamaMemberFactory(chama=self.chama, user=self.user)
        self.contribution = ContributionFactory(chama=self.chama, member=self.member, amount=Decimal('1000.00'), status='PENDING')
        self.client = APIClient()

    def test_successful_callback_marks_completed_and_pays_contribution(self):
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            contribution=self.contribution,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_SUCCESS_1',
            amount=1000
        )

        res = MpesaService.process_callback(payload)
        assert res['success'] is True
        assert res['receipt'] == 'REC_SUCCESS_1'

        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.COMPLETED
        assert transaction.mpesa_receipt_number == 'REC_SUCCESS_1'
        assert transaction.completed_at is not None

        self.contribution.refresh_from_db()
        assert self.contribution.status == 'PAID'

    def test_idempotent_duplicate_callback_does_not_reprocess(self):
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            contribution=self.contribution,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_IDEMPOTENT_1',
            amount=1000
        )

        # First callback invocation
        res1 = MpesaService.process_callback(payload)
        assert res1['success'] is True

        transaction.refresh_from_db()
        completed_time = transaction.completed_at
        assert transaction.status == MpesaTransactionStatus.COMPLETED

        # Second identical callback invocation (simulating network duplicate)
        res2 = MpesaService.process_callback(payload)
        assert res2['success'] is True
        assert res2.get('idempotent') is True

        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.COMPLETED
        assert transaction.completed_at == completed_time

    def test_failed_callback_marks_transaction_failed(self):
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=1032,
            result_desc="Request cancelled by user"
        )

        res = MpesaService.process_callback(payload)
        assert res['success'] is False
        assert 'Request cancelled by user' in res['error']

        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.FAILED
        assert transaction.error_message == 'Request cancelled by user'
        assert transaction.failed_at is not None

    def test_settlement_reconciliation_exact_amount_funds_escrow(self):
        buyer = self.user
        seller = UserFactory()
        settlement = SettlementIntentFactory(
            buyer=buyer,
            seller=seller,
            amount=Decimal('50000.00'),
            state=SettlementState.INTENT_LOCKED
        )
        escrow = EscrowAccount.objects.create(
            settlement=settlement,
            buyer=buyer,
            seller=seller,
            amount=Decimal('50000.00'),
            status=EscrowStatus.CREATED
        )

        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=buyer,
            settlement=settlement,
            transaction_type=MpesaTransactionType.SHARE_PURCHASE,
            phone_number='254712345678',
            amount=Decimal('50000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_SETTLE_EXACT',
            amount=50000
        )

        res = MpesaService.process_callback(payload)
        assert res['success'] is True

        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.COMPLETED

        settlement.refresh_from_db()
        assert settlement.state == SettlementState.BUYER_DEBIT_CONFIRMED
        assert settlement.buyer_debit_ref == 'REC_SETTLE_EXACT'

        escrow.refresh_from_db()
        assert escrow.status == EscrowStatus.FUNDED
        assert escrow.buyer_ref == 'REC_SETTLE_EXACT'

    def test_settlement_reconciliation_mismatch_amount_creates_dispute_and_holds_escrow(self):
        buyer = self.user
        seller = UserFactory()
        settlement = SettlementIntentFactory(
            buyer=buyer,
            seller=seller,
            amount=Decimal('50000.00'),
            state=SettlementState.INTENT_LOCKED
        )
        escrow = EscrowAccount.objects.create(
            settlement=settlement,
            buyer=buyer,
            seller=seller,
            amount=Decimal('50000.00'),
            status=EscrowStatus.CREATED
        )

        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=buyer,
            settlement=settlement,
            transaction_type=MpesaTransactionType.SHARE_PURCHASE,
            phone_number='254712345678',
            amount=Decimal('50000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        # M-Pesa callback provides only 25,000 instead of expected 50,000
        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_SETTLE_MISMATCH',
            amount=25000
        )

        res = MpesaService.process_callback(payload)
        assert res['success'] is True

        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.COMPLETED

        # Check Dispute was created
        dispute = Dispute.objects.filter(settlement=settlement, raised_by=buyer).first()
        assert dispute is not None
        assert dispute.reason == DisputeReason.WRONG_AMOUNT
        assert dispute.status == DisputeStatus.OPEN
        assert "Expected KSh 50000.00, received KSh 25000" in dispute.description

        settlement.refresh_from_db()
        assert settlement.state == SettlementState.DISPUTED_MANUAL

        escrow.refresh_from_db()
        assert escrow.status == EscrowStatus.DISPUTED

    def test_duplicate_receipt_across_different_transactions_fails(self):
        # Transaction 1 completes with receipt REC_SHARED_100
        checkout1 = f"ws_CO_{uuid.uuid4().hex[:12]}"
        tx1 = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout1,
            status=MpesaTransactionStatus.INITIATED
        )
        p1 = create_stk_callback_payload(checkout_request_id=checkout1, result_code=0, receipt='REC_SHARED_100')
        res1 = MpesaService.process_callback(p1)
        assert res1['success'] is True

        # Transaction 2 tries to complete with the same receipt REC_SHARED_100
        checkout2 = f"ws_CO_{uuid.uuid4().hex[:12]}"
        tx2 = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout2,
            status=MpesaTransactionStatus.INITIATED
        )
        p2 = create_stk_callback_payload(checkout_request_id=checkout2, result_code=0, receipt='REC_SHARED_100')
        res2 = MpesaService.process_callback(p2)

        assert res2['success'] is False
        assert "Duplicate M-Pesa receipt detected" in res2['error']

        tx2.refresh_from_db()
        assert tx2.status == MpesaTransactionStatus.FAILED

    def test_unknown_checkout_request_id_returns_error(self):
        payload = create_stk_callback_payload(
            checkout_request_id='non_existent_checkout_id',
            result_code=0,
            receipt='REC_NONE'
        )
        res = MpesaService.process_callback(payload)
        assert res['success'] is False
        assert res['error'] == 'Transaction not found.'

    @override_settings(MPESA_ENFORCE_IP_ALLOWLIST=True, MPESA_ALLOW_DEV_IPS=False)
    def test_callback_endpoint_rejects_untrusted_ip_silently(self):
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_SPOOFED_IP',
            amount=1000
        )

        # Attacker IP (e.g. 45.33.32.156)
        response = self.client.post(
            reverse('mpesa-callback'),
            payload,
            format='json',
            REMOTE_ADDR='45.33.32.156'
        )

        # Returns silent 200 OK to avoid disclosing rejection
        assert response.status_code == 200
        assert response.data['ResultCode'] == 0

        # Transaction was NOT processed
        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.INITIATED
        assert transaction.mpesa_receipt_number == ''

    @override_settings(MPESA_CALLBACK_SECRET='super-secret-safaricom-token-2026', MPESA_ENFORCE_IP_ALLOWLIST=False)
    def test_callback_endpoint_rejects_missing_or_wrong_secret_token(self):
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_WRONG_TOKEN',
            amount=1000
        )

        # 1. No secret passed
        response1 = self.client.post(reverse('mpesa-callback'), payload, format='json')
        assert response1.status_code == 200
        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.INITIATED

        # 2. Invalid secret passed
        response2 = self.client.post(
            reverse('mpesa-callback') + '?token=invalid-token',
            payload,
            format='json'
        )
        assert response2.status_code == 200
        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.INITIATED

    @override_settings(MPESA_CALLBACK_SECRET='super-secret-safaricom-token-2026', MPESA_ENFORCE_IP_ALLOWLIST=True)
    def test_callback_endpoint_accepts_valid_safaricom_ip_and_matching_secret(self):
        checkout_id = f"ws_CO_{uuid.uuid4().hex[:12]}"
        transaction = MpesaTransaction.objects.create(
            user=self.user,
            chama=self.chama,
            contribution=self.contribution,
            transaction_type=MpesaTransactionType.CHAMA_CONTRIBUTION,
            phone_number='254712345678',
            amount=Decimal('1000.00'),
            checkout_request_id=checkout_id,
            status=MpesaTransactionStatus.INITIATED
        )

        payload = create_stk_callback_payload(
            checkout_request_id=checkout_id,
            result_code=0,
            receipt='REC_AUTH_SUCCESS',
            amount=1000
        )

        # Request from legitimate Safaricom IP (196.201.214.20) with valid secret header
        response = self.client.post(
            reverse('mpesa-callback-secret', kwargs={'secret_key': 'super-secret-safaricom-token-2026'}),
            payload,
            format='json',
            REMOTE_ADDR='196.201.214.20'
        )

        assert response.status_code == 200
        assert response.data['ResultCode'] == 0

        transaction.refresh_from_db()
        assert transaction.status == MpesaTransactionStatus.COMPLETED
        assert transaction.mpesa_receipt_number == 'REC_AUTH_SUCCESS'
        self.contribution.refresh_from_db()
        assert self.contribution.status == 'PAID'
