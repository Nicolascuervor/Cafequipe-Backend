import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.inventory.models import (
    Bodega, Producto, StockBodega, 
    SubCategoria, CategoriaPrincipal
)

@pytest.mark.django_db
class TestStockBodegaModel:

    @pytest.fixture
    def data_base(self):

        jefe = User.objects.create_user(email='jefe_test@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA)
        bodega = Bodega.objects.create(nombre='Bodega Test', ubicacion='Ubicacion Test', administrador=jefe)
        sub_cat = SubCategoria.objects.create(nombre='Insumos Basicos')
        
        producto = Producto.objects.create(
            nombre='Café en Grano',
            categoria_principal=CategoriaPrincipal.MATERIA_PRIMA,
            sub_categoria=sub_cat,
            punto_reorden=Decimal('15.0000')
        )
        return bodega, producto

    def test_calculo_stock_proyectado(self, data_base):

        bodega, producto = data_base

        stock = StockBodega(
            bodega=bodega,
            producto=producto,
            stock_disponible=Decimal('10.0000'),
            pedidos_abiertos=Decimal('5.0000'),
            ordenes_atrasadas=Decimal('2.0000')
        )

        assert stock.stock_proyectado == Decimal('13.0000')

    def test_propiedad_requiere_reorden(self, data_base):

        bodega, producto = data_base

        stock_bajo = StockBodega(
            bodega=bodega, producto=producto,
            stock_disponible=Decimal('10.0000'),
            pedidos_abiertos=Decimal('5.0000'),
            ordenes_atrasadas=Decimal('2.0000')
        )
        assert stock_bajo.requiere_reorden is True
        stock_alto = StockBodega(
            bodega=bodega, producto=producto,
            stock_disponible=Decimal('20.0000'),
            pedidos_abiertos=Decimal('0.0000'),
            ordenes_atrasadas=Decimal('0.0000')
        )
        assert stock_alto.requiere_reorden is False

    def test_error_categoria_no_admitida(self, data_base):

        bodega, producto = data_base

        bodega.catalogo_admitido = [CategoriaPrincipal.PRODUCTO]
        bodega.save()


        stock_invalido = StockBodega(
            bodega=bodega,
            producto=producto
        )

        with pytest.raises(ValidationError) as error_info:
            stock_invalido.clean()

        mensaje_error = str(error_info.value)
        assert 'no admite productos de tipo' in mensaje_error
