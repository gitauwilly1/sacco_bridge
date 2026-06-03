import pytest
from django.utils import timezone

from apps.transactions.models import (
    SettlementIntent, SettlementState, SettlementEventTrigger
)
from apps.core.tests.factories import SettlementIntentFactory


@pytest.mark.django_db
class TestSettlementStateMachine:

    def setup_method(self):
        self.intent = SettlementIntentFactory()

    def test_initial_state(self):
        assert self.intent.state == SettlementState.MATCH_PROPOSED

    def test_valid_transition_to_locked(self):
        result = self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )
        assert result is True
        assert self.intent.state == SettlementState.INTENT_LOCKED

    def test_invalid_transition_raises_error(self):
        with pytest.raises(ValueError):
            self.intent.transition_to(
                SettlementState.LEDGER_FINALIZED,
                SettlementEventTrigger.SYSTEM_MATCH
            )

    def test_full_happy_path(self):
        transitions = [
            (SettlementState.INTENT_LOCKED, SettlementEventTrigger.INTENT_CREATED),
            (SettlementState.BUYER_DEBIT_INITIATED, SettlementEventTrigger.INTENT_CREATED),
            (SettlementState.BUYER_DEBIT_CONFIRMED, SettlementEventTrigger.BUYER_SACCO_SUCCESS),
            (SettlementState.SELLER_CREDIT_INITIATED, SettlementEventTrigger.INTENT_CREATED),
            (SettlementState.SELLER_CREDIT_CONFIRMED, SettlementEventTrigger.SELLER_SACCO_SUCCESS),
            (SettlementState.LEDGER_FINALIZED, SettlementEventTrigger.SYSTEM_MATCH),
        ]

        for new_state, trigger in transitions:
            result = self.intent.transition_to(new_state, trigger)
            assert result is True
            assert self.intent.state == new_state

    def test_point_of_no_return(self):
        self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.BUYER_DEBIT_INITIATED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.BUYER_DEBIT_CONFIRMED,
            SettlementEventTrigger.BUYER_SACCO_SUCCESS
        )

        assert self.intent.is_past_point_of_no_return() is True

    def test_not_past_point_of_no_return(self):
        self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )
        assert self.intent.is_past_point_of_no_return() is False

    def test_compensation_path(self):
        self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.BUYER_DEBIT_INITIATED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.BUYER_DEBIT_CONFIRMED,
            SettlementEventTrigger.BUYER_SACCO_SUCCESS
        )
        self.intent.transition_to(
            SettlementState.COMPENSATING,
            SettlementEventTrigger.OPS_REVERSAL_INITIATED
        )
        self.intent.transition_to(
            SettlementState.REVERSED,
            SettlementEventTrigger.COMPENSATION_SUCCESS
        )

        assert self.intent.state == SettlementState.REVERSED

    def test_dispute_path(self):
        self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.DISPUTED_MANUAL,
            SettlementEventTrigger.SELLER_SACCO_FAILURE
        )

        assert self.intent.state == SettlementState.DISPUTED_MANUAL

    def test_terminal_states(self):
        self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.BUYER_DEBIT_INITIATED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.BUYER_DEBIT_CONFIRMED,
            SettlementEventTrigger.BUYER_SACCO_SUCCESS
        )
        self.intent.transition_to(
            SettlementState.SELLER_CREDIT_INITIATED,
            SettlementEventTrigger.INTENT_CREATED
        )
        self.intent.transition_to(
            SettlementState.SELLER_CREDIT_CONFIRMED,
            SettlementEventTrigger.SELLER_SACCO_SUCCESS
        )
        self.intent.transition_to(
            SettlementState.LEDGER_FINALIZED,
            SettlementEventTrigger.SYSTEM_MATCH
        )

        assert self.intent.is_terminal() is True

        # Should not be able to transition from terminal state
        with pytest.raises(ValueError):
            self.intent.transition_to(
                SettlementState.REVERSED,
                SettlementEventTrigger.OPS_REVERSAL_INITIATED
            )

    def test_events_created(self):
        self.intent.transition_to(
            SettlementState.INTENT_LOCKED,
            SettlementEventTrigger.INTENT_CREATED
        )

        assert self.intent.events.count() == 1
        event = self.intent.events.first()
        assert event.from_state == SettlementState.MATCH_PROPOSED
        assert event.to_state == SettlementState.INTENT_LOCKED
        assert event.trigger == SettlementEventTrigger.INTENT_CREATED