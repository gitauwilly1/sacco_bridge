import base64
import logging
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.mpesa.models import (
    MpesaTransaction,
    MpesaTransactionStatus,
    MpesaTransactionType,
)

logger = logging.getLogger(__name__)


class MpesaService:

    @classmethod
    def _get_auth_url(cls):
        env = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        if env == 'production':
            return 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        return 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    @classmethod
    def _get_stk_url(cls):
        env = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        if env == 'production':
            return 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        return 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'

    @classmethod
    def _get_query_url(cls):
        env = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        if env == 'production':
            return 'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'
        return 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'

    @classmethod
    def get_access_token(cls):
        try:
            consumer_key = settings.MPESA_CONSUMER_KEY
            consumer_secret = settings.MPESA_CONSUMER_SECRET

            auth_string = f"{consumer_key}:{consumer_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            response = requests.get(
                cls._get_auth_url(),
                headers={'Authorization': f'Basic {encoded_auth}'},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            else:
                logger.error(
                    f"Failed to get M-Pesa token. "
                    f"Status: {response.status_code}, Body: {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting M-Pesa access token: {str(e)}")
            return None

    @classmethod
    def initiate_stk_push(
        cls,
        phone_number,
        amount,
        account_reference,
        transaction_desc,
        callback_url=None
    ):
        access_token = cls.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to obtain access token.'}

        try:
            shortcode = settings.MPESA_SHORTCODE
            passkey = settings.MPESA_PASSKEY
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_string = f"{shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()

            formatted_phone = cls.format_phone_number(phone_number)

            if callback_url is None:
                callback_url = getattr(
                    settings,
                    'MPESA_CALLBACK_URL',
                    'https://api.saccobridge.co.ke/api/v1/mpesa/callback/'
                )

            payload = {
                'BusinessShortCode': shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(Decimal(str(amount))),
                'PartyA': formatted_phone,
                'PartyB': shortcode,
                'PhoneNumber': formatted_phone,
                'CallBackURL': callback_url,
                'AccountReference': account_reference[:12],
                'TransactionDesc': transaction_desc[:13],
            }

            response = requests.post(
                cls._get_stk_url(),
                json=payload,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                },
                timeout=30
            )

            data = response.json()
            logger.info(f"M-Pesa STK Push response: {data}")

            if response.status_code == 200:
                response_code = data.get('ResponseCode', '')
                if response_code == '0':
                    return {
                        'success': True,
                        'data': data,
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'data': data,
                        'error': data.get('ResponseDescription', 'STK Push failed.')
                    }
            else:
                return {
                    'success': False,
                    'data': data,
                    'error': data.get('errorMessage', 'STK Push request failed.')
                }

        except Exception as e:
            logger.error(f"STK Push error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    @classmethod
    def query_stk_status(cls, checkout_request_id):
        access_token = cls.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to obtain access token.'}

        try:
            shortcode = settings.MPESA_SHORTCODE
            passkey = settings.MPESA_PASSKEY
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_string = f"{shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()

            payload = {
                'BusinessShortCode': shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id,
            }

            response = requests.post(
                cls._get_query_url(),
                json=payload,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                },
                timeout=30
            )

            data = response.json()
            logger.info(f"M-Pesa query response: {data}")
            return {'success': True, 'data': data}

        except Exception as e:
            logger.error(f"STK query error: {str(e)}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def process_callback(cls, callback_data):
        try:
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})

            checkout_request_id = stk_callback.get('CheckoutRequestID', '')
            result_code = stk_callback.get('ResultCode', 1)
            result_desc = stk_callback.get('ResultDesc', '')

            if not checkout_request_id:
                logger.error("Callback missing CheckoutRequestID")
                return {
                    'success': False,
                    'error': 'Missing CheckoutRequestID'
                }

            with db_transaction.atomic():
                try:
                    transaction = MpesaTransaction.objects.select_for_update().get(
                        checkout_request_id=checkout_request_id
                    )
                except MpesaTransaction.DoesNotExist:
                    logger.error(f"No transaction found for CheckoutRequestID: {checkout_request_id}")
                    return {
                        'success': False,
                        'error': 'Transaction not found.',
                        'checkout_request_id': checkout_request_id
                    }

                # Idempotency check: if transaction is already in terminal state, return safely without duplicate side effects
                if transaction.status == MpesaTransactionStatus.COMPLETED:
                    logger.info(
                        f"Transaction {transaction.transaction_id} already completed. "
                        f"Idempotently skipping callback processing."
                    )
                    return {
                        'success': True,
                        'message': 'Transaction already completed.',
                        'receipt': transaction.mpesa_receipt_number,
                        'transaction_id': str(transaction.transaction_id),
                        'idempotent': True
                    }
                elif transaction.status in [MpesaTransactionStatus.FAILED, MpesaTransactionStatus.CANCELLED, MpesaTransactionStatus.TIMEOUT]:
                    logger.info(
                        f"Transaction {transaction.transaction_id} is already in terminal state: {transaction.status}."
                    )
                    return {
                        'success': False,
                        'error': f'Transaction already in terminal state: {transaction.status}',
                        'transaction_id': str(transaction.transaction_id),
                        'idempotent': True
                    }

                if result_code == 0:
                    # Payment successful
                    callback_metadata = stk_callback.get('CallbackMetadata', {})
                    items = callback_metadata.get('Item', [])

                    mpesa_receipt = ''
                    callback_amount = None

                    for item in items:
                        name = item.get('Name')
                        val = item.get('Value')
                        if name == 'MpesaReceiptNumber':
                            mpesa_receipt = str(val) if val is not None else ''
                        elif name == 'Amount':
                            try:
                                callback_amount = Decimal(str(val))
                            except Exception:
                                callback_amount = None

                    # Check for duplicate receipt on another completed transaction
                    if mpesa_receipt and MpesaTransaction.objects.exclude(pk=transaction.pk).filter(
                        mpesa_receipt_number=mpesa_receipt,
                        status=MpesaTransactionStatus.COMPLETED
                    ).exists():
                        err_msg = f"Duplicate M-Pesa receipt detected: {mpesa_receipt}"
                        logger.warning(err_msg)
                        transaction.mark_failed(err_msg, callback_data)
                        return {
                            'success': False,
                            'error': err_msg,
                            'transaction_id': str(transaction.transaction_id)
                        }

                    # Mark transaction completed
                    transaction.mark_completed(mpesa_receipt, callback_data)

                    # Wire Settlement / Escrow routing if settlement is linked
                    if transaction.settlement:
                        settlement = transaction.settlement
                        expected_amount = settlement.amount

                        from apps.transactions.models import (
                            Dispute,
                            DisputeReason,
                            DisputeStatus,
                            SettlementEventTrigger,
                            SettlementState,
                        )
                        from apps.transactions.services import SettlementService

                        # Check for amount mismatch
                        if callback_amount is not None and callback_amount != expected_amount:
                            logger.warning(
                                f"Settlement amount mismatch for {settlement.uuid}: "
                                f"expected KSh {expected_amount}, received KSh {callback_amount}. Raising dispute."
                            )

                            # Create formal dispute record
                            Dispute.objects.get_or_create(
                                settlement=settlement,
                                raised_by=transaction.user,
                                defaults={
                                    'reason': DisputeReason.WRONG_AMOUNT,
                                    'description': (
                                        f"M-Pesa payment amount mismatch. "
                                        f"Expected KSh {expected_amount}, received KSh {callback_amount}. "
                                        f"Receipt: {mpesa_receipt}."
                                    ),
                                    'status': DisputeStatus.OPEN
                                }
                            )

                            # Transition settlement state to disputed
                            if hasattr(settlement, 'transition_to'):
                                settlement.transition_to(
                                    SettlementState.DISPUTED_MANUAL,
                                    SettlementEventTrigger.BUYER_SACCO_FAILURE,
                                    metadata={
                                        'error': 'AMOUNT_MISMATCH',
                                        'expected_amount': str(expected_amount),
                                        'received_amount': str(callback_amount),
                                        'mpesa_receipt': mpesa_receipt
                                    }
                                )

                            # Mark escrow account disputed if attached
                            if hasattr(settlement, 'escrow') and settlement.escrow:
                                settlement.escrow.mark_disputed()

                        else:
                            # Amounts match: ensure state is BUYER_DEBIT_INITIATED before debit confirmation
                            if settlement.state == SettlementState.INTENT_LOCKED:
                                settlement.transition_to(
                                    SettlementState.BUYER_DEBIT_INITIATED,
                                    SettlementEventTrigger.INTENT_CREATED
                                )

                            SettlementService.process_buyer_debit(
                                settlement,
                                {'status': 'SUCCESS', 'transaction_id': mpesa_receipt}
                            )

                            # Mark escrow funded if attached
                            if hasattr(settlement, 'escrow') and settlement.escrow:
                                settlement.escrow.mark_funded(buyer_ref=mpesa_receipt)

                    logger.info(
                        f"M-Pesa payment completed: {mpesa_receipt} "
                        f"for transaction {transaction.transaction_id}"
                    )

                    return {
                        'success': True,
                        'message': 'Payment processed successfully.',
                        'receipt': mpesa_receipt,
                        'transaction_id': str(transaction.transaction_id)
                    }

                else:
                    # Payment failed
                    transaction.mark_failed(result_desc, callback_data)

                    # If linked to a settlement, notify settlement of failure
                    if transaction.settlement:
                        from apps.transactions.services import SettlementService
                        SettlementService.process_buyer_debit(
                            transaction.settlement,
                            {'status': 'FAILURE', 'error_code': 'MPESA_PAYMENT_FAILED'}
                        )

                    logger.warning(
                        f"M-Pesa payment failed: {result_desc} "
                        f"for transaction {transaction.transaction_id}"
                    )

                    return {
                        'success': False,
                        'error': result_desc,
                        'transaction_id': str(transaction.transaction_id)
                    }

        except Exception as e:
            logger.error(f"Callback processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def format_phone_number(cls, phone):
        phone = str(phone).strip().replace(' ', '').replace('-', '')

        if phone.startswith('+254'):
            return phone[1:]
        elif phone.startswith('0'):
            return '254' + phone[1:]
        elif phone.startswith('254'):
            return phone
        else:
            return '254' + phone
