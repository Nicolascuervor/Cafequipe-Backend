from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationLog(models.Model):
    class NotificationType(models.TextChoices):
        REGISTRATION = 'REGISTRATION', 'Registro de Usuario'
        LOGIN_ALERT = 'LOGIN_ALERT', 'Alerta de Inicio de Sesión'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Recuperación de Contraseña'
        OTHER = 'OTHER', 'Otro'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        SENT = 'SENT', 'Enviado'
        FAILED = 'FAILED', 'Fallido'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='Usuario')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.OTHER, verbose_name='Tipo')
    subject = models.CharField(max_length=255, verbose_name='Asunto')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, verbose_name='Estado')
    error_message = models.TextField(blank=True, null=True, verbose_name='Mensaje de Error')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        verbose_name = 'Log de Notificación'
        verbose_name_plural = 'Logs de Notificaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} a {self.user.email} - {self.get_status_display()}"

