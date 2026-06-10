import pytest
from django.core.exceptions import ValidationError
from apps.inventory.models import Bodega, CategoriaPrincipal
from apps.users.models import User

@pytest.mark.django_db
class TestBodegaModel:

    def test_creacion_bodega_con_administrador_valido(self):
        """
        Prueba que se pueda crear una bodega si el administrador asignado
        tiene el rol permitido (Jefe de Bodega o Gerente).
        """
        # 1. Creamos un usuario con rol válido
        jefe = User.objects.create_user(
            email='jefe_bodega@cafequipe.com',
            password='123',
            rol=User.Rol.JEFE_BODEGA
        )

        # 2. Creamos la instancia de la bodega
        bodega = Bodega(
            nombre='Bodega Central',
            ubicacion='Sede Principal',
            administrador=jefe
        )

        # 3. Forzamos la validación del modelo. 
        # (Nota: En Django, el método save() no ejecuta clean() automáticamente, 
        # por lo que en pruebas unitarias puras debemos llamarlo explícitamente).
        bodega.clean()
        bodega.save()

        # Comprobamos que se guardó correctamente y tiene un ID
        assert bodega.id is not None
        assert bodega.administrador == jefe

    def test_error_bodega_con_administrador_invalido(self):
        """
        Prueba que el método clean() lance un ValidationError si intentamos
        asignar como administrador a un usuario que es solo Operario.
        """
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

        # Verificamos que al llamar a clean() se "atrape" el error de validación esperado
        with pytest.raises(ValidationError) as error_info:
            bodega.clean()
        
        # Validamos que el mensaje de error sea el que especificamos en el modelo
        assert 'administrador' in error_info.value.error_dict
        mensaje_error = error_info.value.error_dict['administrador'][0].message
        assert 'rol de Jefe de Bodega (JBD) o Gerente (GER)' in mensaje_error

    def test_catalogo_admitido_por_defecto(self):
        """
        Prueba que al crear una bodega sin especificar el catálogo,
        este se asigne con todos los valores por defecto (MP, IN, PR).
        """
        jefe = User.objects.create_user(
            email='jefe2@cafequipe.com', password='123', rol=User.Rol.JEFE_BODEGA
        )
        
        bodega = Bodega.objects.create(
            nombre='Bodega Norte',
            ubicacion='Sede Norte',
            administrador=jefe
        )

        # Verificamos que el arreglo contenga las categorías principales correctas
        assert CategoriaPrincipal.MATERIA_PRIMA in bodega.catalogo_admitido
        assert CategoriaPrincipal.INSUMO in bodega.catalogo_admitido
        assert CategoriaPrincipal.PRODUCTO in bodega.catalogo_admitido
