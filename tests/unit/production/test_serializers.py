import pytest
import uuid
from decimal import Decimal
from apps.users.models import User
from apps.inventory.models import Bodega, Producto, SubCategoria, CategoriaPrincipal
from apps.production.models import (
    Receta, OrdenProduccion, ParametroCalidad, ControlCalidadLote, ValorParametroCalidad, TipoParametro
)
from apps.production.serializers import OrdenProduccionSerializer, ControlCalidadLoteSerializer

@pytest.mark.django_db
class TestOrdenProduccionSerializer:

    def test_saneamiento_lote_y_fecha(self):
        data_mala = {'codigo_lote': '   ', 'fecha_vencimiento': None, 'cantidad_esperada': 100}
        data_limpia = OrdenProduccionSerializer(partial=True).to_internal_value(data_mala)
        assert 'codigo_lote' not in data_limpia
        assert 'fecha_vencimiento' not in data_limpia
        assert data_limpia['cantidad_esperada'] == 100

    def test_saneamiento_decimal_comas(self):
        data = {'cantidad_obtenida': '150,50'}
        data_limpia = OrdenProduccionSerializer(partial=True).to_internal_value(data)
        assert data_limpia['cantidad_obtenida'] == Decimal('150.50')

    def test_saneamiento_bodega_por_nombre(self):
        jefe = User.objects.create_user(email='jefe_bodega@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA)
        bodega = Bodega.objects.create(nombre='Bodega Central', administrador=jefe)
        data = {'bodega_destino': 'Bodega Central'}
        data_limpia = OrdenProduccionSerializer(partial=True).to_internal_value(data)
        assert data_limpia['bodega_destino'] == bodega

    def test_saneamiento_bodega_por_id_intacto(self):
        jefe = User.objects.create_user(email='jefe2@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA)
        bodega = Bodega.objects.create(nombre='Bodega Norte', administrador=jefe)
        valid_uuid = str(bodega.id)
        data = {'bodega_destino': valid_uuid}
        data_limpia = OrdenProduccionSerializer(partial=True).to_internal_value(data)
        assert data_limpia['bodega_destino'] == bodega

@pytest.mark.django_db
class TestControlCalidadLoteSerializer:

    @pytest.fixture
    def setup_data(self):
        jefe = User.objects.create_user(email='jefe@cafequipe.com', password='123', rol=User.Rol.JEFE_PRODUCCION)
        sub_cat = SubCategoria.objects.create(nombre='Base')
        producto = Producto.objects.create(nombre='Mocaccino', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=sub_cat)
        receta = Receta.objects.create(producto_terminado=producto, rendimiento_base=10.0)
        orden = OrdenProduccion.objects.create(receta=receta, cantidad_esperada=100.0, responsable=jefe)
        
        param_humedad = ParametroCalidad.objects.create(nombre='Humedad', tipo_dato=TipoParametro.DECIMAL)
        param_color = ParametroCalidad.objects.create(nombre='Color', tipo_dato=TipoParametro.TEXTO)
        
        return orden, param_humedad, param_color

    def test_create_insert_anidado(self, setup_data):
        """Prueba que se cree una bitácora nueva con sus parámetros hijos en un solo paso."""
        orden, param_humedad, param_color = setup_data
        
        # Simulamos la data que llegaría desde el frontend ya validada
        validated_data = {
            'orden_produccion': orden,
            'aprobado_final': False,
            'observaciones': 'Primera revisión',
            'valores': [
                {'parametro': param_humedad, 'valor_decimal': '12.5'},
                {'parametro': param_color, 'valor_texto': 'Marrón Oscuro'}
            ]
        }
        
        serializer = ControlCalidadLoteSerializer()
        control = serializer.create(validated_data)
        
        # Verificamos inserción
        assert ControlCalidadLote.objects.count() == 1
        assert control.valores.count() == 2
        assert control.observaciones == 'Primera revisión'

    def test_create_upsert_anidado(self, setup_data):
        """Prueba que si se envía otra vez la misma Orden, no la duplica, sino que sobreescribe los valores."""
        orden, param_humedad, _ = setup_data
        
        # 1. Creamos la primera bitácora manualmente
        control_existente = ControlCalidadLote.objects.create(orden_produccion=orden, observaciones='Vieja')
        ValorParametroCalidad.objects.create(control=control_existente, parametro=param_humedad, valor_decimal='15.0')
        
        # 2. Invocamos create() con nueva data pero enviando la MISMA ORDEN
        validated_data_nueva = {
            'orden_produccion': orden,
            'aprobado_final': True,
            'observaciones': 'Revisión Corregida',
            'valores': [{'parametro': param_humedad, 'valor_decimal': '12.0'}]
        }
        
        serializer = ControlCalidadLoteSerializer()
        control_actualizado = serializer.create(validated_data_nueva)
        
        # 3. Verificamos comportamiento Upsert
        # Sigue habiendo SOLO 1 bitácora en la BD (No se crearon duplicados)
        assert ControlCalidadLote.objects.count() == 1
        assert control_actualizado.id == control_existente.id
        
        # La observación cambió a la nueva
        assert control_actualizado.observaciones == 'Revisión Corregida'
        
        # Sigue habiendo solo 1 parámetro hijo (el viejo de 15.0 fue borrado y reemplazado por 12.0)
        assert ValorParametroCalidad.objects.count() == 1
        assert control_actualizado.valores.first().valor_decimal == Decimal('12.0000')
