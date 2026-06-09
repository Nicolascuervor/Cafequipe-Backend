from rest_framework import serializers
from .models import SystemEmailConfiguration, NotificationLog

class SystemEmailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemEmailConfiguration
        fields = ['notify_alerts', 'daily_summary', 'admin_email']

class NotificationLogSerializer(serializers.ModelSerializer):
    variant = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = ['id', 'subject', 'error_message', 'notification_type', 'status', 'is_read', 'created_at', 'variant', 'time']

    def get_variant(self, obj):
        # Map Django types to React UI variants ("alert", "info", "success")
        if obj.notification_type in ['STOCK_CRITICO', 'OUT_OF_STOCK', 'PRODUCT_EXPIRED', 'QC_REJECTED']:
            return "alert"
        elif obj.notification_type in ['REGISTRATION']:
            return "success"
        return "info"

    def get_time(self, obj):
        # Return ISO string; the frontend can use date-fns to do "Hace 5 min"
        return obj.created_at.isoformat()
