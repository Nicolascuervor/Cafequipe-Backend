# apps/inventory/models.py
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models



class AuditModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SubCategoria(AuditModel):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Subcategoría'
        verbose_name_plural = 'Subcategorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre



class ClasificacionABC(models.TextChoices):
    A = 'A', 'Clase A - Alta Prioridad'
    B = 'B', 'Clase B - Control Periódico'
    C = 'C', 'Clase C - Baja Prioridad'



class CategoriaPrincipal(models.TextChoices):
    MATERIA_PRIMA = 'MP', 'Materia prima'
    INSUMO        = 'IN', 'Insumo'
    PRODUCTO      = 'PR', 'Producto'



class NivelUbicacion(models.TextChoices):
    NIVEL_A = 'A', 'Nivel A'
    NIVEL_B = 'B', 'Nivel B'
    NIVEL_C = 'C', 'Nivel C'
    NIVEL_D = 'D', 'Nivel D'


class Producto(AuditModel):
    # Identificadores únicos comerciales
    nombre = models.CharField(max_length=150)
    
    categoria_principal = models.CharField(
        max_length=2,
        choices=CategoriaPrincipal.choices,
        null=True,
        blank=True,
        verbose_name='categoría principal',
    )
    
    sub_categoria = models.ForeignKey(
        SubCategoria,
        on_delete=models.PROTECT,
        related_name='productos',
    )

    # Costos con precisión decimal exacta (evita errores de redondeo binario)
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name='costo unitario',
    )

    # Segmentación ABC basada en el análisis de consumo anual
    clasificacion = models.CharField(
        max_length=1,
        choices=ClasificacionABC.choices,
        default=ClasificacionABC.C,
        verbose_name='clasificación ABC',
    )

    # Parámetros del modelo de control continuo y periódico
    inventario_seguridad = models.PositiveIntegerField(
        default=0,
        help_text='Stock mínimo de reserva ante variaciones de la demanda o retrasos.',
        verbose_name='inventario de seguridad',
    )
    punto_reorden = models.PositiveIntegerField(
        default=0,
        help_text='Nivel de existencias que dispara automáticamente una orden de reabastecimiento.',
        verbose_name='punto de reorden',
    )

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

    def __str__(self):
        return f'[{self.clasificacion}] {self.nombre}'




class Bodega(AuditModel):
    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=255, verbose_name='ubicación')

    # Asignación del responsable restringido por rol desde la base de datos
    administrador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bodegas_asignadas',
        limit_choices_to={'rol__in': ['JBD', 'GER']},
        help_text='Usuario responsable de la bodega (debe ser Jefe de Bodega o Gerente).',
    )

    # Relación M2M a través del modelo intermedio de Stock
    productos = models.ManyToManyField(
        Producto,
        through='StockBodega',
        related_name='bodegas',
    )

    class Meta:
        verbose_name = 'Bodega'
        verbose_name_plural = 'Bodegas'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} - Resp: {self.administrador.get_full_name()}'

    def clean(self):
        """Validación a nivel de modelo para asegurar consistencia de roles."""
        super().clean()
        if self.administrador_id and self.administrador.rol not in ['JBD', 'GER']:
            raise ValidationError({
                'administrador': (
                    'El usuario asignado debe contar con el rol de '
                    'Jefe de Bodega (JBD) o Gerente (GER).'
                )
            })



class StockBodega(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        related_name='existencias',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='existencias_bodega',
    )

    stock_disponible = models.PositiveIntegerField(
        default=0,
        verbose_name='stock disponible',
    )
    pedidos_abiertos = models.PositiveIntegerField(
        default=0,
        help_text='Cantidad en órdenes de compra emitidas.',
        verbose_name='pedidos abiertos',
    )
    ordenes_atrasadas = models.PositiveIntegerField(
        default=0,
        help_text='Cantidad comprometida no entregada.',
        verbose_name='órdenes atrasadas',
    )

    # Parámetros de ubicación física (basado en análisis ABC)
    rack = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name='rack de almacenamiento'
    )
    nivel_ubicacion = models.CharField(
        max_length=1,
        choices=NivelUbicacion.choices,
        blank=True,
        null=True,
        verbose_name='nivel (A, B, C, D)'
    )
    estiba = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='número/identificador de estiba'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock en Bodega'
        verbose_name_plural = 'Stocks en Bodegas'
        unique_together = ('bodega', 'producto')

    def __str__(self):
        return f'{self.producto.nombre} en {self.bodega.nombre} ({self.stock_disponible} und)'

    @property
    def coordenada_fisica(self):
        partes = []
        if self.rack:
            partes.append(f'Rack {self.rack}')
        if self.nivel_ubicacion:
            partes.append(f'Nivel {self.nivel_ubicacion}')
        if self.estiba:
            partes.append(f'Estiba {self.estiba}')
        
        return " - ".join(partes) if partes else "Sin ubicación asignada"

    @property
    def stock_proyectado(self):
        return self.stock_disponible + self.pedidos_abiertos - self.ordenes_atrasadas

    @property
    def requiere_reorden(self):
        return self.stock_proyectado <= self.producto.punto_reorden
