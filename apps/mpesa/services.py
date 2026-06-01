import logging
import base64
import requests
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from apps.mpesa.models import MpesaTransaction, MpesaTransactionStatus

logger = logging.getLogger(__name__)


class MpesaService:

    # Safaricom API endpoints
    SANDBOX_AUTH_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    PRODUCTION_AUTH_URL = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    SANDBOX_STK_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    PRODUCTION_STK_URL = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'

    SANDBOX_QUERY_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'
    PRODUCTION_QUERY_URL = 'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'

    ACCESS_TOKEN_CACHE_KEY = 'mpesa_access_token'
    ACCESS_TOKEN_CACHE_TIMEOUT = 3500  # 58 minutes (token expires in 60)

    @classmethod
    def _get_auth_url(cls):
        if settings.DEBUG:
            return cls.SANDBOX_AUTH_URL
        return cls.PRODUCTION_AUTH_URL

    @classmethod
    def _get_stk_url(cls):
        if settings.DEBUG:
            return cls.SANDBOX_STK_URL
        return cls.PRODUCTION_STK_URL

    @classmethod
    def _get_query_url(cls):
        if settings.DEBUG:
            return cls.SANDBOX_QUERY_URL
        return cls.PRODUCTION_QUERY_URL

    @classmethod
    def get_access_token(cls):
        cached_token = cache.get(cls.ACCESS_TOKEN_CACHE_KEY)
        if cached_token:
            return cached_token

        try:
            consumer_key = settings.MPESA_CONSUMER_KEY
            consumer_secret = settings.MPESA_CONSUMER_SECRET

            auth_string = base64.b64encode(
                f"{consumer_key}:{consumer_secret}".encode()
            ).decode()

            response = requests.get(
                cls._get_auth_url(),
                headers={
                    'Authorization': f'Basic {auth_string}'
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')

                if access_token:
                    cache.set(
                        cls.ACCESS_TOKEN_CACHE_KEY,
                        access_token,
                        cls.ACCESS_TOKEN_CACHE_TIMEOUT
                    )
                    logger.info("M-Pesa access token obtained successfully")
                    return access_token

            logger.error(f"Failed to get M-Pesa access token: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error getting M-Pesa access token: {str(e)}")
            return None

    @classmethod
    def initiate_stk_push(cls, phone_number, amount, account_reference, transaction_desc):
        access_token = cls.get_access_token()
        if not access_token:
            return {
                'success': False,
                'error': 'Failed to obtain M-Pesa access token.',
                'data': None
            }

        try:
            shortcode = settings.MPESA_SHORTCODE
            passkey = settings.MPESA_PASSKEY
            callback_url = settings.MPESA_CALLBACK_URL

            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

            # Generate password
            password_string = f"{shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()

            payload = {
                'BusinessShortCode': shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': str(int(amount)),
                'PartyA': phone_number,
                'PartyB': shortcode,
                'PhoneNumber': phone_number,
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

            merchant_request_id = stk_callback.get('MerchantRequestID', '')
            checkout_request_id = stk_callback.get('CheckoutRequestID', '')
            result_code = stk_callback.get('ResultCode', 1)
            result_desc = stk_callback.get('ResultDesc', '')

            try:
                transaction = MpesaTransaction.objects.get(
                    checkout_request_id=checkout_request_id
                )
            except MpesaTransaction.DoesNotExist:
                logger.error(f"No transaction found for CheckoutRequestID: {checkout_request_id}")
                return {
                    'success': False,
                    'error': 'Transaction not found.',
                    'checkout_request_id': checkout_request_id
                }

            if result_code == 0:
                # Payment successful
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])

                mpesa_receipt = ''
                amount = None
                phone = ''

                for item in items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt = item.get('Value', '')
                    elif item.get('Name') == 'Amount':
                        amount = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone = item.get('Value')

                transaction.mark_completed(mpesa_receipt, callback_data)

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
        phone = phone.strip().replace(' ', '').replace('-', '')

        if phone.startswith('+254'):
            return phone[1:]
        elif phone.startswith('0'):
            return '254' + phone[1:]
        elif phone.startswith('254'):
            return phone
        else:
            return '254' + phone