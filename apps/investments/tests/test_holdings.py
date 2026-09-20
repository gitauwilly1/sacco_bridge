"""Tests for SACCO member holdings and balance mathematics."""
from decimal import Decimal
import pytest
from apps.core.tests.factories import UserFactory
from apps.investments.models import (
    SACCO,
    SACCOShareClass,
    SACCOMemberHolding,
    SASRATier,
    SACCOStatus,
    ShareClass,
)


@pytest.fixture
def sacco():
    return SACCO.objects.create(
        name="Stima SACCO",
        registration_number="CS/12345",
        sasra_tier=SASRATier.TIER_1,
        status=SACCOStatus.ACTIVE,
    )


@pytest.fixture
def share_class(sacco):
    return SACCOShareClass.objects.create(
        sacco=sacco,
        share_class=ShareClass.DEVELOPMENT,
        nominal_value=Decimal("100.00"),
        total_issued=Decimal("100000.0000"),
    )


@pytest.fixture
def member_user():
    return UserFactory(phone_number="0711111111", email="seller@sacco.test")


@pytest.fixture
def buyer_user():
    return UserFactory(phone_number="0722222222", email="buyer@sacco.test")


@pytest.mark.django_db
class TestSACCOMemberHolding:
    def test_available_shares_calculation(self, sacco, share_class, member_user):
        holding = SACCOMemberHolding.objects.create(
            user=member_user,
            sacco=sacco,
            share_class=share_class,
            total_shares=Decimal("500.0000"),
            reserved_shares=Decimal("150.0000"),
            verification_status="VERIFIED",
        )
        assert holding.available_shares == Decimal("350.0000")

    def test_reserve_shares_success(self, sacco, share_class, member_user):
        holding = SACCOMemberHolding.objects.create(
            user=member_user,
            sacco=sacco,
            share_class=share_class,
            total_shares=Decimal("500.0000"),
            reserved_shares=Decimal("0.0000"),
            verification_status="VERIFIED",
        )
        assert holding.reserve_shares(Decimal("200.0000")) is True
        holding.refresh_from_db()
        assert holding.reserved_shares == Decimal("200.0000")
        assert holding.available_shares == Decimal("300.0000")

    def test_reserve_shares_insufficient_available(self, sacco, share_class, member_user):
        holding = SACCOMemberHolding.objects.create(
            user=member_user,
            sacco=sacco,
            share_class=share_class,
            total_shares=Decimal("100.0000"),
            reserved_shares=Decimal("50.0000"),
            verification_status="VERIFIED",
        )
        with pytest.raises(ValueError, match="Insufficient available shares"):
            holding.reserve_shares(Decimal("60.0000"))
        holding.refresh_from_db()
        assert holding.reserved_shares == Decimal("50.0000")

    def test_release_shares_does_not_go_negative(self, sacco, share_class, member_user):
        holding = SACCOMemberHolding.objects.create(
            user=member_user,
            sacco=sacco,
            share_class=share_class,
            total_shares=Decimal("500.0000"),
            reserved_shares=Decimal("50.0000"),
            verification_status="VERIFIED",
        )
        holding.release_shares(Decimal("100.0000"))
        holding.refresh_from_db()
        assert holding.reserved_shares == Decimal("0.0000")
        assert holding.available_shares == Decimal("500.0000")

    def test_transfer_shares_atomic_balance(self, sacco, share_class, member_user, buyer_user):
        seller_holding = SACCOMemberHolding.objects.create(
            user=member_user,
            sacco=sacco,
            share_class=share_class,
            total_shares=Decimal("1000.0000"),
            reserved_shares=Decimal("300.0000"),
            verification_status="VERIFIED",
        )
        buyer_holding = SACCOMemberHolding.objects.create(
            user=buyer_user,
            sacco=sacco,
            share_class=share_class,
            total_shares=Decimal("200.0000"),
            reserved_shares=Decimal("0.0000"),
            verification_status="VERIFIED",
        )

        seller_holding.transfer_shares(Decimal("300.0000"), to_holding=buyer_holding)

        seller_holding.refresh_from_db()
        buyer_holding.refresh_from_db()

        assert seller_holding.total_shares == Decimal("700.0000")
        assert seller_holding.reserved_shares == Decimal("0.0000")
        assert buyer_holding.total_shares == Decimal("500.0000")
        assert buyer_holding.reserved_shares == Decimal("0.0000")
