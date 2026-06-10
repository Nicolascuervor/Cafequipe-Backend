import pytest
from rest_framework.exceptions import ValidationError
from apps.users.models import User
from apps.inventory.models import Bodega, Producto, SubCategoria, CategoriaPrincipal
from apps.inventory.serializers import BodegaDetailSerializer, StockBodegaSerializer

@pytest.mark.django_db
class TestBodegaDetailSerializer:

    def test_valida_administrador_rol_permitido(self):

        jefe = User.objects.create_user(
            email='jefe_bodega@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA
        )
        serializer = BodegaDetailSerializer()
        resultado = serializer.validate_administrador(jefe)
        assert resultado == jefe

    def test_valida_administrador_rol_prohibido(self):

        operador = User.objects.create_user(
            email='operador@cafequipe.com', password='123', rol=User.Rol.OPERARIO
        )
        serializer = BodegaDetailSerializer()
        
        with pytest.raises(ValidationError) as error_info:
            serializer.validate_administrador(operador)
            
        assert 'El usuario asignado debe ser Jefe de Bodega' in str(error_info.value)


@pytest.mark.django_db
class TestStockBodegaSerializer:

    @pytest.fixture
    def data_base(self):
        jefe = User.objects.create_user(email='admin_bodega@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA)
        sub_cat = SubCategoria.objects.create(nombre='Insumos')

        bodega = Bodega.objects.create(nombre='Bodega Central', administrador=jefe, catalogo_admitido=[CategoriaPrincipal.INSUMO])
        
        producto_valido = Producto.objects.create(
            nombre='Azúcar', categoria_principal=CategoriaPrincipal.INSUMO, sub_categoria=sub_cat
        )
        producto_invalido = Producto.objects.create(
            nombre='Café Molido', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=sub_cat
        )
        return bodega, producto_valido, producto_invalido

    def test_validate_catalogo_admitido_exitoso(self, data_base):

        bodega, producto_valido, _ = data_base
        serializer = StockBodegaSerializer()

        data_entrada = {'bodega': bodega, 'producto': producto_valido}
        
        resultado = serializer.validate(data_entrada)

        assert resultado == data_entrada

    def test_validate_catalogo_admitido_error(self, data_base):

        bodega, _, producto_invalido = data_base
        serializer = StockBodegaSerializer()
        
        data_entrada = {'bodega': bodega, 'producto': producto_invalido}
        
        with pytest.raises(ValidationError) as error_info:
            serializer.validate(data_entrada)
            
        assert 'no admite productos de tipo' in str(error_info.value)
