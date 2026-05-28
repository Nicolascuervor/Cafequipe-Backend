# apps/notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notificaciones'

    def ready(self):
        # Registra las signals al iniciar la app
        import apps.notifications.signals  # noqa: F401
