
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Mínimo 8 caracteres'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='Debe coincidir con password'
    )

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'rol', 'telefono',
            'password', 'password_confirm',
        ]
        # Campos obligatorios en el request — DRF retorna 400 si faltan
        extra_kwargs = {
            'email':      {'required': True},
            'first_name': {'required': True},
            'last_name':  {'required': True},
        }

    def validate_email(self, value):
        """Normaliza el email a minúsculas para evitar duplicados
        como 'Juan@Email.com' y 'juan@email.com'."""
        return value.lower().strip()

    def validate(self, attrs):
        """
        Validaciones que dependen de múltiples campos van en validate().
        📚 POR QUÉ no en validate_password():
        Porque necesitamos comparar password con password_confirm,
        y validate_<field> solo recibe el valor de ese campo.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })

        # Aplica las validaciones de Django (longitud, complejidad, etc.)
        # Estas están en AUTH_PASSWORD_VALIDATORS en settings.py
        validate_password(attrs['password'])

        return attrs

    def create(self, validated_data):
        """
        📚 POR QUÉ usamos create_user() en lugar de User.objects.create():
        create_user() HASHEA la contraseña automáticamente.
        Si usáramos create(), la contraseña se guardaría en texto plano
        → vulnerabilidad crítica.
        """
        # Removemos password_confirm — no es un campo del modelo
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user
