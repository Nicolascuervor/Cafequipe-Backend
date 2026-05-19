# apps/audit/models.py
import uuid
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Registro inmutable de auditoría.
    Solo se pueden CREAR registros — nunca editar ni eliminar.
    """

    class Action(models.TextChoices):
        LOGIN            = 'LOGIN',            'Inicio de sesión'
        LOGOUT           = 'LOGOUT',           'Cierre de sesión'
        USER_CREATED     = 'USER_CREATED',     'Usuario creado'
        USER_UPDATED     = 'USER_UPDATED',     'Usuario actualizado'
        USER_DEACTIVATED = 'USER_DEACTIVATED', 'Usuario desactivado'
        USER_ACTIVATED   = 'USER_ACTIVATED',   'Usuario activado'
        PASSWORD_CHANGED = 'PASSWORD_CHANGED', 'Contraseña cambiada'
        # Inventario
        CATEGORIA_CREATED = 'CATEGORIA_CREATED', 'Categoría creada'
        CATEGORIA_UPDATED = 'CATEGORIA_UPDATED', 'Categoría actualizada'
        CATEGORIA_DELETED = 'CATEGORIA_DELETED', 'Categoría eliminada'
        PRODUCTO_CREATED  = 'PRODUCTO_CREATED',  'Producto creado'
        PRODUCTO_UPDATED  = 'PRODUCTO_UPDATED',  'Producto actualizado'
        PRODUCTO_DELETED  = 'PRODUCTO_DELETED',  'Producto eliminado'
        BODEGA_CREATED    = 'BODEGA_CREATED',    'Bodega creada'
        BODEGA_UPDATED    = 'BODEGA_UPDATED',    'Bodega actualizada'
        BODEGA_DELETED    = 'BODEGA_DELETED',    'Bodega eliminada'
        STOCK_CREATED     = 'STOCK_CREATED',     'Stock registrado'
        STOCK_UPDATED     = 'STOCK_UPDATED',     'Stock actualizado'
        STOCK_DELETED     = 'STOCK_DELETED',     'Stock eliminado'

    class Module(models.TextChoices):
        AUTH       = 'AUTH',       'Autenticación'
        USERS      = 'USERS',     'Usuarios'
        INVENTORY  = 'INVENTORY', 'Inventario'
        MOVEMENTS  = 'MOVEMENTS', 'Movimientos'
        PRODUCTION = 'PRODUCTION','Producción'
        REPORTS    = 'REPORTS',   'Reportes'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    timestamp = models.DateTimeField(
        'fecha y hora',
        auto_now_add=True,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='usuario',
    )
    user_email = models.CharField(
        'email del usuario',
        max_length=254,
        help_text='Snapshot del email al momento de la acción.',
    )
    action = models.CharField(
        'acción',
        max_length=50,
        choices=Action.choices,
        db_index=True,
    )
    module = models.CharField(
        'módulo',
        max_length=50,
        choices=Module.choices,
        db_index=True,
    )
    description = models.CharField(
        'descripción',
        max_length=255,
    )
    ip_address = models.GenericIPAddressField(
        'dirección IP',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registros de auditoría'
        ordering = ['-timestamp']
        # Bloqueo a nivel de DB: no se permite editar ni borrar
        default_permissions = ('add', 'view')

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} — {self.user_email}"

    # ── Inmutabilidad: bloquear updates y deletes ──

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError(
                'Los registros de auditoría son inmutables. '
                'No se permite la modificación.'
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(
            'Los registros de auditoría son inmutables. '
            'No se permite la eliminación.'
        )
