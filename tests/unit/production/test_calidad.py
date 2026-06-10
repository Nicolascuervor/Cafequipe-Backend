import pytest
from django.db import IntegrityError
from apps.users.models import User
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal
from apps.production.models import (
    Receta, OrdenProduccion, ParametroCalidad,
    ControlCalidadLote, ValorParametroCalidad, TipoParametro
)

@pytest.mark.django_db
class TestControlCalidadModel:

    @pytest.fixture
    def data_base(self):
        """Prepara el ecosistema para poder crear una orden de producción."""
        responsable = User.objects.create_user(
            email='jefe@cafequipe.com', password='123', rol=User.Rol.JEFE_PRODUCCION
        )
        sub_cat = SubCategoria.objects.create(nombre='Base')
        producto = Producto.objects.create(
            nombre='Café Molido', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=sub_cat
        )
        receta = Receta.objects.create(producto_terminado=producto, rendimiento_base=10.0)
        
        orden = OrdenProduccion.objects.create(
            receta=receta, cantidad_esperada=100.0, responsable=responsable
        )
        return orden

    def test_bitacora_calidad_inicial_str(self, data_base):
        """
        Prueba que el control de calidad inicie sin aprobación (False por defecto)
        y muestre correctamente el estado en su representación texto.
        """
        orden = data_base
        
        control = ControlCalidadLote.objects.create(
            orden_produccion=orden
        )
        
        assert control.aprobado_final is False
        assert 'RECHAZADO' in str(control)

    def test_valor_parametro_unico_por_control(self, data_base):
        """
        Prueba que no se pueda registrar el mismo parámetro dos veces en la 
        misma bitácora de calidad (violación de unique_together).
        """
        orden = data_base
        control = ControlCalidadLote.objects.create(orden_produccion=orden)
        
        parametro = ParametroCalidad.objects.create(
            nombre='Humedad (%)', tipo_dato=TipoParametro.DECIMAL
        )

        # 1. Primer registro del parámetro de humedad (Exitoso)
        ValorParametroCalidad.objects.create(
            control=control, parametro=parametro, valor_decimal='12.5'
        )

        # 2. Intento de sobreescribir o duplicar el mismo parámetro en la misma orden
        with pytest.raises(IntegrityError):
            ValorParametroCalidad.objects.create(
                control=control, parametro=parametro, valor_decimal='12.8'
            )
