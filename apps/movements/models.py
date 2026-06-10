import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.inventory.models import AuditModel, Bodega, Producto

class EstadoSolicitud(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    APROBADA = 'APROBADA', 'Aprobada'
    RECHAZADA = 'RECHAZADA', 'Rechazada'
    CANCELADA = 'CANCELADA', 'Cancelada'

class SolicitudInterna(AuditModel):
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='solicitudes_creadas'
    )
    aprobador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='solicitudes_aprobadas', null=True, blank=True
    )
    estado = models.CharField(
        max_length=20, choices=EstadoSolicitud.choices, default=EstadoSolicitud.PENDIENTE
    )
    motivo = models.TextField(blank=True, default='')
    motivo_rechazo = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Solicitud Interna'
        verbose_name_plural = 'Solicitudes Internas'

    def __str__(self):
        return f'Solicitud {self.id} - {self.estado}'

class DetalleSolicitud(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    solicitud = models.ForeignKey(SolicitudInterna, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)

class TipoMovimiento(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    SALIDA = 'SALIDA', 'Salida'
    AJUSTE = 'AJUSTE', 'Ajuste'
    TRASLADO = 'TRASLADO', 'Traslado'

class Recepcion(AuditModel):
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name='recepciones')
    proveedor = models.CharField(max_length=255, blank=True, default='')
    observaciones = models.TextField(blank=True, default='')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='recepciones_registradas'
    )

class Movimiento(AuditModel):
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name='movimientos')
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    recepcion = models.ForeignKey(Recepcion, on_delete=models.CASCADE, null=True, blank=True, related_name='movimientos')
    solicitud = models.ForeignKey(SolicitudInterna, on_delete=models.CASCADE, null=True, blank=True, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'
        ordering = ['-created_at']

class DetalleRecepcion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recepcion = models.ForeignKey(Recepcion, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    costo_unitario_ingreso = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lote_proveedor = models.CharField(max_length=100, blank=True, default='')
