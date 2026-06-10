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
        """
        Fixture de PyTest que prepara los datos base necesarios (Usuario, Bodega, SubCategoria, Producto)
        para poder crear los stocks en los diferentes tests, evitando repetir código.
        """
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
        """
        Prueba que la fórmula matemática del stock proyectado funcione correctamente:
        Stock Proyectado = Disponible + Pedidos Abiertos - Ordenes Atrasadas
        """
        bodega, producto = data_base

        stock = StockBodega(
            bodega=bodega,
            producto=producto,
            stock_disponible=Decimal('10.0000'),
            pedidos_abiertos=Decimal('5.0000'),
            ordenes_atrasadas=Decimal('2.0000')
        )

        # Cálculo esperado: 10 + 5 - 2 = 13
        assert stock.stock_proyectado == Decimal('13.0000')

    def test_propiedad_requiere_reorden(self, data_base):
        """
        Prueba que la alerta 'requiere_reorden' se active solo cuando el 
        stock proyectado baja del punto de reorden configurado en el producto.
        """
        bodega, producto = data_base
        # El producto de nuestra fixture tiene punto_reorden = 15.0000

        # Caso 1: Stock proyectado (13) es menor que punto_reorden (15) -> DEBE requerir reorden
        stock_bajo = StockBodega(
            bodega=bodega, producto=producto,
            stock_disponible=Decimal('10.0000'),
            pedidos_abiertos=Decimal('5.0000'),
            ordenes_atrasadas=Decimal('2.0000') # Proyectado: 13
        )
        assert stock_bajo.requiere_reorden is True

        # Caso 2: Stock proyectado (20) es mayor que punto_reorden (15) -> NO requiere reorden
        stock_alto = StockBodega(
            bodega=bodega, producto=producto,
            stock_disponible=Decimal('20.0000'),
            pedidos_abiertos=Decimal('0.0000'),
            ordenes_atrasadas=Decimal('0.0000') # Proyectado: 20
        )
        assert stock_alto.requiere_reorden is False

    def test_error_categoria_no_admitida(self, data_base):
        """
        Prueba que el método clean() lance un ValidationError si intentamos
        guardar un producto en una bodega que no admite su categoría.
        """
        bodega, producto = data_base

        # Modificamos la bodega para que SOLO acepte Productos Terminados (restringimos Materia Prima)
        bodega.catalogo_admitido = [CategoriaPrincipal.PRODUCTO]
        bodega.save()

        # Nuestro producto es MATERIA_PRIMA. Intentar asignarlo a la bodega debería fallar.
        stock_invalido = StockBodega(
            bodega=bodega,
            producto=producto
        )

        with pytest.raises(ValidationError) as error_info:
            stock_invalido.clean()
        
        # Validamos que el mensaje de error indique el problema de categorías
        mensaje_error = str(error_info.value)
        assert 'no admite productos de tipo' in mensaje_error
