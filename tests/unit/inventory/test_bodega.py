import pytest
from django.core.exceptions import ValidationError
from apps.inventory.models import Bodega, CategoriaPrincipal
from apps.users.models import User

@pytest.mark.django_db
class TestBodegaModel:

    def test_creacion_bodega_con_administrador_valido(self):

        jefe = User.objects.create_user(
            email='jefe_bodega@cafequipe.com',
            password='123',
            rol=User.Rol.JEFE_BODEGA
        )


        bodega = Bodega(
            nombre='Bodega Central',
            ubicacion='Sede Principal',
            administrador=jefe
        )


        bodega.clean()
        bodega.save()

        assert bodega.id is not None
        assert bodega.administrador == jefe

    def test_error_bodega_con_administrador_invalido(self):

        operario = User.objects.create_user(
            email='operario@cafequipe.com',
            password='123',
            rol=User.Rol.OPERARIO
        )

        bodega = Bodega(
            nombre='Bodega Secundaria',
            ubicacion='Sede Sur',
            administrador=operario
        )

        with pytest.raises(ValidationError) as error_info:
            bodega.clean()

        assert 'administrador' in error_info.value.error_dict
        mensaje_error = error_info.value.error_dict['administrador'][0].message
        assert 'rol de Jefe de Bodega (JBD) o Gerente (GER)' in mensaje_error

    def test_catalogo_admitido_por_defecto(self):

        jefe = User.objects.create_user(
            email='jefe2@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA
        )
        
        bodega = Bodega.objects.create(
            nombre='Bodega Norte',
            ubicacion='Sede Norte',
            administrador=jefe
        )

        assert CategoriaPrincipal.MATERIA_PRIMA in bodega.catalogo_admitido
        assert CategoriaPrincipal.INSUMO in bodega.catalogo_admitido
        assert CategoriaPrincipal.PRODUCTO in bodega.catalogo_admitido
