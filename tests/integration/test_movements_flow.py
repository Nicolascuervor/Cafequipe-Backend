import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import CategoriaPrincipal, UnidadMedida, SubCategoria, Producto, Bodega

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestMovementsFlow:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        # Usuarios
        self.jefe_bodega = User.objects.create_user(
            email='jefebodega@cafequipe.com', password='Password123!',
            rol=User.Rol.JEFE_BODEGA, first_name='Juan', last_name='Jefe'
        )
        self.operario = User.objects.create_user(
            email='operario@cafequipe.com', password='Password123!',
            rol=User.Rol.OPERARIO, first_name='Pedro', last_name='Operario'
        )
        
        # Datos base de inventario
        self.subcategoria = SubCategoria.objects.create(nombre='Insumos Básicos')
        self.producto_cafe = Producto.objects.create(
            nombre='Café Verde',
            categoria_principal=CategoriaPrincipal.MATERIA_PRIMA,
            unidad_medida=UnidadMedida.KILOGRAMO,
            sub_categoria=self.subcategoria,
            costo_unitario='5000.00'
        )
        self.bodega_principal = Bodega.objects.create(
            nombre='Bodega Principal',
            ubicacion='Planta 1',
            administrador=self.jefe_bodega,
            permite_stock_negativo=False
        )
        self.bodega_principal.catalogo_admitido = [CategoriaPrincipal.MATERIA_PRIMA]
        self.bodega_principal.save()

        # URLs (Asumiendo que seguirán el estándar REST)
        # Nota: Estas URLs fallarán hasta que se implemente la vista y el enrutador correspondientes.
        self.recepciones_url = '/api/v1/movements/recepciones/'
        self.movimientos_url = '/api/v1/movements/historial/'

    def test_cp023_registro_exitoso_recepcion(self, api_client):
        """CP-023: Registro exitoso de recepción de mercancía."""
        api_client.force_authenticate(user=self.jefe_bodega)
        payload = {
            'bodega': str(self.bodega_principal.id),
            'detalles': [
                {
                    'producto': str(self.producto_cafe.id),
                    'cantidad': '200.00',
                    'costo_unitario_ingreso': '5000.00',
                    'lote_proveedor': 'LOTE-2026-A'
                }
            ],
            'proveedor': 'Proveedor XYZ',
            'observaciones': 'Ingreso de materia prima'
        }
        response = api_client.post(self.recepciones_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_cp024_recepcion_producto_no_registrado(self, api_client):
        """CP-024: Recepción con producto no registrado."""
        api_client.force_authenticate(user=self.jefe_bodega)
        import uuid
        payload = {
            'bodega': str(self.bodega_principal.id),
            'detalles': [
                {
                    'producto': str(uuid.uuid4()), # UUID inexistente
                    'cantidad': '100.00'
                }
            ]
        }
        response = api_client.post(self.recepciones_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cp044_registro_automatico_movimiento_entrada(self, api_client):
        """CP-044: Registro automático de movimiento de entrada tras recepción."""
        api_client.force_authenticate(user=self.jefe_bodega)
        # 1. Crear recepción
        payload_recepcion = {
            'bodega': str(self.bodega_principal.id),
            'detalles': [{'producto': str(self.producto_cafe.id), 'cantidad': '100.00'}]
        }
        recepcion_response = api_client.post(self.recepciones_url, payload_recepcion, format='json')
        
        # 2. Verificar si se generó el movimiento en el historial
        response = api_client.get(self.movimientos_url)
        # Asumiendo que el GET list retorna un paginador o lista directa
        resultados = response.json().get('results', response.json())
        movimiento_encontrado = any(
            m['tipo'] == 'ENTRADA' and m['producto'] == str(self.producto_cafe.id)
            for m in resultados if type(m) == dict
        )
        assert movimiento_encontrado == True

    def test_cp047_filtrado_movimientos(self, api_client):
        """CP-047: Filtrado de movimientos por producto, tipo y fecha."""
        api_client.force_authenticate(user=self.jefe_bodega)
        # Enviar petición con query params
        url_con_filtros = f"{self.movimientos_url}?producto={self.producto_cafe.id}&tipo=ENTRADA"
        response = api_client.get(url_con_filtros)
        
        # Debe responder un 200 OK
        assert response.status_code == status.HTTP_200_OK
