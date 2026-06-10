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
        
        # Utilizamos el manager personalizado que requiere email en lugar de username
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            first_name='Juan',
            last_name='Perez'
        )
        
        # Obtenemos las rutas (URLs) a las que haremos las peticiones simuladas
        self.login_url = reverse('users:login')
        self.refresh_url = reverse('users:token-refresh')
        self.me_url = reverse('users:me')

    def test_flujo_login_exitoso(self, api_client):
        # 1. Enviamos una petición POST al endpoint de login con credenciales válidas
        response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': self.user_password
        }, format='json')
        
        # Comprobamos que el servidor responda con un 200 OK (éxito)
        assert response.status_code == status.HTTP_200_OK
        
        # Comprobamos que el cuerpo de la respuesta contenga los tokens 'access' y 'refresh'
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_login_fallido_credenciales_incorrectas(self, api_client):
        # 2. Enviamos una petición con una contraseña deliberadamente incorrecta
        response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': 'WrongPassword!'
        }, format='json')
        
        # Comprobamos que la respuesta sea 401 Unauthorized (No autorizado)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Nos aseguramos de que por seguridad no se haya devuelto ningún token
        assert 'access' not in response.json()

    def test_refresco_de_token_exitoso(self, api_client):
        # 3. Primero, iniciamos sesión para obtener un 'refresh' token válido
        login_response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': self.user_password
        }, format='json')
        refresh_token = login_response.json()['refresh']
        
        # Luego, enviamos el 'refresh' token al endpoint correspondiente para renovar la sesión
        refresh_response = api_client.post(self.refresh_url, {
            'refresh': refresh_token
        }, format='json')
        
        # Verificamos que la solicitud fue exitosa
        assert refresh_response.status_code == status.HTTP_200_OK
        
        # Verificamos que nos hayan entregado un nuevo 'access' token
        assert 'access' in refresh_response.json()

    def test_acceso_endpoint_protegido_con_token(self, api_client):
        # 4. Obtenemos un token de acceso válido iniciando sesión
        login_response = api_client.post(self.login_url, {
            'email': self.user_email,
            'password': self.user_password
        }, format='json')
        access_token = login_response.json()['access']
        
        # Configuramos el cliente para que incluya el token en las cabeceras HTTP de futuras peticiones
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Hacemos una petición GET al endpoint de perfil (ruta protegida)
        response = api_client.get(self.me_url)
        
        # Verificamos que ahora sí nos da acceso (200 OK)
        assert response.status_code == status.HTTP_200_OK
        
        # Verificamos que la información devuelta corresponda a nuestro usuario
        assert response.json()['email'] == self.user_email

    def test_acceso_denegado_sin_token(self, api_client):
        # 5. Intentamos acceder al perfil SIN haber configurado ninguna credencial/token
        response = api_client.get(self.me_url)
        
        # Verificamos que el sistema bloquee el acceso retornando 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
