import logging
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core import models
from apps.core.utils import (
    generate_idempotency_key, calculate_settlement_fee
)
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, LedgerEntry,
    SettlementReversal, SettlementState, SettlementEventTrigger,
    DisputeResolutionType
)

logger = logging.getLogger(__name__)


class SettlementService:
    @staticmethod
    def create_settlement_intent(
        connection, buyer, seller, amount, share_quantity,
        price_per_share, buyer_sacco_id, buyer_sacco_name,
        seller_sacco_id, seller_sacco_name
    ):
        idempotency_key = generate_idempotency_key(
            str(connection.id),
            str(buyer.id),
            str(seller.id),
            str(amount),
            str(share_quantity)
        )

        platform_fee = calculate_settlement_fee(amount)

        with db_transaction.atomic():
            intent = SettlementIntent.objects.create(
                idempotency_key=idempotency_key,
                state=SettlementState.MATCH_PROPOSED,
                connection=connection,
                liquidity_request_id=connection.liquidity_request.id if connection.liquidity_request else None,
                buyer=buyer,
                seller=seller,
                amount=amount,
                share_quantity=share_quantity,
                price_per_share=price_per_share,
                platform_fee=platform_fee,
                buyer_sacco_id=buyer_sacco_id,
                buyer_sacco_name=buyer_sacco_name,
                seller_sacco_id=seller_sacco_id,
                seller_sacco_name=seller_sacco_name,
            )

            logger.info(
                f"Settlement intent created: {intent.uuid} "
                f"for connection {connection.id}"
            )

            return intent

    @staticmethod
    def initiate_settlement(intent):
        if intent.state != SettlementState.MATCH_PROPOSED:
            raise ValueError(_('Settlement must be in MATCH_PROPOSED state.'))

        intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )

        logger.info(f"Settlement {intent.uuid} locked. Funds reserved.")

        return intent

    @staticmethod
    def process_buyer_debit(intent, sacco_response):
        if sacco_response.get('status') == 'SUCCESS':
            intent.buyer_debit_ref = sacco_response.get('transaction_id', '')
            intent.save(update_fields=['buyer_debit_ref'])

            intent.transition_to(
                SettlementState.BUYER_DEBIT_CONFIRMED,
                SettlementEventTrigger.BUYER_SACCO_SUCCESS,
                external_ref=intent.buyer_debit_ref
            )

            logger.info(
                f"Buyer debit confirmed: {intent.uuid} "
                f"Ref: {intent.buyer_debit_ref}"
            )

        elif sacco_response.get('status') == 'FAILURE':
            error_code = sacco_response.get('error_code', 'UNKNOWN')

            if error_code in ['INSUFFICIENT_FUNDS', 'ACCOUNT_FROZEN']:
                intent.transition_to(
                    SettlementState.REVERSED,
                    SettlementEventTrigger.BUYER_SACCO_FAILURE,
                    metadata={'error_code': error_code}
                )
            else:
                intent.transition_to(
                    SettlementState.DISPUTED_MANUAL,
                    SettlementEventTrigger.BUYER_SACCO_FAILURE,
                    metadata={'error_code': error_code}
                )

        return intent

    @staticmethod
    def process_seller_credit(intent, sacco_response):
        if sacco_response.get('status') == 'SUCCESS':
            intent.seller_credit_ref = sacco_response.get('transaction_id', '')
            intent.save(update_fields=['seller_credit_ref'])

            intent.transition_to(
                SettlementState.SELLER_CREDIT_CONFIRMED,
                SettlementEventTrigger.SELLER_SACCO_SUCCESS,
                external_ref=intent.seller_credit_ref
            )

            logger.info(
                f"Seller credit confirmed: {intent.uuid} "
                f"Ref: {intent.seller_credit_ref}"
            )

        elif sacco_response.get('status') in ['TIMEOUT', 'UNKNOWN']:
            intent.transition_to(
                SettlementState.DISPUTED_MANUAL,
                SettlementEventTrigger.SELLER_SACCO_FAILURE,
                metadata=sacco_response
            )

            logger.warning(
                f"Seller credit ambiguous for settlement {intent.uuid}"
            )

        return intent

    @staticmethod
    def finalize_settlement(intent):
        if intent.state != SettlementState.SELLER_CREDIT_CONFIRMED:
            raise ValueError(_('Settlement must have seller credit confirmed.'))

        with db_transaction.atomic():
            LedgerEntry.objects.create(
                settlement=intent,
                buyer=intent.buyer,
                seller=intent.seller,
                sacco_id=intent.seller_sacco_id,
                share_quantity=intent.share_quantity,
                price_per_share=intent.price_per_share,
                total_amount=intent.amount,
                platform_fee=intent.platform_fee,
            )

            intent.transition_to(
                SettlementState.LEDGER_FINALIZED,
                SettlementEventTrigger.SYSTEM_MATCH
            )

            if intent.liquidity_request_id:
                from apps.investments.models import LiquidityRequest, LiquidityRequestStatus
                LiquidityRequest.objects.filter(
                    id=intent.liquidity_request_id
                ).update(status=LiquidityRequestStatus.SETTLED)

            if intent.connection:
                from apps.investments.models import Connection, ConnectionStatus
                Connection.objects.filter(
                    id=intent.connection.id
                ).update(
                    status=ConnectionStatus.SETTLED,
                    settlement_intent_id=intent.id,
                    settled_at=timezone.now()
                )

            logger.info(f"Settlement {intent.uuid} finalized.")

        return intent

    @staticmethod
    def initiate_compensation(intent):
        if not intent.is_past_point_of_no_return():
            raise ValueError(_('Compensation only applies after point of no return.'))

        intent.transition_to(
            SettlementState.COMPENSATING,
            SettlementEventTrigger.OPS_REVERSAL_INITIATED
        )

        SettlementReversal.objects.create(
            settlement=intent,
            reversal_type='BUYER_DEBIT',
            amount=intent.amount,
            initiated_by='system',
            status='INITIATED',
            notes=_('Automated compensation for failed seller credit.')
        )

        logger.info(f"Compensation initiated for settlement {intent.uuid}")

        return intent

    @staticmethod
    def complete_reversal(intent, reversal_ref=''):
        intent.buyer_reversal_ref = reversal_ref
        intent.save(update_fields=['buyer_reversal_ref'])

        intent.transition_to(
            SettlementState.REVERSED,
            SettlementEventTrigger.COMPENSATION_SUCCESS,
            external_ref=reversal_ref
        )

        SettlementReversal.objects.filter(
            settlement=intent,
            status='INITIATED'
        ).update(
            status='COMPLETED',
            completed_at=timezone.now(),
            external_ref=reversal_ref
        )

        if intent.liquidity_request_id:
            from apps.investments.models import LiquidityRequest, LiquidityRequestStatus
            LiquidityRequest.objects.filter(
                id=intent.liquidity_request_id
            ).update(status=LiquidityRequestStatus.CANCELLED)

        logger.info(f"Settlement {intent.uuid} fully reversed.")

        return intent

    @staticmethod
    def escalate_to_trustee(intent, resolved_by, notes=''):
        intent.dispute_resolution_type = DisputeResolutionType.ESCALATED_TO_TRUSTEE
        intent.dispute_resolved_by = resolved_by
        intent.internal_notes = notes
        intent.save(update_fields=[
            'dispute_resolution_type', 'dispute_resolved_by', 'internal_notes'
        ])

        intent.transition_to(
            SettlementState.CLOSED_BY_TRUSTEE,
            SettlementEventTrigger.OPS_ESCALATED_TO_TRUSTEE,
            metadata={'resolved_by': str(resolved_by.id), 'notes': notes}
        )

        logger.info(f"Settlement {intent.uuid} escalated to trustee.")

        return intent


class RecoveryService:

    STATE_TIMEOUTS = {
        SettlementState.MATCH_PROPOSED: 300,      # 5 minutes
        SettlementState.INTENT_LOCKED: 60,         # 1 minute
        SettlementState.BUYER_DEBIT_INITIATED: 300, # 5 minutes
        SettlementState.SELLER_CREDIT_INITIATED: 900, # 15 minutes
    }

    @staticmethod
    def find_stuck_settlements():
        from django.db.models import Q

        stuck = []
        for state, timeout_seconds in RecoveryService.STATE_TIMEOUTS.items():
            cutoff = timezone.now() - timezone.timedelta(seconds=timeout_seconds)

            stalled = SettlementIntent.objects.filter(
                state=state,
                updated_at__lt=cutoff,
                retry_count__lt=models.F('max_retries'),
                is_deleted=False
            )

            stuck.extend(stalled)

        return stuck

    @staticmethod
    def attempt_recovery(intent):
        if intent.retry_count >= intent.max_retries:
            intent.transition_to(
                SettlementState.DISPUTED_MANUAL,
                SettlementEventTrigger.API_RETRY_EXHAUSTED,
                metadata={'retry_count': intent.retry_count}
            )
            return False

        intent.retry_count += 1
        intent.save(update_fields=['retry_count', 'updated_at'])

        logger.info(
            f"Recovery attempt {intent.retry_count}/{intent.max_retries} "
            f"for settlement {intent.uuid} in state {intent.state}"
        )

        return True