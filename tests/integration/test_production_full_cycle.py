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

        self.jefe_produccion = User.objects.create_user(email='jefeprod@cafequipe.com', password='pw', rol=User.Rol.JEFE_PRODUCCION)

        self.gerente_bodega = User.objects.create_user(email='gerente@cafequipe.com', password='pw', rol=User.Rol.GERENTE)

        subcat = SubCategoria.objects.create(nombre='Insumos', descripcion='Generico')
        self.materia_prima = Producto.objects.create(nombre='Azúcar', categoria_principal=CategoriaPrincipal.MATERIA_PRIMA, unidad_medida=UnidadMedida.KILOGRAMO, sub_categoria=subcat)
        self.producto_terminado = Producto.objects.create(nombre='Dulces', categoria_principal=CategoriaPrincipal.PRODUCTO, unidad_medida=UnidadMedida.PAQUETE, sub_categoria=subcat)

        self.receta = Receta.objects.create(producto_terminado=self.producto_terminado, rendimiento_base=10.0, activa=True)
        IngredienteReceta.objects.create(receta=self.receta, producto_insumo=self.materia_prima, cantidad_necesaria=5.0)

        self.bodega_origen = Bodega.objects.create(nombre='Bodega Insumos', ubicacion='Norte', administrador=self.gerente_bodega)
        self.bodega_destino = Bodega.objects.create(nombre='Bodega Principal', ubicacion='Sur', administrador=self.gerente_bodega)

        StockBodega.objects.create(
            bodega=self.bodega_origen, 
            producto=self.materia_prima, 
            stock_disponible=50.0, 
            codigo_lote='LOTE-AZU-001'
        )

    def test_ciclo_completo_produccion(self, api_client):

        api_client.force_authenticate(user=self.jefe_produccion)
        orden_url = reverse('ordenes-list')

        response_orden = api_client.post(orden_url, {
            'receta': self.receta.id,
            'cantidad_esperada': '20.0'
        }, format='json')
        
        assert response_orden.status_code == status.HTTP_201_CREATED
        orden_id = response_orden.json()['id']

        from apps.production.models import TicketInsumo
        ticket = TicketInsumo.objects.get(orden_produccion_id=orden_id)
        assert ticket.detalles.first().cantidad_solicitada == 10.0

        orden_detail_url = reverse('ordenes-detail', args=[orden_id])

        resp_fail = api_client.patch(orden_detail_url, {'estado': EstadoOrden.COMPLETADA}, format='json')

        assert resp_fail.status_code == status.HTTP_400_BAD_REQUEST

        api_client.force_authenticate(user=self.gerente_bodega)
        entregar_ticket_url = reverse('tickets-entregar', args=[ticket.id])

        resp_entrega = api_client.post(entregar_ticket_url, {
            'bodega_origen_id': self.bodega_origen.id
        }, format='json')
        
        assert resp_entrega.status_code == status.HTTP_200_OK

        stock_azucar = StockBodega.objects.get(bodega=self.bodega_origen, producto=self.materia_prima)
        assert float(stock_azucar.stock_disponible) == 40.0

        api_client.force_authenticate(user=self.jefe_produccion)
        calidad_url = reverse('control_calidad-list')
        
        resp_calidad = api_client.post(calidad_url, {
            'orden_produccion': orden_id,
            'aprobado_final': True,
            'valores': []
        }, format='json')
        
        assert resp_calidad.status_code == status.HTTP_201_CREATED

        resp_cierre = api_client.patch(orden_detail_url, {
            'estado': EstadoOrden.COMPLETADA,
            'bodega_destino': self.bodega_destino.id,
            'cantidad_obtenida': '20.0'
        }, format='json')
        
        assert resp_cierre.status_code == status.HTTP_200_OK

        stock_dulces = StockBodega.objects.get(bodega=self.bodega_destino, producto=self.producto_terminado)
        assert float(stock_dulces.stock_disponible) == 20.0