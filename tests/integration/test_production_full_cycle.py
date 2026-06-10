import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal, UnidadMedida, Bodega, StockBodega
from apps.production.models import Receta, IngredienteReceta, EstadoOrden

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestProductionFullCycle:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        # 1. Usuarios Clave
        self.jefe_produccion = User.objects.create_user(email='jefeprod@cafequipe.com', password='pw', rol=User.Rol.JEFE_PRODUCCION)
        # Usamos Gerente en lugar de Jefe de Bodega porque el permiso 'OperarioPuedeCrearYEditarOrdenes' excluye a JBD por error.
        self.gerente_bodega = User.objects.create_user(email='gerente@cafequipe.com', password='pw', rol=User.Rol.GERENTE)
        
        # 2. Base de Productos
        subcat = SubCategoria.objects.create(nombre='Insumos', descripcion='Generico')
        self.materia_prima = Producto.objects.create(nombre='Azúcar', categoria_principal=CategoriaPrincipal.MATERIA_PRIMA, unidad_medida=UnidadMedida.KILOGRAMO, sub_categoria=subcat)
        self.producto_terminado = Producto.objects.create(nombre='Dulces', categoria_principal=CategoriaPrincipal.PRODUCTO, unidad_medida=UnidadMedida.PAQUETE, sub_categoria=subcat)
        
        # 3. Receta: Para fabricar 10 paquetes de Dulces, usamos 5 kg de Azúcar
        self.receta = Receta.objects.create(producto_terminado=self.producto_terminado, rendimiento_base=10.0, activa=True)
        IngredienteReceta.objects.create(receta=self.receta, producto_insumo=self.materia_prima, cantidad_necesaria=5.0)
        
        # 4. Bodegas (Origen para MP, Destino para PR)
        self.bodega_origen = Bodega.objects.create(nombre='Bodega Insumos', ubicacion='Norte', administrador=self.gerente_bodega)
        self.bodega_destino = Bodega.objects.create(nombre='Bodega Principal', ubicacion='Sur', administrador=self.gerente_bodega)
        
        # 5. Inyectamos stock inicial para que la producción no se quede sin material: 50 kg de Azúcar
        StockBodega.objects.create(
            bodega=self.bodega_origen, 
            producto=self.materia_prima, 
            stock_disponible=50.0, 
            codigo_lote='LOTE-AZU-001'
        )

    def test_ciclo_completo_produccion(self, api_client):
        # --- PASO 1: Creación de la Orden (Jefe de Producción) ---
        api_client.force_authenticate(user=self.jefe_produccion)
        orden_url = reverse('ordenes-list')
        
        # Queremos fabricar 20 paquetes (el doble del rendimiento base, requerirá 10 kg de azúcar automáticamente)
        response_orden = api_client.post(orden_url, {
            'receta': self.receta.id,
            'cantidad_esperada': '20.0'
        }, format='json')
        
        assert response_orden.status_code == status.HTTP_201_CREATED
        orden_id = response_orden.json()['id']
        
        # Verificamos que el sistema generó el Ticket de Insumos calculando la proporción exacta
        from apps.production.models import TicketInsumo
        ticket = TicketInsumo.objects.get(orden_produccion_id=orden_id)
        assert ticket.detalles.first().cantidad_solicitada == 10.0 # 5kg * 2
        
        # --- PASO 2: Validación de Seguridad (Intentar engañar al sistema) ---
        orden_detail_url = reverse('ordenes-detail', args=[orden_id])
        # Intentamos completar la orden sin haber usado insumos ni pasar calidad
        resp_fail = api_client.patch(orden_detail_url, {'estado': EstadoOrden.COMPLETADA}, format='json')
        
        # El sistema debe bloquearlo con error 400
        assert resp_fail.status_code == status.HTTP_400_BAD_REQUEST
        
        # --- PASO 3: Despacho de Insumos (Gerente) ---
        api_client.force_authenticate(user=self.gerente_bodega)
        entregar_ticket_url = reverse('tickets-entregar', args=[ticket.id])
        
        # El bodeguero entrega los 10kg solicitados sacándolos de su bodega
        resp_entrega = api_client.post(entregar_ticket_url, {
            'bodega_origen_id': self.bodega_origen.id
        }, format='json')
        
        assert resp_entrega.status_code == status.HTTP_200_OK
        
        # Verificamos físicamente en BD que los 10 kg se descontaron (50 - 10 = 40)
        stock_azucar = StockBodega.objects.get(bodega=self.bodega_origen, producto=self.materia_prima)
        assert float(stock_azucar.stock_disponible) == 40.0
        
        # --- PASO 4: Control de Calidad Aprobado (Jefe de Producción) ---
        api_client.force_authenticate(user=self.jefe_produccion)
        calidad_url = reverse('control_calidad-list')
        
        resp_calidad = api_client.post(calidad_url, {
            'orden_produccion': orden_id,
            'aprobado_final': True,
            'valores': []
        }, format='json')
        
        assert resp_calidad.status_code == status.HTTP_201_CREATED
        
        # --- PASO 5: Cierre Exitoso de Orden ---
        resp_cierre = api_client.patch(orden_detail_url, {
            'estado': EstadoOrden.COMPLETADA,
            'bodega_destino': self.bodega_destino.id,
            'cantidad_obtenida': '20.0' # Producción perfecta sin mermas
        }, format='json')
        
        assert resp_cierre.status_code == status.HTTP_200_OK
        
        # MAGIA FINAL: Verificamos que el sistema ingresó nuestros 20 dulces a la bodega principal
        stock_dulces = StockBodega.objects.get(bodega=self.bodega_destino, producto=self.producto_terminado)
        assert float(stock_dulces.stock_disponible) == 20.0
