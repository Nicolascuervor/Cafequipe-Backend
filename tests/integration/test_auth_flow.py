import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestAuthFlow:

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.user_email = 'test@cafequipe.com'
        self.user_password = 'Password123!'

        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            first_name='Juan',
            last_name='Perez'
        )

        self.login_url = reverse('users:login')
        self.refresh_url = reverse('users:token-refresh')
        self.me_url = reverse('users:me')

    def test_flujo_login_exitoso(self, api_client):

        response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': self.user_password
        }, format='json')

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_login_fallido_credenciales_incorrectas(self, api_client):

        response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': 'WrongPassword!'
        }, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        assert 'access' not in response.json()

    def test_refresco_de_token_exitoso(self, api_client):

        login_response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': self.user_password
        }, format='json')
        refresh_token = login_response.json()['refresh']

        refresh_response = api_client.post(self.refresh_url, {
            'refresh': refresh_token
        }, format='json')

        assert refresh_response.status_code == status.HTTP_200_OK

        assert 'access' in refresh_response.json()

    def test_acceso_endpoint_protegido_con_token(self, api_client):

        login_response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': self.user_password
        }, format='json')
        access_token = login_response.json()['access']

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = api_client.get(self.me_url)

        assert response.status_code == status.HTTP_200_OK

        assert response.json()['email'] == self.user_email

    def test_acceso_denegado_sin_token(self, api_client):

        response = api_client.get(self.me_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED