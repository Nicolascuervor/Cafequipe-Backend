# apps/audit/apps.py
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Auditoría'

    def ready(self):
        # Registra las signals al iniciar la app
        import apps.audit.signals  # noqa: F401
