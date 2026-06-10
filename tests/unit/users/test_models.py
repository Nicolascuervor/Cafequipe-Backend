import pytest
from apps.users.models import User


@pytest.mark.django_db
class TestUserModel:

    def test_creacion_usuario_regular(self):

        usuario = User.objects.create_user(
            email='operario@cafequipe.com',
            password='PasswordSeguro123',
            first_name='Juan',
            last_name='Perez'
        )

        assert usuario.email == 'operario@cafequipe.com'

        assert usuario.password != 'PasswordSeguro123'

        assert usuario.check_password('PasswordSeguro123') is True

        assert usuario.rol == User.Rol.OPERARIO
        assert usuario.is_staff is False
        assert usuario.is_superuser is False

    def test_error_creacion_sin_email(self):

        with pytest.raises(ValueError, match='El email es obligatorio.'):
            User.objects.create_user(
                email='',
                password='PasswordSeguro123'
            )

    def test_creacion_superusuario_exitoso(self):

        admin = User.objects.create_superuser(
            email='admin@cafequipe.com',
            password='AdminPassword123'
        )

        assert admin.email == 'admin@cafequipe.com'
        assert admin.is_staff is True
        assert admin.is_superuser is True

        assert admin.rol == User.Rol.GERENTE

    def test_error_superusuario_sin_is_staff(self):

        with pytest.raises(ValueError, match='Superuser debe tener is_staff=True.'):
            User.objects.create_superuser(
                email='admin2@cafequipe.com',
                password='AdminPassword123',
                is_staff=False
            )

    def test_error_superusuario_sin_is_superuser(self):

        with pytest.raises(ValueError, match='Superuser debe tener is_superuser=True.'):
            User.objects.create_superuser(
                email='admin3@cafequipe.com',
                password='AdminPassword123',
                is_superuser=False
            )

    def test_metodo_str_del_usuario(self):

        usuario = User.objects.create_user(
            email='jefe@cafequipe.com',
            password='Password123',
            first_name='Maria',
            last_name='Gomez',
            rol=User.Rol.JEFE_BODEGA
        )

        expected_str = "Maria Gomez (Jefe de Bodega)"
        assert str(usuario) == expected_str

    def test_propiedades_de_roles(self):
        gerente = User.objects.create_user(email='g@test.com', password='123', rol=User.Rol.GERENTE)
        jefe_bodega = User.objects.create_user(email='jb@test.com', password='123', rol=User.Rol.JEFE_BODEGA)
        operario = User.objects.create_user(email='op@test.com', password='123', rol=User.Rol.OPERARIO)
        assert gerente.es_gerente is True
        assert gerente.puede_aprobar_traslados is True
        assert jefe_bodega.es_jefe_bodega is True
        assert jefe_bodega.puede_aprobar_traslados is True
        assert jefe_bodega.es_gerente is False
        assert operario.es_operario is True  
        assert operario.puede_aprobar_traslados is False
