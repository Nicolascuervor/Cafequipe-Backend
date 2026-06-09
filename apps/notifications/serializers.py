from rest_framework import serializers
from .models import SystemEmailConfiguration

class SystemEmailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemEmailConfiguration
        fields = ['notify_alerts', 'daily_summary', 'admin_email']
