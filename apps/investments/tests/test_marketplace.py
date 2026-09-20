"""Tests for secondary SACCO share marketplace views and negotiation lifecycle."""
import uuid
from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from apps.core.tests.factories import UserFactory
from apps.investments.models import (
    SACCO,
    SACCOShareClass,
    SACCOMemberHolding,
    LiquidityRequest,
    LiquidityRequestStatus,
    BuyerInterest,
    Connection,
    ConnectionStatus,
    Offer,
    SASRATier,
    SACCOStatus,
    ShareClass,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sacco():
    return SACCO.objects.create(
        name="Harambee SACCO",
        registration_number="CS/99887",
        sasra_tier=SASRATier.TIER_1,
        status=SACCOStatus.ACTIVE,
    )


@pytest.fixture
def share_class(sacco):
    return SACCOShareClass.objects.create(
        sacco=sacco,
        share_class=ShareClass.DEVELOPMENT,
        nominal_value=Decimal("100.00"),
        total_issued=Decimal("50000.0000"),
    )


@pytest.fixture
def seller():
    return UserFactory(phone_number="0733111222", email="seller_market@test.com")


@pytest.fixture
def buyer():
    return UserFactory(phone_number="0733333444", email="buyer_market@test.com")


@pytest.fixture
def seller_holding(sacco, share_class, seller):
    return SACCOMemberHolding.objects.create(
        user=seller,
        sacco=sacco,
        share_class=share_class,
        total_shares=Decimal("1000.0000"),
        reserved_shares=Decimal("0.0000"),
        verification_status="VERIFIED",
    )


@pytest.fixture
def buyer_holding(sacco, share_class, buyer):
    return SACCOMemberHolding.objects.create(
        user=buyer,
        sacco=sacco,
        share_class=share_class,
        total_shares=Decimal("100.0000"),
        reserved_shares=Decimal("0.0000"),
        verification_status="VERIFIED",
    )


@pytest.mark.django_db
class TestLiquidityRequestLifecycle:
    def test_create_liquidity_request_reserves_shares(self, api_client, sacco, share_class, seller, seller_holding):
        api_client.force_authenticate(user=seller)
        url = "/api/v1/investments/requests/"
        data = {
            "sacco": str(sacco.id),
            "share_class": str(share_class.id),
            "holding": str(seller_holding.id),
            "share_quantity": "250.0000",
            "expected_price_per_share": "120.00",
            "minimum_price_per_share": "110.00",
        }
        headers = {"HTTP_X_IDEMPOTENCY_KEY": str(uuid.uuid4())}
        response = api_client.post(url, data, format="json", **headers)
        assert response.status_code == 201

        seller_holding.refresh_from_db()
        assert seller_holding.reserved_shares == Decimal("250.0000")
        assert seller_holding.available_shares == Decimal("750.0000")

    def test_cancel_liquidity_request_releases_shares(self, api_client, sacco, share_class, seller, seller_holding):
        seller_holding.reserve_shares(Decimal("200.0000"))
        req = LiquidityRequest.objects.create(
            seller=seller,
            sacco=sacco,
            share_class=share_class,
            holding=seller_holding,
            share_quantity=Decimal("200.0000"),
            expected_price_per_share=Decimal("120.00"),
            status=LiquidityRequestStatus.ACTIVE,
        )

        api_client.force_authenticate(user=seller)
        cancel_url = f"/api/v1/investments/requests/{req.id}/cancel/"
        headers = {"HTTP_X_IDEMPOTENCY_KEY": str(uuid.uuid4())}
        response = api_client.post(cancel_url, format="json", **headers)
        assert response.status_code == 200

        req.refresh_from_db()
        seller_holding.refresh_from_db()
        assert req.status == LiquidityRequestStatus.CANCELLED
        assert seller_holding.reserved_shares == Decimal("0.0000")


@pytest.mark.django_db
class TestNegotiationStateTransitions:
    def test_express_interest_creates_buyer_interest(
        self, api_client, sacco, share_class, seller, buyer, seller_holding, buyer_holding
    ):
        seller_holding.reserve_shares(Decimal("100.0000"))
        req = LiquidityRequest.objects.create(
            seller=seller,
            sacco=sacco,
            share_class=share_class,
            holding=seller_holding,
            share_quantity=Decimal("100.0000"),
            expected_price_per_share=Decimal("150.00"),
            status=LiquidityRequestStatus.ACTIVE,
        )

        api_client.force_authenticate(user=buyer)
        opp_url = f"/api/v1/investments/opportunities/{req.id}/express_interest/"
        headers = {"HTTP_X_IDEMPOTENCY_KEY": str(uuid.uuid4())}
        resp = api_client.post(opp_url, {"message": "Interested in these shares"}, format="json", **headers)
        assert resp.status_code == 200

        interest = BuyerInterest.objects.get(liquidity_request=req, buyer=buyer)
        assert interest.buyer_message == "Interested in these shares"
        req.refresh_from_db()
        assert req.status == LiquidityRequestStatus.MATCHED

    def test_connection_make_and_accept_offer(
        self, api_client, sacco, share_class, seller, buyer, seller_holding, buyer_holding
    ):
        seller_holding.reserve_shares(Decimal("100.0000"))
        req = LiquidityRequest.objects.create(
            seller=seller,
            sacco=sacco,
            share_class=share_class,
            holding=seller_holding,
            share_quantity=Decimal("100.0000"),
            expected_price_per_share=Decimal("150.00"),
            status=LiquidityRequestStatus.MATCHED,
        )

        connection = Connection.objects.create(
            liquidity_request=req,
            buyer=buyer,
            seller=seller,
            status=ConnectionStatus.CONNECTED,
        )

        # Buyer makes offer
        api_client.force_authenticate(user=buyer)
        offer_url = f"/api/v1/investments/connections/{connection.id}/make_offer/"
        headers = {"HTTP_X_IDEMPOTENCY_KEY": str(uuid.uuid4())}
        resp = api_client.post(offer_url, {"price_per_share": "140.00", "quantity": "100.0000"}, format="json", **headers)
        assert resp.status_code == 201
        connection.refresh_from_db()
        assert connection.status == ConnectionStatus.OFFER_MADE
        offer = Offer.objects.get(connection=connection)
        assert offer.status == "PENDING"
        assert offer.price_per_share == Decimal("140.00")

        # Seller accepts offer
        api_client.force_authenticate(user=seller)
        accept_url = f"/api/v1/investments/connections/{connection.id}/offers/{offer.id}/accept/"
        headers = {"HTTP_X_IDEMPOTENCY_KEY": str(uuid.uuid4())}
        resp = api_client.post(accept_url, format="json", **headers)
        assert resp.status_code == 200

        connection.refresh_from_db()
        offer.refresh_from_db()
        assert connection.status == ConnectionStatus.OFFER_ACCEPTED
        assert offer.status == "ACCEPTED"
        assert connection.agreed_price_per_share == Decimal("140.00")
        assert connection.agreed_quantity == Decimal("100.0000")
