import pytest
from decimal import Decimal
from django.db import IntegrityError
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal
from apps.production.models import Receta, IngredienteReceta

@pytest.mark.django_db
class TestRecetaModel:

    @pytest.fixture
    def data_base(self):

        sub_cat = SubCategoria.objects.create(nombre='Base')
        producto_final = Producto.objects.create(
            nombre='Mocaccino', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=sub_cat
        )
        insumo = Producto.objects.create(
            nombre='Cacao en Polvo', categoria_principal=CategoriaPrincipal.INSUMO, sub_categoria=sub_cat
        )
        return producto_final, insumo

    def test_receta_activa_y_str(self, data_base):

        producto_final, _ = data_base

        receta = Receta.objects.create(
            producto_terminado=producto_final,
            rendimiento_base=Decimal('1.00')
        )

        assert receta.activa is True
        assert str(receta) == 'Receta para: Mocaccino'

    def test_ingrediente_unico_por_receta(self, data_base):

        producto_final, insumo = data_base

        receta = Receta.objects.create(producto_terminado=producto_final, rendimiento_base=Decimal('1.00'))

        IngredienteReceta.objects.create(
            receta=receta,
            producto_insumo=insumo,
            cantidad_necesaria=Decimal('5.0000')
        )

        with pytest.raises(IntegrityError):
            IngredienteReceta.objects.create(
                receta=receta,
                producto_insumo=insumo,

                cantidad_necesaria=Decimal('2.0000') 
            )

    def test_ingrediente_str(self, data_base):

        producto_final, insumo = data_base
        receta = Receta.objects.create(producto_terminado=producto_final, rendimiento_base=Decimal('1.00'))
        
        ingrediente = IngredienteReceta.objects.create(
            receta=receta,
            producto_insumo=insumo,
            cantidad_necesaria=Decimal('15.5000')
        )


        assert str(ingrediente) == '15.5000 x Cacao en Polvo'
