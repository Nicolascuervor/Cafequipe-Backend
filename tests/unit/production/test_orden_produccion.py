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
        """Prepara los datos base (Usuario Responsable, SubCategoria, Producto y Receta)."""
        responsable = User.objects.create_user(
            email='jefe_prod@cafequipe.com', password='123', rol=User.Rol.JEFE_PRODUCCION
        )
        sub_cat = SubCategoria.objects.create(nombre='Productos Finales')
        
        # La receta exige que el producto esté categorizado como Producto Terminado (PR)
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
        """
        Prueba que al crear una orden de producción, el sistema genere
        correctamente el código de lote, el estado inicial y la fecha de vencimiento.
        """
        responsable, receta = data_base

        # Creamos la orden solo proveyendo los campos estrictamente requeridos manualmente
        orden = OrdenProduccion.objects.create(
            receta=receta,
            cantidad_esperada=500.00,
            responsable=responsable
        )

        # 1. Validar el estado por defecto (Debe iniciar como PLANIFICADA)
        assert orden.estado == EstadoOrden.PLANIFICADA

        # 2. Validar el código de lote dinámico (Debe empezar con LOTE- y tener la fecha de hoy)
        fecha_str = timezone.now().strftime('%Y%m%d')
        assert orden.codigo_lote.startswith(f'LOTE-{fecha_str}-')
        
        # Validar la estructura del formato LOTE-YYYYMMDD-XXXX
        # "LOTE-" (5) + YYYYMMDD (8) + "-" (1) + XXXX (4) = 18 caracteres
        assert len(orden.codigo_lote) == 18

        # 3. Validar la fecha de vencimiento predeterminada (30 días en el futuro)
        fecha_esperada = timezone.now().date() + timedelta(days=30)
        assert orden.fecha_vencimiento == fecha_esperada
