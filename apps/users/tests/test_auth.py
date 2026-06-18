import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.tests.factories import UserFactory


@pytest.mark.django_db
class TestRegistration:

    def setup_method(self):
        self.client = APIClient()
        self.register_url = reverse('auth-register')
        self.valid_data = {
            'email': 'newuser@test.com',
            'phone_number': '0712123456',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePass@2026',
            'password_confirm': 'SecurePass@2026',
            'accepted_terms': True,
            'accepted_privacy': True,
            'recaptcha': 'test-token'
        }

    def test_register_success(self):
        response = self.client.post(self.register_url, self.valid_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert 'user_id' in response.data['data']

    def test_register_duplicate_email(self):
        UserFactory(email='existing@test.com')
        data = {**self.valid_data, 'email': 'existing@test.com'}
        response = self.client.post(self.register_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self):
        data = {**self.valid_data, 'password_confirm': 'Different@2026'}
        response = self.client.post(self.register_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self):
        data = {**self.valid_data, 'password': 'short', 'password_confirm': 'short'}
        response = self.client.post(self.register_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_terms(self):
        data = {**self.valid_data, 'accepted_terms': False}
        response = self.client.post(self.register_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:

    def setup_method(self):
        self.client = APIClient()
        self.login_url = reverse('auth-login')
        self.user = UserFactory(email='logintest@test.com')
        self.user.set_password('TestPass@2026')
        self.user.save()

    def test_login_success(self):
        response = self.client.post(self.login_url, {
            'email': 'logintest@test.com',
            'password': 'TestPass@2026',
            'device_info': 'Test',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data['data']
        # Refresh token is set as httpOnly cookie, not in response body
        assert 'refresh_token' in response.cookies
        
    def test_login_wrong_password(self):
        response = self.client.post(self.login_url, {
            'email': 'logintest@test.com',
            'password': 'WrongPass@2026',
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self):
        response = self.client.post(self.login_url, {
            'email': 'noone@test.com',
            'password': 'TestPass@2026',
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_returns_user_data(self):
        response = self.client.post(self.login_url, {
            'email': 'logintest@test.com',
            'password': 'TestPass@2026',
            'device_info': 'Test',
        }, format='json')
        assert 'user' in response.data['data']
        assert response.data['data']['user']['email'] == 'logintest@test.com'
        # refresh_token should NOT be in body
        assert 'refresh_token' not in response.data['data']

@pytest.mark.django_db
class TestTokenManagement:

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(email='tokentest@test.com')
        self.refresh_url = reverse('auth-token-refresh')

        # Get tokens - refresh is in cookie now
        login_resp = self.client.post(reverse('auth-login'), {
            'email': 'tokentest@test.com',
            'password': 'TestPass@2026',
            'device_info': 'Test',
        }, format='json')
        self.access_token = login_resp.data['data']['access_token']
        # Get refresh token from cookie for tests that need it
        self.refresh_token = login_resp.cookies.get('refresh_token').value

    def test_refresh_token_success(self):
        response = self.client.post(self.refresh_url, {
            'refresh': self.refresh_token,
        }, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_refresh_invalid_token(self):
        response = self.client.post(self.refresh_url, {
            'refresh': 'invalid-token',
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_endpoint(self):
        profile_url = reverse('user-profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(profile_url)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_endpoint(self):
        profile_url = reverse('user-profile')
        response = self.client.get(profile_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(email='logouttest@test.com')
        self.logout_url = reverse('auth-logout')

        login_resp = self.client.post(reverse('auth-login'), {
            'email': 'logouttest@test.com',
            'password': 'TestPass@2026',
            'device_info': 'Test',
        }, format='json')
        self.access_token = login_resp.data['data']['access_token']
        self.refresh_token = login_resp.cookies.get('refresh_token').value

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.logout_url, {
            'refresh_token': self.refresh_token,
        }, format='json')
        assert response.status_code == status.HTTP_200_OK