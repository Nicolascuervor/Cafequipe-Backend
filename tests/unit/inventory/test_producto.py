import pytest
from decimal import Decimal
from django.db import IntegrityError
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal, ClasificacionABC

@pytest.mark.django_db
class TestProductoModel:

    def test_subcategoria_str(self):

        sub = SubCategoria.objects.create(
            nombre='Lácteos y Derivados',
            descripcion='Insumos perecederos que requieren refrigeración.'
        )

        assert str(sub) == 'Lácteos y Derivados'

    def test_producto_decimales(self):

        sub = SubCategoria.objects.create(nombre='Insumos Básicos')
        
        producto = Producto.objects.create(
            nombre='Leche Deslactosada',
            categoria_principal=CategoriaPrincipal.INSUMO,
            sub_categoria=sub,
            costo_unitario=Decimal('3500.50'),
            inventario_seguridad=Decimal('12.3456')
        )


        producto.refresh_from_db()

        assert producto.costo_unitario == Decimal('3500.50')
        assert producto.inventario_seguridad == Decimal('12.3456')

    def test_producto_str(self):

        sub = SubCategoria.objects.create(nombre='Cafés')

        prod_c = Producto.objects.create(
            nombre='Café Standard',
            sub_categoria=sub
        )
        assert str(prod_c) == '[C] Café Standard'
        prod_a = Producto.objects.create(
            nombre='Café Premium de Exportación',
            sub_categoria=sub,
            clasificacion=ClasificacionABC.A
        )
        assert str(prod_a) == '[A] Café Premium de Exportación'
