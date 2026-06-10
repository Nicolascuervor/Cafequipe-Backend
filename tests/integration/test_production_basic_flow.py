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
        # 1. Creamos al Jefe de Producción que tiene permisos para crear recetas
        self.jefe_produccion = User.objects.create_user(
            email='jefeproduccion@cafequipe.com',
            password='Password123!',
            rol=User.Rol.JEFE_PRODUCCION
        )
        
        # 2. Creamos una Subcategoría genérica necesaria para crear productos
        self.subcat = SubCategoria.objects.create(nombre='Genérica', descripcion='Gen')
        
        # 3. Creamos un "Producto Terminado" (PR) válido para ser fabricado
        self.producto_terminado = Producto.objects.create(
            nombre='Galletas de Chocolate',
            categoria_principal=CategoriaPrincipal.PRODUCTO, # PR
            unidad_medida=UnidadMedida.PAQUETE,
            sub_categoria=self.subcat
        )
        
        # 4. Creamos una "Materia Prima" (MP) válida para ser usada como ingrediente
        self.materia_prima = Producto.objects.create(
            nombre='Harina de Trigo',
            categoria_principal=CategoriaPrincipal.MATERIA_PRIMA, # MP
            unidad_medida=UnidadMedida.KILOGRAMO,
            sub_categoria=self.subcat
        )
        
        # 5. Obtenemos la URL de la vista de recetas (nuestro endpoint)
        # El nombre 'recetas-list' es el estándar generado por el DefaultRouter de DRF
        self.recetas_url = reverse('recetas-list')

    def test_creacion_receta_y_asignacion_ingrediente_exitosa(self, api_client):
        # ESCENARIO 1: Camino feliz
        api_client.force_authenticate(user=self.jefe_produccion)
        
        # Armamos el paquete de datos con la receta principal y sus ingredientes anidados
        payload = {
            'producto_terminado': str(self.producto_terminado.id),
            'rendimiento_base': '10.0',
            'instrucciones': 'Mezclar la harina y hornear',
            'activa': True,
            'ingredientes': [
                {
                    'producto_insumo': str(self.materia_prima.id), # MP válida
                    'cantidad_necesaria': '2.5'
                }
            ]
        }
        
        response = api_client.post(self.recetas_url, payload, format='json')
        
        # El sistema debe aceptar la receta y el ingrediente (HTTP 201 Created)
        assert response.status_code == status.HTTP_201_CREATED
        # Verificamos que se haya guardado exactamente 1 ingrediente
        assert len(response.json()['ingredientes']) == 1

    def test_falla_al_crear_receta_para_materia_prima(self, api_client):
        # ESCENARIO 2: Regla de negocio - No se puede fabricar lo que es Materia Prima
        api_client.force_authenticate(user=self.jefe_produccion)
        
        payload = {
            'producto_terminado': str(self.materia_prima.id), # Intentamos fabricar "Harina"
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
        
        # El sistema debe bloquear la acción (HTTP 400 Bad Request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # El mensaje de error debe indicar que el problema es el 'producto_terminado'
        assert 'producto_terminado' in response.json()

    def test_falla_al_usar_producto_terminado_como_ingrediente(self, api_client):
        # ESCENARIO 3: Regla de negocio - Un Producto Terminado no debe usarse como materia prima
        api_client.force_authenticate(user=self.jefe_produccion)
        
        payload = {
            'producto_terminado': str(self.producto_terminado.id),
            'rendimiento_base': '10.0',
            'instrucciones': 'Intentando hacer galletas usando galletas como masa',
            'activa': True,
            'ingredientes': [
                {
                    'producto_insumo': str(self.producto_terminado.id), # Intentamos usar "Galletas" como ingrediente
                    'cantidad_necesaria': '2.5'
                }
            ]
        }
        
        response = api_client.post(self.recetas_url, payload, format='json')
        
        # El sistema detecta que el insumo no es válido y bloquea la creación
        assert response.status_code == status.HTTP_400_BAD_REQUEST
