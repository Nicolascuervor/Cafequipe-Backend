from rest_framework import serializers
from apps.users.models import TrustedDevice

class TrustedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedDevice
        fields = ['id', 'device_id', 'device_name', 'ip_address', 'is_trusted', 'last_login', 'created_at']
        read_only_fields = ['id', 'device_id', 'ip_address', 'last_login', 'created_at']
