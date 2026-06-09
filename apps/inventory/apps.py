# apps/inventory/apps.py
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Inventario'

    def ready(self):
        import apps.inventory.signals  # noqa: F401
