import pytest
from decimal import Decimal
from django.db import IntegrityError
from apps.users.models import User
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal
from apps.production.models import (
    Receta, OrdenProduccion, TicketInsumo, DetalleTicketInsumo, EstadoTicket
)

@pytest.mark.django_db
class TestTicketInsumoModel:

    @pytest.fixture
    def data_base(self):
        responsable = User.objects.create_user(email='jefe@cafequipe.com', password='123', rol=User.Rol.JEFE_PRODUCCION)
        sub_cat = SubCategoria.objects.create(nombre='Base')
        producto = Producto.objects.create(nombre='Café Molido', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=sub_cat)
        insumo = Producto.objects.create(nombre='Grano Crudo', categoria_principal=CategoriaPrincipal.MATERIA_PRIMA, sub_categoria=sub_cat)
        receta = Receta.objects.create(producto_terminado=producto, rendimiento_base=10.0)
        
        orden = OrdenProduccion.objects.create(
            receta=receta, cantidad_esperada=100.0, responsable=responsable
        )
        return orden, insumo

    def test_ticket_estado_inicial(self, data_base):

        orden, _ = data_base
        ticket = TicketInsumo.objects.create(orden_produccion=orden)
        
        assert ticket.estado == EstadoTicket.SOLICITADO
        assert 'Solicitado' in str(ticket)

    def test_detalle_ticket_unico_por_producto(self, data_base):

        orden, insumo = data_base
        ticket = TicketInsumo.objects.create(orden_produccion=orden)

        DetalleTicketInsumo.objects.create(
            ticket=ticket, producto=insumo, cantidad_solicitada=Decimal('50.0')
        )

        with pytest.raises(IntegrityError):
            DetalleTicketInsumo.objects.create(
                ticket=ticket, producto=insumo, cantidad_solicitada=Decimal('10.0')
            )