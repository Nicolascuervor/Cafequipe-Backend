import pytest
from datetime import timedelta
from django.utils import timezone
from apps.users.models import User
from apps.inventory.models import Producto, SubCategoria, CategoriaPrincipal
from apps.production.models import Receta, OrdenProduccion, EstadoOrden

@pytest.mark.django_db
class TestOrdenProduccionModel:

    @pytest.fixture
    def data_base(self):

        responsable = User.objects.create_user(
            email='jefe_prod@cafequipe.com', password='123', rol=User.Rol.JEFE_PRODUCCION
        )
        sub_cat = SubCategoria.objects.create(nombre='Productos Finales')

        producto = Producto.objects.create(
            nombre='Café Molido Premium',
            categoria_principal=CategoriaPrincipal.PRODUCTO,
            sub_categoria=sub_cat
        )
        
        receta = Receta.objects.create(
            producto_terminado=producto,
            rendimiento_base=100.00
        )
        return responsable, receta

    def test_valores_iniciales_automaticos(self, data_base):

        responsable, receta = data_base

        orden = OrdenProduccion.objects.create(
            receta=receta,
            cantidad_esperada=500.00,
            responsable=responsable
        )

        assert orden.estado == EstadoOrden.PLANIFICADA

        fecha_str = timezone.now().strftime('%Y%m%d')
        assert orden.codigo_lote.startswith(f'LOTE-{fecha_str}-')

        assert len(orden.codigo_lote) == 18

        fecha_esperada = timezone.now().date() + timedelta(days=30)
        assert orden.fecha_vencimiento == fecha_esperada