import pytest
from decimal import Decimal
from django.db import IntegrityError
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal
from apps.production.models import Receta, IngredienteReceta

@pytest.mark.django_db
class TestRecetaModel:

    @pytest.fixture
    def data_base(self):
        """Fixture base para instanciar rápidamente productos e insumos."""
        sub_cat = SubCategoria.objects.create(nombre='Base')
        producto_final = Producto.objects.create(
            nombre='Mocaccino', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=sub_cat
        )
        insumo = Producto.objects.create(
            nombre='Cacao en Polvo', categoria_principal=CategoriaPrincipal.INSUMO, sub_categoria=sub_cat
        )
        return producto_final, insumo

    def test_receta_activa_y_str(self, data_base):
        """
        Prueba que una receta nueva nazca activa por defecto
        y tenga un formato de texto amigable en el backend.
        """
        producto_final, _ = data_base

        receta = Receta.objects.create(
            producto_terminado=producto_final,
            rendimiento_base=Decimal('1.00')
        )

        assert receta.activa is True
        assert str(receta) == 'Receta para: Mocaccino'

    def test_ingrediente_unico_por_receta(self, data_base):
        """
        Prueba que la base de datos bloquee con IntegrityError la asignación duplicada 
        de un mismo insumo dentro de una misma receta (regla unique_together).
        """
        producto_final, insumo = data_base

        receta = Receta.objects.create(producto_terminado=producto_final, rendimiento_base=Decimal('1.00'))

        # 1. Asignamos el ingrediente la primera vez (Debe ser exitoso)
        IngredienteReceta.objects.create(
            receta=receta,
            producto_insumo=insumo,
            cantidad_necesaria=Decimal('5.0000')
        )

        # 2. Intentamos volver a asignar EXACTAMENTE el mismo insumo a la misma receta
        with pytest.raises(IntegrityError):
            IngredienteReceta.objects.create(
                receta=receta,
                producto_insumo=insumo,
                # La cantidad distinta no importa, lo que importa es que el producto ya está en la receta
                cantidad_necesaria=Decimal('2.0000') 
            )

    def test_ingrediente_str(self, data_base):
        """
        Prueba la correcta representación en texto de la línea de receta (el ingrediente).
        """
        producto_final, insumo = data_base
        receta = Receta.objects.create(producto_terminado=producto_final, rendimiento_base=Decimal('1.00'))
        
        ingrediente = IngredienteReceta.objects.create(
            receta=receta,
            producto_insumo=insumo,
            cantidad_necesaria=Decimal('15.5000')
        )

        # Formato de visualización exigido por el modelo
        assert str(ingrediente) == '15.5000 x Cacao en Polvo'
