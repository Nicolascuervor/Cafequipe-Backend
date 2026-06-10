import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal, UnidadMedida

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestProductionBasicFlow:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):

        self.jefe_produccion = User.objects.create_user(
            email='jefeproduccion@cafequipe.com',
            password='Password123!',
            rol=User.Rol.JEFE_PRODUCCION
        )

        self.subcat = SubCategoria.objects.create(nombre='Genérica', descripcion='Gen')

        self.producto_terminado = Producto.objects.create(
            nombre='Galletas de Chocolate',
            categoria_principal=CategoriaPrincipal.PRODUCTO, # PR
            unidad_medida=UnidadMedida.PAQUETE,
            sub_categoria=self.subcat
        )

        self.materia_prima = Producto.objects.create(
            nombre='Harina de Trigo',
            categoria_principal=CategoriaPrincipal.MATERIA_PRIMA, # MP
            unidad_medida=UnidadMedida.KILOGRAMO,
            sub_categoria=self.subcat
        )

        self.recetas_url = reverse('recetas-list')

    def test_creacion_receta_y_asignacion_ingrediente_exitosa(self, api_client):

        api_client.force_authenticate(user=self.jefe_produccion)

        payload = {
            'producto_terminado': str(self.producto_terminado.id),
            'rendimiento_base': '10.0',
            'instrucciones': 'Mezclar la harina y hornear',
            'activa': True,
            'ingredientes': [
                {
                    'producto_insumo': str(self.materia_prima.id),
                    'cantidad_necesaria': '2.5'
                }
            ]
        }
        
        response = api_client.post(self.recetas_url, payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        assert len(response.json()['ingredientes']) == 1

    def test_falla_al_crear_receta_para_materia_prima(self, api_client):

        api_client.force_authenticate(user=self.jefe_produccion)
        
        payload = {
            'producto_terminado': str(self.materia_prima.id),
            'rendimiento_base': '10.0',
            'instrucciones': 'Imposible fabricar esto aquí',
            'activa': True,
            'ingredientes': [
                {
                    'producto_insumo': str(self.materia_prima.id),
                    'cantidad_necesaria': '2.5'
                }
            ]
        }
        
        response = api_client.post(self.recetas_url, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        assert 'producto_terminado' in response.json()

    def test_falla_al_usar_producto_terminado_como_ingrediente(self, api_client):

        api_client.force_authenticate(user=self.jefe_produccion)
        
        payload = {
            'producto_terminado': str(self.producto_terminado.id),
            'rendimiento_base': '10.0',
            'instrucciones': 'Intentando hacer galletas usando galletas como masa',
            'activa': True,
            'ingredientes': [
                {
                    'producto_insumo': str(self.producto_terminado.id),
                    'cantidad_necesaria': '2.5'
                }
            ]
        }
        
        response = api_client.post(self.recetas_url, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST