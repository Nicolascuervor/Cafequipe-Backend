from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationLog(models.Model):
    class NotificationType(models.TextChoices):
        REGISTRATION = 'REGISTRATION', 'Registro de Usuario'
        LOGIN_ALERT = 'LOGIN_ALERT', 'Alerta de Inicio de Sesión'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Recuperación de Contraseña'
        SUPPLY_REQUEST = 'SUPPLY_REQUEST', 'Solicitud de Insumos'
        SUPPLY_DELIVERED = 'SUPPLY_DELIVERED', 'Insumos Entregados'
        QC_REJECTED = 'QC_REJECTED', 'Control de Calidad Rechazado'
        FINISHED_PRODUCT = 'FINISHED_PRODUCT', 'Producto Terminado'
        OUT_OF_STOCK = 'OUT_OF_STOCK', 'Stock Agotado'
        PRODUCT_EXPIRED = 'PRODUCT_EXPIRED', 'Producto Vencido'
        OTHER = 'OTHER', 'Otro'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        SENT = 'SENT', 'Enviado'
        FAILED = 'FAILED', 'Fallido'

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name='Usuario')
    recipient_email = models.EmailField(blank=True, default='', verbose_name='Correo Destino')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.OTHER, verbose_name='Tipo')
    subject = models.CharField(max_length=255, verbose_name='Asunto')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, verbose_name='Estado')
    error_message = models.TextField(blank=True, default='', verbose_name='Mensaje de Error')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        verbose_name = 'Log de Notificación'
        verbose_name_plural = 'Logs de Notificaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} a {self.user.email if self.user else 'Admin'} - {self.get_status_display()}"


class SystemEmailConfiguration(models.Model):
    """Modelo Singleton para la configuración global de correos del sistema."""
    notify_alerts = models.BooleanField(default=True, verbose_name='Notificar por correo')
    daily_summary = models.BooleanField(default=False, verbose_name='Resumen diario')
    admin_email = models.EmailField(blank=True, default='', verbose_name='Correo administrativo')

    class Meta:
        verbose_name = 'Configuración de Correos del Sistema'
        verbose_name_plural = 'Configuraciones de Correos del Sistema'

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SystemEmailConfiguration, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

