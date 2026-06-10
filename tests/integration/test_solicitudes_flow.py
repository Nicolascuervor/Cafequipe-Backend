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
class TestSolicitudesFlow:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        # Usuarios
        self.jefe_bodega = User.objects.create_user(
            email='jefebodega2@cafequipe.com', password='Password123!',
            rol=User.Rol.JEFE_BODEGA, first_name='Ana', last_name='Bodega'
        )
        self.operario = User.objects.create_user(
            email='operario2@cafequipe.com', password='Password123!',
            rol=User.Rol.OPERARIO, first_name='Luis', last_name='Operario'
        )
        
        # Datos base de inventario
        self.subcategoria = SubCategoria.objects.create(nombre='Insumos Operativos')
        self.producto_filtro = Producto.objects.create(
            nombre='Filtros de Café',
            categoria_principal=CategoriaPrincipal.INSUMO,
            unidad_medida=UnidadMedida.UNIDAD,
            sub_categoria=self.subcategoria,
            costo_unitario='150.00'
        )
        self.producto_bolsa = Producto.objects.create(
            nombre='Bolsas Empaque',
            categoria_principal=CategoriaPrincipal.INSUMO,
            unidad_medida=UnidadMedida.UNIDAD,
            sub_categoria=self.subcategoria,
            costo_unitario='200.00'
        )
        self.bodega = Bodega.objects.create(
            nombre='Bodega Insumos',
            ubicacion='Planta 2',
            administrador=self.jefe_bodega,
            permite_stock_negativo=False
        )

        # URLs
        self.solicitudes_url = '/api/v1/movements/solicitudes/'

    def test_cp027_creacion_solicitud_interna_operario(self, api_client):
        """CP-027: Creación de solicitud interna de insumos por Operario."""
        api_client.force_authenticate(user=self.operario)
        payload = {
            'detalles': [
                {
                    'producto': str(self.producto_filtro.id),
                    'cantidad': '100.00'
                }
            ],
            'motivo': 'Reabastecimiento estación de filtrado'
        }
        response = api_client.post(self.solicitudes_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_cp028_multiples_productos_en_solicitud(self, api_client):
        """CP-028: Múltiples productos en una sola solicitud."""
        api_client.force_authenticate(user=self.operario)
        payload = {
            'detalles': [
                {'producto': str(self.producto_filtro.id), 'cantidad': '100.00'},
                {'producto': str(self.producto_bolsa.id), 'cantidad': '50.00'}
            ],
            'motivo': 'Material para semana 2'
        }
        response = api_client.post(self.solicitudes_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        # Verificar que se guardaron 2 detalles
        assert len(response.json().get('detalles', [])) == 2

    def test_cp029_solicitud_cantidad_cero_negativa(self, api_client):
        """CP-029: Solicitud con cantidad cero o negativa."""
        api_client.force_authenticate(user=self.operario)
        payload = {
            'detalles': [
                {'producto': str(self.producto_filtro.id), 'cantidad': '0.00'},
                {'producto': str(self.producto_bolsa.id), 'cantidad': '-5.00'}
            ]
        }
        response = api_client.post(self.solicitudes_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cp030_solicitud_insumo_no_disponible(self, api_client):
        """CP-030: Solicitud con insumo no disponible en catálogo (ID incorrecto)."""
        api_client.force_authenticate(user=self.operario)
        import uuid
        payload = {
            'detalles': [{'producto': str(uuid.uuid4()), 'cantidad': '10.00'}]
        }
        response = api_client.post(self.solicitudes_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cp033_aprobacion_solicitud_jefe_bodega(self, api_client):
        """CP-033: Aprobación de solicitud por Jefe de Bodega."""
        # 1. Crear solicitud por operario
        api_client.force_authenticate(user=self.operario)
        res_solicitud = api_client.post(self.solicitudes_url, {
            'detalles': [{'producto': str(self.producto_filtro.id), 'cantidad': '10.00'}]
        }, format='json')
        solicitud_id = res_solicitud.json().get('id', 'dummy-id')
        
        # 2. Jefe de bodega la aprueba
        api_client.force_authenticate(user=self.jefe_bodega)
        aprobar_url = f"{self.solicitudes_url}{solicitud_id}/aprobar/"
        response = api_client.post(aprobar_url, {}, format='json')
        
        assert response.status_code == status.HTTP_200_OK

    def test_cp034_rechazo_solicitud_con_motivo(self, api_client):
        """CP-034: Rechazo de solicitud con motivo."""
        # 1. Crear solicitud
        api_client.force_authenticate(user=self.operario)
        res_solicitud = api_client.post(self.solicitudes_url, {
            'detalles': [{'producto': str(self.producto_filtro.id), 'cantidad': '10.00'}]
        }, format='json')
        solicitud_id = res_solicitud.json().get('id', 'dummy-id')
        
        # 2. Jefe rechaza
        api_client.force_authenticate(user=self.jefe_bodega)
        rechazar_url = f"{self.solicitudes_url}{solicitud_id}/rechazar/"
        payload = {'motivo_rechazo': 'No hay stock disponible actualmente'}
        response = api_client.post(rechazar_url, payload, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get('estado') == 'RECHAZADA'

    def test_cp035_cancelar_solicitud(self, api_client):
        """CP-035: Cancelación de solicitud con justificación."""
        api_client.force_authenticate(user=self.operario)
        res_solicitud = api_client.post(self.solicitudes_url, {
            'detalles': [{'producto': str(self.producto_filtro.id), 'cantidad': '10.00'}]
        }, format='json')
        solicitud_id = res_solicitud.json().get('id')
        
        cancelar_url = f"{self.solicitudes_url}{solicitud_id}/cancelar/"
        response = api_client.post(cancelar_url, {'motivo': 'Error de digitación'}, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get('estado') == 'CANCELADA'

    def test_cp032_historial_solicitudes_propias(self, api_client):
        """CP-032: Consulta de historial de solicitudes propias."""
        api_client.force_authenticate(user=self.operario)
        api_client.post(self.solicitudes_url, {
            'detalles': [{'producto': str(self.producto_filtro.id), 'cantidad': '10.00'}]
        }, format='json')
        
        response = api_client.get(self.solicitudes_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0
        
    def test_cp045_cp046_registro_movimiento_salida_automatico(self, api_client):
        """CP-045 y CP-046: Movimiento automático de SALIDA y clasificación correcta."""
        api_client.force_authenticate(user=self.operario)
        res_solicitud = api_client.post(self.solicitudes_url, {
            'detalles': [{'producto': str(self.producto_filtro.id), 'cantidad': '5.00'}]
        }, format='json')
        solicitud_id = res_solicitud.json().get('id')
        
        api_client.force_authenticate(user=self.jefe_bodega)
        aprobar_url = f"{self.solicitudes_url}{solicitud_id}/aprobar/"
        api_client.post(aprobar_url, {}, format='json')
        
        # Verificar movimientos
        mov_url = '/api/v1/movements/historial/'
        response = api_client.get(mov_url)
        resultados = response.json().get('results', response.json())
        movimientos = [m for m in resultados if type(m) == dict and m.get('solicitud') == solicitud_id]
        
        assert len(movimientos) == 1
        assert movimientos[0]['tipo'] == 'SALIDA'
        assert float(movimientos[0]['cantidad']) == 5.00
