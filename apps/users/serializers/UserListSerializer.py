from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(
        source='get_rol_display',
        read_only=True
    )
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'rol', 'rol_display', 'is_active',
        ]
