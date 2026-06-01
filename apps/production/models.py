import uuid
from django.db import models
from django.conf import settings
from apps.inventory.models import AuditModel, Producto, Bodega
from django.utils import timezone
from datetime import timedelta
import random
import string

class Receta(AuditModel):
    producto_terminado = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE,
        limit_choices_to={'categoria_principal': 'PR'},
        related_name='receta_produccion',
        verbose_name='producto a fabricar'
    )
    rendimiento_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text='Cantidad de producto que se obtiene con esta receta base (ej. 50 unidades, 1 kg).',
        verbose_name='rendimiento base esperado'
    )
    instrucciones = models.TextField(
        blank=True,
        help_text='Paso a paso de la preparación (Temperaturas, tiempos, etc).',
        verbose_name='instrucciones de preparación'
    )
    activa = models.BooleanField(
        default=True,
        help_text='Indica si esta receta es la fórmula oficial vigente.'
    )

    class Meta:
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'
        ordering = ['-created_at']

    def __str__(self):
        return f'Receta para: {self.producto_terminado.nombre}'


class IngredienteReceta(AuditModel):
    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name='ingredientes'
    )
    # Solo permite usar Materias Primas (MP) e Insumos (IN)
    producto_insumo = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        limit_choices_to={'categoria_principal__in': ['MP', 'IN']},
        related_name='utilizado_en_recetas',
        verbose_name='ingrediente/insumo'
    )
    cantidad_necesaria = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text='Cantidad necesaria de este insumo para fabricar el rendimiento base de la receta.',
        verbose_name='cantidad necesaria'
    )

    class Meta:
        verbose_name = 'Ingrediente de Receta'
        verbose_name_plural = 'Ingredientes de Receta'
        unique_together = ('receta', 'producto_insumo')

    def __str__(self):
        return f'{self.cantidad_necesaria} x {self.producto_insumo.nombre}'

class EstadoOrden(models.TextChoices):
    PLANIFICADA = 'PLN', 'Planificada'
    EN_PROCESO = 'PRO', 'En Proceso'
    CONTROL_CALIDAD = 'CAL', 'Control de Calidad'
    COMPLETADA = 'FIN', 'Completada'
    RECHAZADA = 'REC', 'Rechazada'

def generar_codigo_lote():
    fecha_str = timezone.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'LOTE-{fecha_str}-{random_str}'

def fecha_vencimiento_default():
    return timezone.now().date() + timedelta(days=30)

class OrdenProduccion(AuditModel):
    receta = models.ForeignKey(
        Receta,
        on_delete=models.RESTRICT,
        related_name='ordenes_produccion'
    )
    codigo_lote = models.CharField(
        max_length=100,
        default=generar_codigo_lote,
        help_text='Código del lote. Puede ser editado manualmente si se requiere.',
        verbose_name='código de lote'
    )
    estado = models.CharField(
        max_length=3,
        choices=EstadoOrden.choices,
        default=EstadoOrden.PLANIFICADA
    )
    cantidad_esperada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Cantidad que se espera producir.',
        verbose_name='cantidad a producir (esperada)'
    )
    cantidad_obtenida = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Rendimiento real obtenido al finalizar la producción.',
        verbose_name='cantidad real obtenida'
    )
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateField(
        default=fecha_vencimiento_default,
        help_text='Fecha de vencimiento que tendrá este lote de producto terminado.',
        verbose_name='fecha de vencimiento del lote'
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'rol__in': ['JPR', 'GER']},
        related_name='ordenes_supervisadas'
    )
    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='ordenes_entrantes',
        help_text='Bodega a la cual se enviará el producto terminado una vez se apruebe la calidad.'
    )

    class Meta:
        verbose_name = 'Orden de Producción'
        verbose_name_plural = 'Órdenes de Producción'
        ordering = ['-created_at']

    def __str__(self):
        return f'Orden {self.codigo_lote} - {self.receta.producto_terminado.nombre}'

