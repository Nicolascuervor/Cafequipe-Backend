import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import CategoriaPrincipal, UnidadMedida, SubCategoria

# Fixture para obtener el cliente de DRF, útil para envíos JSON
@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestInventoryFlow:
    
    # Preparación de datos (se ejecuta antes de cada test)
    @pytest.fixture(autouse=True)
    def setup_data(self):
        # Creamos un usuario "Operario" que tiene pocos privilegios
        self.operario = User.objects.create_user(
            email='operario@cafequipe.com',
            password='Password123!',
            rol=User.Rol.OPERARIO,
            first_name='Pepe',
            last_name='Operario'
        )
        
        # Creamos un usuario "Jefe de Bodega" que tiene los privilegios necesarios
        self.jefe_bodega = User.objects.create_user(
            email='jefe@cafequipe.com',
            password='Password123!',
            rol=User.Rol.JEFE_BODEGA,
            first_name='Ana',
            last_name='Jefa'
        )
        
        # Rutas de nuestros endpoints en el API
        self.subcategoria_url = reverse('inventory:subcategoria-list')
        self.producto_url = reverse('inventory:producto-list')
        self.bodega_url = reverse('inventory:bodega-list')

    def test_creacion_subcategoria_exitosa(self, api_client):
        # 1. ESCENARIO: Creación de una Subcategoría.
        # Autenticamos al jefe de bodega directamente (ahorra hacer login real)
        api_client.force_authenticate(user=self.jefe_bodega)
        
        # Enviamos los datos para crear la subcategoría
        response = api_client.post(self.subcategoria_url, {
            'nombre': 'Lácteos',
            'descripcion': 'Insumos derivados de la leche'
        }, format='json')
        
        # Verificamos que se haya creado exitosamente (HTTP 201 Created)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['nombre'] == 'Lácteos'

    def test_creacion_producto_exitoso(self, api_client):
        # 2. ESCENARIO: Creación de un Producto que depende de una subcategoría.
        # Primero necesitamos crear una subcategoría directamente en base de datos
        subcategoria = SubCategoria.objects.create(
            nombre='Frutas', 
            descripcion='Frutas frescas'
        )
        
        api_client.force_authenticate(user=self.jefe_bodega)
        
        # Armamos el paquete de datos del producto
        payload_producto = {
            'nombre': 'Manzanas Frescas',
            'categoria_principal': CategoriaPrincipal.MATERIA_PRIMA,
            'unidad_medida': UnidadMedida.KILOGRAMO,
            'sub_categoria': str(subcategoria.id), # Referenciamos la subcategoría
            'costo_unitario': '1.50',
            'inventario_seguridad': '10.0',
            'punto_reorden': '5.0'
        }
        
        response = api_client.post(self.producto_url, payload_producto, format='json')
        
        # Comprobamos que el producto se creó correctamente
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['nombre'] == 'Manzanas Frescas'

    def test_creacion_bodega_falla_con_administrador_operario(self, api_client):
        # 3. ESCENARIO: Restricción de seguridad al crear Bodega.
        # La regla de negocio dicta que el administrador debe ser GERENTE o JEFE DE BODEGA.
        api_client.force_authenticate(user=self.jefe_bodega)
        
        # Intentamos asignar la bodega al usuario "operario"
        payload_bodega = {
            'nombre': 'Bodega de Pruebas',
            'ubicacion': 'Planta Principal',
            'administrador': str(self.operario.id), # Asignamos al operario
            'permite_stock_negativo': False
        }
        
        response = api_client.post(self.bodega_url, payload_bodega, format='json')
        
        # El sistema debe bloquear esto devolviendo un 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Verificamos que el error nos indique el problema con el campo 'administrador'
        assert 'administrador' in response.json()

    def test_creacion_bodega_exitosa_con_jefe_bodega(self, api_client):
        # 4. ESCENARIO: Camino feliz para crear una bodega.
        api_client.force_authenticate(user=self.jefe_bodega)
        
        # Asignamos correctamente al Jefe de Bodega como administrador
        payload_bodega = {
            'nombre': 'Bodega Norte',
            'ubicacion': 'Almacén Central',
            'administrador': str(self.jefe_bodega.id), # Asignación correcta
            'permite_stock_negativo': False,
            'catalogo_admitido': [CategoriaPrincipal.MATERIA_PRIMA, CategoriaPrincipal.INSUMO]
        }
        
        response = api_client.post(self.bodega_url, payload_bodega, format='json')
        
        # El sistema debe aceptarlo y devolver 201 Created
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['nombre'] == 'Bodega Norte'
