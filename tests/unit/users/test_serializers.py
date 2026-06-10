import pytest
from rest_framework.exceptions import ValidationError
from apps.users.models import User
from apps.users.serializers.UserRegisterSerializer import UserRegisterSerializer
from apps.users.serializers.CustomTokenObtainPairSerializer import CustomTokenObtainPairSerializer

@pytest.mark.django_db
class TestUserRegisterSerializer:

    def test_normalizacion_de_email(self):

        serializer = UserRegisterSerializer()
        email_limpio = serializer.validate_email("  JUAn@EmaiL.cOm  ")
        assert email_limpio == "juan@email.com"

    def test_validacion_contrasenas_cruzadas_fallida(self):

        serializer = UserRegisterSerializer()
        attrs_malos = {'password': 'MiSuperPassword123', 'password_confirm': 'MiSuperPassword124'}
        with pytest.raises(ValidationError) as error_info:
            serializer.validate(attrs_malos)
        assert 'Las contraseñas no coinciden' in str(error_info.value)

    def test_creacion_encripta_password(self):

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

        user = User.objects.create_user(
            email='gerente@cafequipe.com',
            password='123',
            first_name='Ana',
            last_name='Gómez',
            rol=User.Rol.GERENTE
        )

        token = CustomTokenObtainPairSerializer.get_token(user)
        

        assert 'user_id' in token
        assert str(token['user_id']) == str(user.id)
        

        assert 'email' in token
        assert token['email'] == 'gerente@cafequipe.com'
        
        assert 'rol' in token
        assert token['rol'] == 'GER'
        
        assert 'full_name' in token
        assert token['full_name'] == 'Ana Gómez'
