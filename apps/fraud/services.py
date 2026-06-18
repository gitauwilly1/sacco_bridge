"""Fraud detection engine for real-time transaction risk assessment."""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count

from apps.fraud.models import (
    TransactionRiskAssessment, DeviceFingerprint,
    RiskLevel, FraudAction,
)

logger = logging.getLogger(__name__)


class FraudDetectionService:

    # Risk thresholds
    HIGH_RISK_SCORE = 70
    MEDIUM_RISK_SCORE = 40
    LOW_RISK_SCORE = 20

    # Velocity thresholds
    MAX_TRANSACTIONS_24H = 10
    MAX_TOTAL_24H = Decimal('500000.00')
    MAX_TRANSACTIONS_7D = 50

    # Amount thresholds
    UNUSUAL_AMOUNT_MULTIPLIER = 3  # 3x user's average
    LARGE_TRANSACTION = Decimal('100000.00')
    CRITICAL_TRANSACTION = Decimal('500000.00')

    @classmethod
    def assess_transaction(cls, user, transaction_type, transaction_ref,
        amount, device_fingerprint='', ip_address=None):
        assessment = TransactionRiskAssessment.objects.create(
            user=user,
            transaction_type=transaction_type,
            transaction_reference=transaction_ref,
            amount=amount,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
        )

        risk_score = 0
        triggers = []

        # 1. Velocity Checks
        velocity_24h = cls._check_velocity_24h(user)
        assessment.velocity_24h_count = velocity_24h['count']
        assessment.velocity_24h_total = velocity_24h['total']
        assessment.velocity_7d_count = cls._check_velocity_7d(user)

        if velocity_24h['count'] > cls.MAX_TRANSACTIONS_24H:
            risk_score += 25
            triggers.append('HIGH_VELOCITY_24H')

        if velocity_24h['total'] > cls.MAX_TOTAL_24H:
            risk_score += 25
            triggers.append('HIGH_TOTAL_24H')

        if velocity_24h['count'] > cls.MAX_TRANSACTIONS_24H * 2:
            risk_score += 25
            triggers.append('CRITICAL_VELOCITY')

        # 2. Amount Patterns
        avg_amount = cls._get_average_amount(user)
        if avg_amount > 0 and amount > avg_amount * cls.UNUSUAL_AMOUNT_MULTIPLIER:
            risk_score += 15
            assessment.is_unusual_amount = True
            triggers.append('UNUSUAL_AMOUNT')

        if amount >= cls.CRITICAL_TRANSACTION:
            risk_score += 20
            triggers.append('CRITICAL_AMOUNT')
        elif amount >= cls.LARGE_TRANSACTION:
            risk_score += 10
            triggers.append('LARGE_AMOUNT')

        # 3. Device Fingerprinting
        if device_fingerprint:
            device = cls._check_device(user, device_fingerprint, ip_address)
            assessment.is_new_device = device['is_new']

            if device['is_new']:
                risk_score += 15
                triggers.append('NEW_DEVICE')

            if device['location_mismatch']:
                risk_score += 20
                assessment.location_mismatch = True
                triggers.append('LOCATION_MISMATCH')

        # 4. IP Reputation
        if ip_address:
            ip_score = cls._check_ip_reputation(ip_address)
            assessment.ip_reputation_score = ip_score

            if ip_score < 30:
                risk_score += 20
                triggers.append('SUSPICIOUS_IP')
            elif ip_score < 50:
                risk_score += 10
                triggers.append('UNKNOWN_IP')

        # 5. Time-Based Patterns
        current_hour = timezone.now().hour
        if current_hour < 5 or current_hour > 23:
            risk_score += 5
            assessment.is_unusual_hour = True
            triggers.append('UNUSUAL_HOUR')

        # Determine risk level and action
        assessment.risk_score = min(100, risk_score)
        assessment.triggers = triggers

        if risk_score >= cls.HIGH_RISK_SCORE:
            assessment.risk_level = RiskLevel.HIGH
            assessment.recommended_action = FraudAction.HOLD
        elif risk_score >= cls.MEDIUM_RISK_SCORE:
            assessment.risk_level = RiskLevel.MEDIUM
            assessment.recommended_action = FraudAction.FLAG
        elif risk_score >= cls.LOW_RISK_SCORE:
            assessment.risk_level = RiskLevel.LOW
            assessment.recommended_action = FraudAction.ALLOW
        else:
            assessment.risk_level = RiskLevel.LOW
            assessment.recommended_action = FraudAction.ALLOW

        # Critical: block if multiple high-risk triggers
        if len([t for t in triggers if 'CRITICAL' in t]) >= 2:
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.recommended_action = FraudAction.BLOCK

        assessment.save()

        logger.info(
            f"Fraud assessment: {assessment.risk_level} (score={risk_score}) "
            f"for user {user.email}, triggers: {triggers}"
        )

        return assessment

    @classmethod
    def _check_velocity_24h(cls, user):
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        transactions = TransactionRiskAssessment.objects.filter(
            user=user,
            created_at__gte=cutoff,
            applied_action=FraudAction.ALLOW,
        )
        return {
            'count': transactions.count(),
            'total': transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        }

    @classmethod
    def _check_velocity_7d(cls, user):
        cutoff = timezone.now() - timezone.timedelta(days=7)
        return TransactionRiskAssessment.objects.filter(
            user=user,
            created_at__gte=cutoff,
        ).count()

    @classmethod
    def _get_average_amount(cls, user):
        avg = TransactionRiskAssessment.objects.filter(
            user=user,
            applied_action=FraudAction.ALLOW,
        ).aggregate(avg=Sum('amount'))['avg']
        return avg or Decimal('0')

    @classmethod
    def _check_device(cls, user, fingerprint, ip_address):
        device, created = DeviceFingerprint.objects.get_or_create(
            user=user,
            fingerprint=fingerprint,
            defaults={'ip_address': ip_address},
        )

        if not created:
            device.last_seen = timezone.now()
            device.transaction_count += 1
            device.save()

        # Check location mismatch
        location_mismatch = False
        if device.ip_address and ip_address:
            # Simple check: different /24 subnet
            device_subnet = '.'.join(device.ip_address.split('.')[:3])
            current_subnet = '.'.join(ip_address.split('.')[:3])
            location_mismatch = device_subnet != current_subnet

        return {
            'is_new': created,
            'location_mismatch': location_mismatch,
            'is_trusted': device.is_trusted,
        }

    @classmethod
    def _check_ip_reputation(cls, ip_address):
        # Known trusted ranges
        trusted_ranges = ['127.0.0', '10.', '192.168.']
        if any(ip_address.startswith(r) for r in trusted_ranges):
            return 100

        # Suspicious ranges (known VPN/Tor exit nodes - simplified)
        suspicious_ranges = []
        if any(ip_address.startswith(r) for r in suspicious_ranges):
            return 10

        # Default: neutral
        return 50