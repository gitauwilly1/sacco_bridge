import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.models import DeletionRequest
from apps.core.tests.factories import UserFactory
from apps.users.models import Role


@pytest.mark.django_db
class TestAdminDeletionRequestDetail:

    def setup_method(self):
        self.client = APIClient()
        admin = UserFactory(roles=[Role.PLATFORM_ADMIN])
        self.client.force_authenticate(admin)
        requester = UserFactory()
        self.req = DeletionRequest.objects.create(
            requested_by=requester,
            content_type=ContentType.objects.get_for_model(requester),
            object_id=requester.id,
            object_repr='Some chama',
            reason='duplicate',
        )

    def test_detail_returns_request(self):
        url = reverse('admin-deletion-request-detail', args=[self.req.id])
        res = self.client.get(url)
        assert res.status_code == 200
        assert res.data['data']['id'] == str(self.req.id)
        assert res.data['data']['reason'] == 'duplicate'

    def test_detail_unknown_id_is_404(self):
        url = reverse('admin-deletion-request-detail', args=[uuid.uuid4()])
        assert self.client.get(url).status_code == 404

    def test_non_staff_forbidden(self):
        self.client.force_authenticate(UserFactory())
        url = reverse('admin-deletion-request-detail', args=[self.req.id])
        assert self.client.get(url).status_code == 403
