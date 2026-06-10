import pytest
from rest_framework.exceptions import ValidationError
from apps.users.models import User
from apps.users.serializers.UserRegisterSerializer import UserRegisterSerializer
from apps.users.serializers.CustomTokenObtainPairSerializer import CustomTokenObtainPairSerializer

@pytest.mark.django_db
class TestUserRegisterSerializer:

    def test_normalizacion_de_email(self):
        """Limpia espacios y pone en minúsculas el email automáticamente."""
        serializer = UserRegisterSerializer()
        email_limpio = serializer.validate_email("  JUAn@EmaiL.cOm  ")
        assert email_limpio == "juan@email.com"

    def test_validacion_contrasenas_cruzadas_fallida(self):
        """Bloquea si password y password_confirm no son idénticos."""
        serializer = UserRegisterSerializer()
        attrs_malos = {'password': 'MiSuperPassword123', 'password_confirm': 'MiSuperPassword124'}
        with pytest.raises(ValidationError) as error_info:
            serializer.validate(attrs_malos)
        assert 'Las contraseñas no coinciden' in str(error_info.value)

    def test_creacion_encripta_password(self):
        """Comprueba que el password se convierta en un Hash seguro antes de guardarse."""
        serializer = UserRegisterSerializer()
        validated_data = {
            'email': 'operador_prueba@cafequipe.com', 'first_name': 'Carlos', 'last_name': 'Ruiz',
            'password': 'PasswordSeguro1*', 'password_confirm': 'PasswordSeguro1*', 'rol': 'OPR'
        }
        user = serializer.create(validated_data)
        
        assert user.password != 'PasswordSeguro1*'
        assert user.check_password('PasswordSeguro1*') is True


@pytest.mark.django_db
class TestCustomTokenObtainPairSerializer:

    def test_get_token_inyecta_claims_personalizados(self):
        """
        Prueba que la firma digital (Token JWT) contenga
        la inyección de nuestros claims personalizados (email, rol, full_name).
        """
        # 1. Instanciamos un usuario real simulado
        user = User.objects.create_user(
            email='gerente@cafequipe.com',
            password='123',
            first_name='Ana',
            last_name='Gómez',
            rol=User.Rol.GERENTE
        )
        
        # 2. Solicitamos la emisión de un nuevo Token
        token = CustomTokenObtainPairSerializer.get_token(user)
        
        # 3. Verificamos que los claims vitales (ID) de la librería base existan
        assert 'user_id' in token
        assert str(token['user_id']) == str(user.id)
        
        # 4. Comprobamos la inyección exitosa de NUESTRA personalización
        assert 'email' in token
        assert token['email'] == 'gerente@cafequipe.com'
        
        assert 'rol' in token
        assert token['rol'] == 'GER'
        
        assert 'full_name' in token
        assert token['full_name'] == 'Ana Gómez'
