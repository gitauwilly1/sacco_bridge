import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import AuthenticationFailed as DRFAuthenticationFailed, PermissionDenied as DRFPermissionDenied, NotAuthenticated as DRFNotAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class SaccoBridgeException(Exception):

    def __init__(self, message, code=None, status_code=None):
        self.message = message
        self.code = code or 'error'
        self.status_code = status_code or status.HTTP_400_BAD_REQUEST
        super().__init__(self.message)


class InsufficientFundsError(SaccoBridgeException):

    def __init__(self, message="Insufficient funds to complete the transaction."):
        super().__init__(message=message, code='insufficient_funds', status_code=status.HTTP_402_PAYMENT_REQUIRED)


class SettlementError(SaccoBridgeException):

    def __init__(self, message="Settlement failed.", settlement_id=None):
        self.settlement_id = settlement_id
        detail = f"{message} Settlement ID: {settlement_id}" if settlement_id else message
        super().__init__(message=detail, code='settlement_error', status_code=status.HTTP_409_CONFLICT)


class VerificationError(SaccoBridgeException):

    def __init__(self, message="Verification failed."):
        super().__init__(message=message, code='verification_error', status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ChamaMembershipError(SaccoBridgeException):

    def __init__(self, message="Chama membership error."):
        super().__init__(message=message, code='chama_membership_error', status_code=status.HTTP_403_FORBIDDEN)


class LoanEligibilityError(SaccoBridgeException):

    def __init__(self, message="Member is not eligible for a loan."):
        super().__init__(message=message, code='loan_eligibility_error', status_code=status.HTTP_403_FORBIDDEN)


class DuplicateRequestError(SaccoBridgeException):

    def __init__(self, message="This request has already been processed."):
        super().__init__(message=message, code='duplicate_request', status_code=status.HTTP_409_CONFLICT)


class AuthenticationFailedError(SaccoBridgeException):

    def __init__(self, message="Authentication failed."):
        super().__init__(message=message, code='authentication_failed', status_code=status.HTTP_401_UNAUTHORIZED)


class PermissionDeniedError(SaccoBridgeException):

    def __init__(self, message="You do not have permission to perform this action."):
        super().__init__(message=message, code='permission_denied', status_code=status.HTTP_403_FORBIDDEN)


def custom_exception_handler(exc, context):
    
    # Handle DRF AuthenticationFailed (returns 401)
    if isinstance(exc, DRFAuthenticationFailed):
        return Response(
            {
                'success': False,
                'error': {
                    'code': getattr(exc.detail, 'code', 'authentication_failed') if hasattr(exc.detail, 'code') else 'authentication_failed',
                    'message': str(exc.detail) if not hasattr(exc.detail, 'code') else str(exc.detail),
                },
                'meta': {
                    'timestamp': str(timezone.now()),
                }
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Handle DRF NotAuthenticated
    if isinstance(exc, DRFNotAuthenticated):
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'authentication_required',
                    'message': str(exc.detail),
                },
                'meta': {
                    'timestamp': str(timezone.now()),
                }
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Handle DRF PermissionDenied
    if isinstance(exc, DRFPermissionDenied):
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': str(exc.detail),
                },
                'meta': {
                    'timestamp': str(timezone.now()),
                }
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Handle SaccoBridge custom exceptions
    if isinstance(exc, SaccoBridgeException):
        return Response(
            {
                'success': False,
                'error': {
                    'code': exc.code,
                    'message': exc.message,
                },
                'meta': {
                    'timestamp': str(timezone.now()),
                }
            },
            status=exc.status_code
        )

    # Handle standard DRF exceptions
    response = exception_handler(exc, context)

    if response is not None:
        errors = []
        request_id = getattr(context.get('request'), 'request_id', None)

        status_code_map = {
            400: 'validation_error',
            401: 'authentication_failed',
            403: 'permission_denied',
            404: 'not_found',
            405: 'method_not_allowed',
            409: 'conflict',
            429: 'rate_limit_exceeded',
            500: 'server_error',
        }
        error_code = status_code_map.get(response.status_code, 'error')

        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if isinstance(value, list):
                    for item in value:
                        errors.append({
                            'field': key,
                            'message': str(item),
                            'code': response.status_code
                        })
                elif key == 'detail':
                    errors.append({
                        'field': 'detail',
                        'message': str(value),
                        'code': response.status_code
                    })
                else:
                    errors.append({
                        'field': key,
                        'message': str(value),
                        'code': response.status_code
                    })
        elif isinstance(response.data, list):
            for item in response.data:
                errors.append({
                    'field': 'non_field_errors',
                    'message': str(item),
                    'code': response.status_code
                })

        response.data = {
            'success': False,
            'error': {
                'code': error_code,
                'message': 'Request failed.',
                'details': errors,
            },
            'meta': {
                'request_id': request_id,
                'timestamp': str(timezone.now()),
            }
        }

    # In production, don't expose stack traces
    if not settings.DEBUG:
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'server_error',
                    'message': 'An unexpected error occurred. Our team has been notified.',
                },
                'meta': {
                    'timestamp': str(timezone.now()),
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response