"""Tests for LegalDocument publishing, versioning, and acceptance tracking."""
from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.core.tests.factories import UserFactory
from apps.legal.models import LegalDocument, LegalDocumentType, UserLegalAcceptance


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user():
    return UserFactory(email="legal_user@test.com", phone_number="0744111222")


@pytest.mark.django_db
class TestLegalDocuments:
    def test_publish_activates_new_version_and_deactivates_old(self, test_user):
        doc_v1 = LegalDocument.objects.create(
            document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
            title="Terms & Conditions v1",
            version="1.0",
            content="Version 1.0 terms content.",
            is_current=True,
            published_at=timezone.now() - timedelta(days=30),
        )

        doc_v2 = LegalDocument.objects.create(
            document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
            title="Terms & Conditions v2",
            version="2.0",
            content="Version 2.0 terms content.",
            is_current=False,
        )

        doc_v2.publish(published_by=test_user)

        doc_v1.refresh_from_db()
        doc_v2.refresh_from_db()

        assert doc_v2.is_current is True
        assert doc_v2.published_by == test_user
        assert doc_v1.is_current is False

    def test_acceptance_status_detects_outdated_acceptance(self, api_client, test_user):
        doc_v1 = LegalDocument.objects.create(
            document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
            title="Terms & Conditions v1",
            version="1.0",
            content="Version 1.0 terms content.",
            is_current=True,
            published_at=timezone.now() - timedelta(days=30),
        )

        # User accepts v1.0
        UserLegalAcceptance.objects.create(
            user=test_user,
            document=doc_v1,
            ip_address="127.0.0.1",
            user_agent="pytest-client",
        )

        api_client.force_authenticate(user=test_user)
        resp = api_client.get("/api/v1/legal/status/")
        assert resp.status_code == 200
        # Only terms accepted (no privacy acceptance in this test)
        data = resp.json()['data']
        assert data.get('terms_accepted') is True

        # Now publish v2.0
        doc_v2 = LegalDocument.objects.create(
            document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
            title="Terms & Conditions v2",
            version="2.0",
            content="Version 2.0 terms content.",
            is_current=False,
        )
        doc_v2.publish(published_by=test_user)

        resp2 = api_client.get("/api/v1/legal/status/")
        assert resp2.status_code == 200
        data2 = resp2.json()['data']
        assert data2.get('terms_accepted') is False
