import pytest
from unittest.mock import MagicMock
from apps.users.models import User
from apps.users.permissions.EsGerenteOJefeBodegaPeroSoloGerenteElimina import EsGerenteOJefeBodegaPeroSoloGerenteElimina

class TestPermisosPersonalizados:

    @pytest.fixture
    def permiso(self):
        """Instancia de la clase de permiso a probar."""
        return EsGerenteOJefeBodegaPeroSoloGerenteElimina()

    @pytest.fixture
    def request_mock(self):
        """Simula una petición HTTP de Django Rest Framework."""
        req = MagicMock()
        req.user.is_authenticated = True
        return req

    def test_deniega_anonimo(self, permiso, request_mock):
        """Bloquea cualquier petición si no hay token/sesión."""
        request_mock.user.is_authenticated = False
        # Para permisos a nivel de vista, view es irrelevante aquí
        assert permiso.has_permission(request_mock, view=None) is False

    def test_gerente_puede_eliminar(self, permiso, request_mock):
        """El gerente (GER) tiene poder absoluto, incluyendo DELETE."""
        request_mock.user.rol = User.Rol.GERENTE
        request_mock.method = 'DELETE'
        
        assert permiso.has_permission(request_mock, view=None) is True

    def test_jefe_no_puede_eliminar(self, permiso, request_mock):
        """Un Jefe de Bodega (JBD) intenta borrar, pero el sistema lo rechaza."""
        request_mock.user.rol = User.Rol.JEFE_BODEGA
        request_mock.method = 'DELETE'
        
        assert permiso.has_permission(request_mock, view=None) is False

    def test_operario_solo_lectura(self, permiso, request_mock):
        """El Operador de Máquina (OPR) puede leer (GET) pero no escribir (POST)."""
        request_mock.user.rol = User.Rol.OPERARIO
        request_mock.method = 'GET'
        assert permiso.has_permission(request_mock, view=None) is True
        
        request_mock.method = 'POST'
        assert permiso.has_permission(request_mock, view=None) is False

    def test_jefe_puede_modificar(self, permiso, request_mock):
        """El Jefe de Producción (JPR) puede alterar registros (PUT) sin problema."""
        request_mock.user.rol = User.Rol.JEFE_PRODUCCION
        request_mock.method = 'PUT'
        
        assert permiso.has_permission(request_mock, view=None) is True