class TipoParametro(models.TextChoices):
    BOOLEANO = 'BOOL', 'Aprobado / Rechazado (Sí/No)'
    DECIMAL = 'NUM', 'Valor Numérico (Decimal)'
    TEXTO = 'TXT', 'Texto Abierto'

class ParametroCalidad(AuditModel):
    nombre = models.CharField(max_length=150, unique=True, help_text='Ej: Grados Brix, Porcentaje de Humedad, Sabor Aprobado')
    tipo_dato = models.CharField(max_length=4, choices=TipoParametro.choices, default=TipoParametro.BOOLEANO)
    activo = models.BooleanField(default=True, help_text='Desactívalo si ya no quieres que aparezca en el formulario de calidad.')

    class Meta:
        verbose_name = 'Parámetro de Calidad'
        verbose_name_plural = 'Parámetros de Calidad'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_dato_display()})'

class ControlCalidadLote(AuditModel):
    orden_produccion = models.OneToOneField(
        OrdenProduccion,
        on_delete=models.CASCADE,
        related_name='control_calidad'
    )
    aprobado_final = models.BooleanField(
        default=False, 
        help_text='¿El lote cumple con todos los estándares para salir a venta?'
    )
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Bitácora de Calidad'
        verbose_name_plural = 'Bitácoras de Calidad'

    def __str__(self):
        estado = "APROBADO" if self.aprobado_final else "RECHAZADO"
        return f'Calidad Orden {self.orden_produccion.codigo_lote} - {estado}'

class ValorParametroCalidad(AuditModel):
    control = models.ForeignKey(
        ControlCalidadLote,
        on_delete=models.CASCADE,
        related_name='valores'
    )
    parametro = models.ForeignKey(
        ParametroCalidad,
        on_delete=models.RESTRICT
    )
    valor_booleano = models.BooleanField(null=True, blank=True)
    valor_decimal = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    valor_texto = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('control', 'parametro')
        verbose_name = 'Valor de Parámetro'
        verbose_name_plural = 'Valores de Parámetros'

    def __str__(self):
        return f'{self.parametro.nombre} para {self.control.orden_produccion.codigo_lote}'

class EstadoTicket(models.TextChoices):
    SOLICITADO = 'SOL', 'Solicitado'
    ENTREGADO = 'ENT', 'Entregado'
    RECHAZADO = 'REC', 'Rechazado'

class TicketInsumo(AuditModel):
    orden_produccion = models.OneToOneField(
        OrdenProduccion,
        on_delete=models.CASCADE,
        related_name='ticket_insumos'
    )
    estado = models.CharField(
        max_length=3,
        choices=EstadoTicket.choices,
        default=EstadoTicket.SOLICITADO
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    despachador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={'rol__in': ['JBD', 'GER']},
        related_name='tickets_despachados'
    )
    razon_rechazo = models.TextField(
        'Razón de Rechazo',
        blank=True,
        null=True,
        help_text='Motivo por el cual el Jefe de Producción rechazó este ticket.'
    )

    class Meta:
        verbose_name = 'Ticket de Insumos'
        verbose_name_plural = 'Tickets de Insumos'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'Ticket para {self.orden_produccion.codigo_lote} ({self.get_estado_display()})'

class DetalleTicketInsumo(AuditModel):
    ticket = models.ForeignKey(
        TicketInsumo,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        limit_choices_to={'categoria_principal__in': ['MP', 'IN']}
    )
    cantidad_solicitada = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text='Cantidad matemática requerida según la receta'
    )
    cantidad_entregada = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text='Cantidad física real entregada por la bodega'
    )
    lote_origen = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Lotes de los que se extrajo el material (Para PEPS)'
    )

    class Meta:
        verbose_name = 'Detalle de Ticket'
        verbose_name_plural = 'Detalles de Ticket'
        unique_together = ('ticket', 'producto')

    def __str__(self):
        return f'{self.cantidad_solicitada} de {self.producto.nombre}'

