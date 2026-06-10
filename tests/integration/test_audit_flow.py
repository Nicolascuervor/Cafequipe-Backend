import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import CategoriaPrincipal, SubCategoria, Producto

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestAuditFlow:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.gerente = User.objects.create_user(
            email='gerente_audit@cafequipe.com', password='Password123!',
            rol=User.Rol.GERENTE, first_name='Carlos', last_name='G'
        )
        self.operario = User.objects.create_user(
            email='operario_audit@cafequipe.com', password='Password123!',
            rol=User.Rol.OPERARIO, first_name='Juan', last_name='Pérez'
        )
        
        self.audit_url = '/api/v1/audit/logs/'
        self.productos_url = reverse('inventory:producto-list')
        self.subcategoria = SubCategoria.objects.create(nombre='SubCat Audit')

    def test_cp064_registro_automatico_auditoria(self, api_client):
        """CP-064: Registro automático de acción en bitácora de auditoría."""
        api_client.force_authenticate(user=self.gerente)
        
        # Realizar acción
        payload = {
            'nombre': 'Cafe Audit',
            'categoria_principal': CategoriaPrincipal.PRODUCTO,
            'sub_categoria': str(self.subcategoria.id),
            'costo_unitario': '150.00',
            'inventario_seguridad': '10',
            'punto_reorden': '20'
        }
        res_prod = api_client.post(self.productos_url, payload, format='json')
        assert res_prod.status_code == status.HTTP_201_CREATED
        
        # Verificar auditoría
        res_audit = api_client.get(self.audit_url)
        assert res_audit.status_code == status.HTTP_200_OK
        data = res_audit.json().get('results', res_audit.json())
        assert len(data) > 0
        assert data[0]['action'] == 'PRODUCTO_CREATED'
        assert data[0]['user'] == str(self.gerente.id)
        assert 'Cafe Audit' in data[0]['description']

    def test_cp065_consulta_bitacora_filtros(self, api_client):
        """CP-065: Consulta de bitácora con filtros por usuario."""
        # Se asume que el test anterior (u otro) generó auditoría, pero los tests de DB son aislados, así que generamos una acción primero.
        api_client.force_authenticate(user=self.gerente)
        payload = {
            'nombre': 'Cafe Audit 2',
            'categoria_principal': CategoriaPrincipal.PRODUCTO,
            'sub_categoria': str(self.subcategoria.id),
            'costo_unitario': '150.00',
            'inventario_seguridad': '10',
            'punto_reorden': '20'
        }
        api_client.post(self.productos_url, payload, format='json')
        
        # Filtrar
        res_audit = api_client.get(f"{self.audit_url}?user={self.gerente.id}")
        assert res_audit.status_code == status.HTTP_200_OK
        data = res_audit.json().get('results', res_audit.json())
        assert len(data) > 0
        assert all(item['user'] == str(self.gerente.id) for item in data)

    def test_cp066_cp067_inmutabilidad(self, api_client):
        """CP-066 y CP-067: Intento de modificación y verificación de inmutabilidad."""
        api_client.force_authenticate(user=self.gerente)
        payload = {
            'nombre': 'Cafe Audit 3',
            'categoria_principal': CategoriaPrincipal.PRODUCTO,
            'sub_categoria': str(self.subcategoria.id),
            'costo_unitario': '150.00',
            'inventario_seguridad': '10',
            'punto_reorden': '20'
        }
        api_client.post(self.productos_url, payload, format='json')
        
        # Obtener log
        res_audit = api_client.get(self.audit_url)
        log_id = res_audit.json().get('results', res_audit.json())[0]['id']
        
        # Intentar modificar (debe fallar 405 Method Not Allowed ya que solo hay GET)
        res_patch = api_client.patch(f"{self.audit_url}{log_id}/", {'action': 'FALSO'}, format='json')
        assert res_patch.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
        
        # Intentar eliminar con otro rol
        api_client.force_authenticate(user=self.operario)
        res_delete = api_client.delete(f"{self.audit_url}{log_id}/")
        assert res_delete.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    def test_cp068_bitacora_sin_resultados(self, api_client):
        """CP-068: Bitácora sin resultados según filtros aplicados."""
        api_client.force_authenticate(user=self.gerente)
        # Filtro de búsqueda que no arroja resultados
        res_audit = api_client.get(f"{self.audit_url}?search=FALSO_ERROR")
        assert res_audit.status_code == status.HTTP_200_OK
        data = res_audit.json().get('results', res_audit.json())
        assert len(data) == 0
