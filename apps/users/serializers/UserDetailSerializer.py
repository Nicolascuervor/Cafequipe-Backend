from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='users:user-detail')
    rol_display = serializers.CharField(
        source='get_rol_display',
        read_only=True
    )
    full_name = serializers.CharField(
        source='get_full_name',
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            'url', 'id', 'email', 'first_name', 'last_name',
            'rol', 'rol_display', 'telefono',
            'full_name', 'is_active',
            'date_joined', 'updated_at', 'last_login',
        ]
        read_only_fields = [
            'id', 'email', 'rol',
            'date_joined', 'updated_at', 'last_login',
        ]
