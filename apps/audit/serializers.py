# apps/audit/serializers.py
from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer de solo lectura para los registros de auditoría."""

    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True,
    )
    module_display = serializers.CharField(
        source='get_module_display',
        read_only=True,
    )

    user_full_name = serializers.SerializerMethodField()
    user_role_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'timestamp',
            'user',
            'user_email',
            'user_full_name',
            'user_role_display',
            'action',
            'action_display',
            'module',
            'module_display',
            'description',
            'ip_address',
        ]
        read_only_fields = fields

    def get_user_full_name(self, obj) -> str:
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return obj.user_email

    def get_user_role_display(self, obj) -> str:
        if obj.user:
            return obj.user.get_rol_display()
        return "Desconocido"
