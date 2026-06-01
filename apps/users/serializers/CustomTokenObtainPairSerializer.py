from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para el login.
    Solo inyecta claims dentro del JWT (no en el body de la respuesta HTTP).
    La información del usuario debe consultarse aparte con GET /api/v1/auth/me/
    """

    default_error_messages = {
        'no_active_account': 'Correo electrónico o contraseña incorrectos',
    }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['rol'] = user.rol
        token['full_name'] = user.get_full_name()
        return token
