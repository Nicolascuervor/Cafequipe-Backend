import pytest
from unittest.mock import MagicMock, patch
from apps.users.throttles import LoginFailedThrottle

class TestLoginFailedThrottle:

    @pytest.fixture
    def throttle(self):

        return LoginFailedThrottle()

    @pytest.fixture
    def request_mock(self):

        req = MagicMock()
        req.method = 'POST'
        req.META = {'REMOTE_ADDR': '192.168.1.100'}
        return req

    def test_allow_request_metodo_distinto(self, throttle, request_mock):

        request_mock.method = 'GET'
        assert throttle.allow_request(request_mock, view=None) is True

    @patch('apps.users.throttles.cache')
    def test_allow_request_menor_a_5(self, mock_cache, throttle, request_mock):

        mock_cache.get.return_value = 3 # Simulamos 3 fallos en caché
        
        assert throttle.allow_request(request_mock, view=None) is True
        mock_cache.get.assert_called_with('login_failed_count_192.168.1.100', 0)

    @patch('apps.users.throttles.cache')
    def test_allow_request_bloqueo(self, mock_cache, throttle, request_mock):

        mock_cache.get.return_value = 5
        
        assert throttle.allow_request(request_mock, view=None) is False

    @patch('apps.users.throttles.cache')
    def test_extrae_ip_desde_proxy(self, mock_cache, throttle, request_mock):

        request_mock.META = {
            'HTTP_X_FORWARDED_FOR': '10.0.0.5, 192.168.1.1',
            'REMOTE_ADDR': '127.0.0.1' # IP del proxy que debemos ignorar
        }
        mock_cache.get.return_value = 1
        
        throttle.allow_request(request_mock, view=None)

        mock_cache.get.assert_called_with('login_failed_count_10.0.0.5', 0)
