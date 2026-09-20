import uuid
from decimal import Decimal
import pytest
from django.utils import timezone

from apps.core.tests.factories import SettlementIntentFactory, UserFactory
from apps.fraud.models import (
    DeviceFingerprint,
    FraudAction,
    RiskLevel,
    TransactionRiskAssessment,
)
from apps.fraud.services import FraudDetectionService
from apps.transactions.models import SettlementIntent, SettlementState


@pytest.mark.django_db
class TestFraudDetectionEngine:

    def setup_method(self):
        self.user = UserFactory()

    def test_low_risk_standard_transaction_allows(self):
        assessment = FraudDetectionService.assess_transaction(
            user=self.user,
            transaction_type='SETTLEMENT',
            transaction_ref=f"TX_{uuid.uuid4().hex[:8]}",
            amount=Decimal('5000.00'),
            device_fingerprint='known_device_abc123',
            ip_address='192.168.1.10'
        )

        assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert assessment.recommended_action in [FraudAction.ALLOW, FraudAction.FLAG]
        assert assessment.risk_score < 70

    def test_large_and_critical_amount_triggers(self):
        # 1. Large transaction (>= 100,000 KSh)
        a1 = FraudDetectionService.assess_transaction(
            user=self.user,
            transaction_type='SETTLEMENT',
            transaction_ref=f"TX_{uuid.uuid4().hex[:8]}",
            amount=Decimal('150000.00'),
            ip_address='192.168.1.10'
        )
        assert 'LARGE_AMOUNT' in a1.triggers

        # 2. Critical transaction (>= 500,000 KSh)
        a2 = FraudDetectionService.assess_transaction(
            user=self.user,
            transaction_type='SETTLEMENT',
            transaction_ref=f"TX_{uuid.uuid4().hex[:8]}",
            amount=Decimal('600000.00'),
            ip_address='192.168.1.10'
        )
        assert 'CRITICAL_AMOUNT' in a2.triggers

    def test_velocity_24h_high_triggers(self):
        # Seed 11 allowed transactions in past 24 hours
        for i in range(11):
            TransactionRiskAssessment.objects.create(
                user=self.user,
                transaction_type='SETTLEMENT',
                transaction_reference=f"TX_SEED_{i}_{uuid.uuid4().hex[:6]}",
                amount=Decimal('1000.00'),
                risk_score=10,
                risk_level=RiskLevel.LOW,
                recommended_action=FraudAction.ALLOW,
                applied_action=FraudAction.ALLOW,
            )

        # 12th transaction should flag velocity trigger
        assessment = FraudDetectionService.assess_transaction(
            user=self.user,
            transaction_type='SETTLEMENT',
            transaction_ref=f"TX_NEW_{uuid.uuid4().hex[:8]}",
            amount=Decimal('5000.00'),
            ip_address='192.168.1.10'
        )
        assert 'HIGH_VELOCITY_24H' in assessment.triggers
        assert assessment.velocity_24h_count >= 11

    def test_device_fingerprinting_new_device_and_location_mismatch(self):
        # First transaction on device 1 with IP 192.168.1.50
        DeviceFingerprint.objects.create(
            user=self.user,
            fingerprint='dev_fingerprint_xyz',
            ip_address='192.168.1.50',
            is_trusted=False
        )

        # Second transaction on same fingerprint from different /24 subnet 10.0.4.12
        assessment = FraudDetectionService.assess_transaction(
            user=self.user,
            transaction_type='SETTLEMENT',
            transaction_ref=f"TX_{uuid.uuid4().hex[:8]}",
            amount=Decimal('5000.00'),
            device_fingerprint='dev_fingerprint_xyz',
            ip_address='10.0.4.12'
        )
        assert assessment.location_mismatch is True
        assert 'LOCATION_MISMATCH' in assessment.triggers

    def test_settlement_post_save_signal_low_risk_preserves_match_proposed(self):
        buyer = UserFactory()
        buyer.last_login_ip = '192.168.1.10'
        buyer.save()
        seller = UserFactory()

        settlement = SettlementIntentFactory(
            buyer=buyer,
            seller=seller,
            amount=Decimal('10000.00'),
            state=SettlementState.MATCH_PROPOSED
        )

        settlement.refresh_from_db()
        assert settlement.state == SettlementState.MATCH_PROPOSED
        assessment = TransactionRiskAssessment.objects.filter(transaction_reference=str(settlement.uuid)).first()
        assert assessment is not None
        assert assessment.user == buyer

    def test_settlement_post_save_signal_high_risk_holds_settlement(self):
        buyer = UserFactory()
        buyer.last_login_ip = '192.168.1.10'
        buyer.save()

        # Seed high velocity to force high risk
        for i in range(12):
            TransactionRiskAssessment.objects.create(
                user=buyer,
                transaction_type='SETTLEMENT',
                transaction_reference=f"SEED_{i}",
                amount=Decimal('50000.00'),
                risk_score=10,
                risk_level=RiskLevel.LOW,
                recommended_action=FraudAction.ALLOW,
                applied_action=FraudAction.ALLOW,
            )

        seller = UserFactory()
        # Large settlement amount
        settlement = SettlementIntentFactory(
            buyer=buyer,
            seller=seller,
            amount=Decimal('550000.00'),
            state=SettlementState.MATCH_PROPOSED
        )

        settlement.refresh_from_db()
        assessment = TransactionRiskAssessment.objects.filter(transaction_reference=str(settlement.uuid)).first()
        assert assessment is not None
        assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert assessment.recommended_action in [FraudAction.HOLD, FraudAction.BLOCK]
        if assessment.recommended_action == FraudAction.HOLD:
            assert settlement.state == SettlementState.DISPUTED_MANUAL
