import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404

logger = logging.getLogger(__name__)


class SaccoBridgeException(Exception):
    def __init__(self, message, code=None, status_code=None):
        self.message = message
        self.code = code or 'error'
        self.status_code = status_code or status.HTTP_400_BAD_REQUEST
        super().__init__(self.message)


class InsufficientFundsError(SaccoBridgeException):

    def __init__(self, message="Insufficient funds to complete the transaction."):
        super().__init__(
            message=message,
            code='insufficient_funds',
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )


class SettlementError(SaccoBridgeException):

    def __init__(self, message="Settlement failed.", settlement_id=None):
        self.settlement_id = settlement_id
        detail = message
        if settlement_id:
            detail = f"{message} Settlement ID: {settlement_id}"
        super().__init__(
            message=detail,
            code='settlement_error',
            status_code=status.HTTP_409_CONFLICT
        )


class VerificationError(SaccoBridgeException):

    def __init__(self, message="Verification failed."):
        super().__init__(
            message=message,
            code='verification_error',
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class ChamaMembershipError(SaccoBridgeException):

    def __init__(self, message="Chama membership error."):
        super().__init__(
            message=message,
            code='chama_membership_error',
            status_code=status.HTTP_403_FORBIDDEN
        )


class LoanEligibilityError(SaccoBridgeException):

    def __init__(self, message="Member is not eligible for a loan."):
        super().__init__(
            message=message,
            code='loan_eligibility_error',
            status_code=status.HTTP_403_FORBIDDEN
        )


class DuplicateRequestError(SaccoBridgeException):

    def __init__(self, message="This request has already been processed."):
        super().__init__(
            message=message,
            code='duplicate_request',
            status_code=status.HTTP_409_CONFLICT
        )


class AuthenticationFailedError(SaccoBridgeException):

    def __init__(self, message="Authentication failed."):
        super().__init__(
            message=message,
            code='authentication_failed',
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class PermissionDeniedError(SaccoBridgeException):

    def __init__(self, message="You do not have permission to perform this action."):
        super().__init__(
            message=message,
            code='permission_denied',
            status_code=status.HTTP_403_FORBIDDEN
        )


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:
        errors = []
        request_id = getattr(context.get('request'), 'request_id', None)

        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if isinstance(value, list):
                    for item in value:
                        errors.append({
                            'field': key,
                            'message': str(item),
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
                'code': 'validation_error',
                'message': 'Request validation failed.',
                'details': errors,
            },
            'meta': {
                'request_id': request_id,
                'timestamp': str(__import__('django.utils.timezone').now()),
            }
        }

    return response


def handle_sacco_bridge_exception(exc, context):
    logger.error(
        f"SaccoBridge Exception: {exc.message}",
        extra={
            'code': exc.code,
            'status_code': exc.status_code,
            'context': str(context)
        }
    )

    return Response(
        {
            'success': False,
            'error': {
                'code': exc.code,
                'message': exc.message,
                'details': [],
            },
            'meta': {
                'timestamp': str(__import__('django.utils.timezone').now()),
            }
        },
        status=exc.status_code
    )