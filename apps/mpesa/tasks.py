import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.mpesa.tasks.reconcile_pending_mpesa_transactions',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def reconcile_pending_mpesa_transactions(self):
    logger.info("Starting M-Pesa transaction reconciliation...")

    from apps.mpesa.models import MpesaTransaction, MpesaTransactionStatus
    from apps.mpesa.services import MpesaService

    try:
        cutoff = timezone.now() - timezone.timedelta(minutes=5)

        pending_transactions = MpesaTransaction.objects.filter(
            status__in=[
                MpesaTransactionStatus.INITIATED,
                MpesaTransactionStatus.PROCESSING,
            ],
            initiated_at__lt=cutoff,
            is_deleted=False,
        )

        reconciled_count = 0
        timeout_count = 0

        for transaction in pending_transactions:
            try:
                if not transaction.checkout_request_id:
                    continue

                result = MpesaService.query_stk_status(
                    transaction.checkout_request_id
                )

                if result.get('success'):
                    response_data = result.get('data', {})
                    result_code = response_data.get('ResultCode', '')

                    if result_code == '0':
                        # Payment completed but callback was missed
                        transaction.mark_completed(
                            mpesa_receipt_number=response_data.get(
                                'MpesaReceiptNumber', 'RECONCILED'
                            ),
                            callback_data=response_data,
                        )
                        reconciled_count += 1
                        logger.info(
                            f"Reconciled transaction {transaction.transaction_id}"
                        )
                    elif result_code == '1032':
                        # Transaction cancelled or timed out
                        transaction.mark_timeout()
                        timeout_count += 1
                    elif result_code == '1':
                        # Insufficient funds
                        transaction.mark_failed(
                            'Insufficient funds',
                            response_data,
                        )
                        timeout_count += 1

            except Exception as e:
                logger.error(
                    f"Error reconciling transaction "
                    f"{transaction.transaction_id}: {str(e)}"
                )

        logger.info(
            f"M-Pesa reconciliation complete: "
            f"{reconciled_count} reconciled, {timeout_count} resolved"
        )

        return {
            'reconciled': reconciled_count,
            'resolved': timeout_count,
        }

    except Exception as e:
        logger.error(f"M-Pesa reconciliation failed: {str(e)}")
        raise self.retry(exc=e)