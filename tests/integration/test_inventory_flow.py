import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import CategoriaPrincipal, UnidadMedida, SubCategoria

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestInventoryFlow:

    @pytest.fixture(autouse=True)
    def setup_data(self):

        self.operario = User.objects.create_user(
            email='operario@cafequipe.com',
            password='Password123!',
            rol=User.Rol.OPERARIO,
            first_name='Pepe',
            last_name='Operario'
        )

        self.jefe_bodega = User.objects.create_user(
            email='jefe@cafequipe.com',
            password='Password123!',
            rol=User.Rol.JEFE_BODEGA,
            first_name='Ana',
            last_name='Jefa'
        )

        self.subcategoria_url = reverse('inventory:subcategoria-list')
        self.producto_url = reverse('inventory:producto-list')
        self.bodega_url = reverse('inventory:bodega-list')

    def test_creacion_subcategoria_exitosa(self, api_client):

        api_client.force_authenticate(user=self.jefe_bodega)

        response = api_client.post(self.subcategoria_url, {
            'nombre': 'Lácteos',
            'descripcion': 'Insumos derivados de la leche'
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['nombre'] == 'Lácteos'

    def test_creacion_producto_exitoso(self, api_client):

        subcategoria = SubCategoria.objects.create(
            nombre='Frutas', 
            descripcion='Frutas frescas'
        )
        
        api_client.force_authenticate(user=self.jefe_bodega)

        payload_producto = {
            'nombre': 'Manzanas Frescas',
            'categoria_principal': CategoriaPrincipal.MATERIA_PRIMA,
            'unidad_medida': UnidadMedida.KILOGRAMO,
            'sub_categoria': str(subcategoria.id),
            'costo_unitario': '1.50',
            'inventario_seguridad': '10.0',
            'punto_reorden': '5.0'
        }
        
        response = api_client.post(self.producto_url, payload_producto, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['nombre'] == 'Manzanas Frescas'

    def test_creacion_bodega_falla_con_administrador_operario(self, api_client):

        api_client.force_authenticate(user=self.jefe_bodega)

        payload_bodega = {
            'nombre': 'Bodega de Pruebas',
            'ubicacion': 'Planta Principal',
            'administrador': str(self.operario.id),
            'permite_stock_negativo': False
        }
        
        response = api_client.post(self.bodega_url, payload_bodega, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        assert 'administrador' in response.json()

    def test_creacion_bodega_exitosa_con_jefe_bodega(self, api_client):

        api_client.force_authenticate(user=self.jefe_bodega)

        payload_bodega = {
            'nombre': 'Bodega Norte',
            'ubicacion': 'Almacén Central',
            'administrador': str(self.jefe_bodega.id),
            'permite_stock_negativo': False,
            'catalogo_admitido': [CategoriaPrincipal.MATERIA_PRIMA, CategoriaPrincipal.INSUMO]
        }
        
        response = api_client.post(self.bodega_url, payload_bodega, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['nombre'] == 'Bodega Norte'