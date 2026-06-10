import pytest
from apps.users.models import User

# El decorador @pytest.mark.django_db es fundamental aquí. 
# Le indica a PyTest que esta prueba necesita acceder a la base de datos de prueba
# de Django. Sin esto, cualquier intento de hacer User.objects.create() fallará.
@pytest.mark.django_db
class TestUserModel:

    def test_creacion_usuario_regular(self):
        """
        Prueba que un usuario normal se crea correctamente.
        Verifica que su contraseña se encripte y que los roles por defecto apliquen.
        """
        usuario = User.objects.create_user(
            email='operario@cafequipe.com',
            password='PasswordSeguro123',
            first_name='Juan',
            last_name='Perez'
        )

        assert usuario.email == 'operario@cafequipe.com'
        
        # Verificamos que la contraseña se encriptó y no se guardó en texto plano
        assert usuario.password != 'PasswordSeguro123'
        
        # check_password es el método de Django para validar contraseñas encriptadas
        assert usuario.check_password('PasswordSeguro123') is True
        
        # El rol por defecto debería ser Operario ('OPR')
        assert usuario.rol == User.Rol.OPERARIO
        assert usuario.is_staff is False
        assert usuario.is_superuser is False

    def test_error_creacion_sin_email(self):
        """
        Prueba que el sistema lance un error si intentamos crear un usuario
        sin proporcionarle un correo electrónico.
        """
        # pytest.raises "atrapa" el error esperado. Si el código dentro de 'with'
        # genera el ValueError con el mensaje indicado, la prueba es exitosa.
        with pytest.raises(ValueError, match='El email es obligatorio.'):
            User.objects.create_user(
                email='',
                password='PasswordSeguro123'
            )

    def test_creacion_superusuario_exitoso(self):
        """
        Prueba que la creación de un superusuario configure correctamente
        los permisos elevados y el rol de Gerente.
        """
        admin = User.objects.create_superuser(
            email='admin@cafequipe.com',
            password='AdminPassword123'
        )

        assert admin.email == 'admin@cafequipe.com'
        assert admin.is_staff is True
        assert admin.is_superuser is True
        
        # El superusuario en este proyecto asume por defecto el rol de Gerente ('GER')
        assert admin.rol == User.Rol.GERENTE

    def test_error_superusuario_sin_is_staff(self):
        """
        Prueba que el sistema no permita crear un superusuario
        si le enviamos explícitamente el parámetro is_staff=False.
        """
        with pytest.raises(ValueError, match='Superuser debe tener is_staff=True.'):
            User.objects.create_superuser(
                email='admin2@cafequipe.com',
                password='AdminPassword123',
                is_staff=False
            )

    def test_error_superusuario_sin_is_superuser(self):
        """
        Prueba que el sistema no permita crear un superusuario
        si le enviamos explícitamente el parámetro is_superuser=False.
        """
        with pytest.raises(ValueError, match='Superuser debe tener is_superuser=True.'):
            User.objects.create_superuser(
                email='admin3@cafequipe.com',
                password='AdminPassword123',
                is_superuser=False
            )

    def test_metodo_str_del_usuario(self):
        """
        Prueba que la representación en texto del usuario (__str__) 
        tenga el formato esperado: "Nombre Apellido (Rol)".
        """
        usuario = User.objects.create_user(
            email='jefe@cafequipe.com',
            password='Password123',
            first_name='Maria',
            last_name='Gomez',
            rol=User.Rol.JEFE_BODEGA
        )

        # get_rol_display() de Django retorna el nombre legible ('Jefe de Bodega') 
        # en lugar del código interno ('JBD')
        expected_str = "Maria Gomez (Jefe de Bodega)"
        assert str(usuario) == expected_str

    def test_propiedades_de_roles(self):
        """
        Prueba que las propiedades de conveniencia (es_gerente, es_jefe_bodega, etc.)
        retornen los valores booleanos (True/False) correctos según el rol.
        """
        gerente = User.objects.create_user(email='g@test.com', password='123', rol=User.Rol.GERENTE)
        jefe_bodega = User.objects.create_user(email='jb@test.com', password='123', rol=User.Rol.JEFE_BODEGA)
        operario = User.objects.create_user(email='op@test.com', password='123', rol=User.Rol.OPERARIO)

        # Comprobamos las reglas de negocio para Gerente
        assert gerente.es_gerente is True
        assert gerente.puede_aprobar_traslados is True

        # Comprobamos las reglas de negocio para Jefe de Bodega
        assert jefe_bodega.es_jefe_bodega is True
        assert jefe_bodega.puede_aprobar_traslados is True
        assert jefe_bodega.es_gerente is False

        # Comprobamos las reglas de negocio para Operario
        assert operario.es_operario is True  
        assert operario.puede_aprobar_traslados is False
