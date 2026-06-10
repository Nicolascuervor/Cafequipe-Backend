import pytest
from unittest.mock import MagicMock, patch
from apps.users.throttles import LoginFailedThrottle

class TestLoginFailedThrottle:

    @pytest.fixture
    def throttle(self):
        """Instancia del limitador anti fuerza bruta."""
        return LoginFailedThrottle()

    @pytest.fixture
    def request_mock(self):
        """Simulacro de petición HTTP."""
        req = MagicMock()
        req.method = 'POST'
        req.META = {'REMOTE_ADDR': '192.168.1.100'}
        return req

    def test_allow_request_metodo_distinto(self, throttle, request_mock):
        """Si la petición no es POST (ej. un GET de lectura), no cuenta como intento fallido."""
        request_mock.method = 'GET'
        assert throttle.allow_request(request_mock, view=None) is True

    @patch('apps.users.throttles.cache')
    def test_allow_request_menor_a_5(self, mock_cache, throttle, request_mock):
        """Si la IP tiene menos de 5 fallos, se le permite seguir intentando."""
        mock_cache.get.return_value = 3 # Simulamos 3 fallos en caché
        
        assert throttle.allow_request(request_mock, view=None) is True
        mock_cache.get.assert_called_with('login_failed_count_192.168.1.100', 0)

    @patch('apps.users.throttles.cache')
    def test_allow_request_bloqueo(self, mock_cache, throttle, request_mock):
        """Si la IP alcanza los 5 fallos, se rechaza la petición inmediatamente (False)."""
        mock_cache.get.return_value = 5
        
        assert throttle.allow_request(request_mock, view=None) is False

    @patch('apps.users.throttles.cache')
    def test_extrae_ip_desde_proxy(self, mock_cache, throttle, request_mock):
        """Si la petición viene detrás de un proxy (Nginx), debe leer la IP real del cliente."""
        request_mock.META = {
            'HTTP_X_FORWARDED_FOR': '10.0.0.5, 192.168.1.1',
            'REMOTE_ADDR': '127.0.0.1' # IP del proxy que debemos ignorar
        }
        mock_cache.get.return_value = 1
        
        throttle.allow_request(request_mock, view=None)
        
        # Comprobamos que generó la llave sobre la IP real
        mock_cache.get.assert_called_with('login_failed_count_10.0.0.5', 0)
