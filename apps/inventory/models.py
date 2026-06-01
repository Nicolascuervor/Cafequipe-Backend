# apps/inventory/models.py
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal



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


class UnidadMedida(models.TextChoices):
    KILOGRAMO = 'KG', 'Kilogramos (kg)'
    GRAMO = 'G', 'Gramos (g)'
    LITRO = 'L', 'Litros (L)'
    MILILITRO = 'ML', 'Mililitros (ml)'
    UNIDAD = 'UND', 'Unidades (und)'
    CAJA = 'CAJ', 'Cajas'
    PAQUETE = 'PAQ', 'Paquetes'


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
    
    unidad_medida = models.CharField(
        max_length=3,
        choices=UnidadMedida.choices,
        default=UnidadMedida.UNIDAD,
        verbose_name='unidad de medida',
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
    inventario_seguridad = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Stock mínimo de reserva ante variaciones de la demanda o retrasos.',
        verbose_name='inventario de seguridad',
    )
    punto_reorden = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('0.0000'),
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

    def default_catalogo(self):
        return [CategoriaPrincipal.MATERIA_PRIMA, CategoriaPrincipal.INSUMO, CategoriaPrincipal.PRODUCTO]

    catalogo_admitido = ArrayField(
        models.CharField(
            max_length=2, 
            choices=CategoriaPrincipal.choices
        ),
        default=default_catalogo,
        verbose_name='catálogo admitido'
    )

    permite_stock_negativo = models.BooleanField(
        default=False,
        help_text='Permite descontar inventario en negativo. Útil para que la producción continúe y el inventario cuadre automáticamente al registrar el ingreso.',
        verbose_name='permite stock negativo'
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

    stock_disponible = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name='stock disponible',
    )
    pedidos_abiertos = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Cantidad en órdenes de compra emitidas.',
        verbose_name='pedidos abiertos',
    )
    ordenes_atrasadas = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Cantidad comprometida no entregada.',
        verbose_name='órdenes atrasadas',
    )

    # Control de Lotes y Fechas de Vencimiento (Fase 2)
    codigo_lote = models.CharField(
        max_length=100,
        default='LOTE_INICIAL',
        help_text='Código de lote para trazabilidad PEPS.',
        verbose_name='código de lote'
    )
    fecha_vencimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name='fecha de vencimiento'
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
        unique_together = ('bodega', 'producto', 'codigo_lote')

    def __str__(self):
        return f'{self.producto.nombre} en {self.bodega.nombre} [Lote: {self.codigo_lote}] ({self.stock_disponible} und)'

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

    def clean(self):
        super().clean()
        if self.producto_id and self.bodega_id:
            cat_producto = self.producto.categoria_principal
            if not cat_producto:
                raise ValidationError({
                    'producto': 'Este producto no tiene definida su categoría principal.'
                })
            
            if cat_producto not in self.bodega.catalogo_admitido:
                cat_nombre = self.producto.get_categoria_principal_display()
                raise ValidationError(
                    f'La bodega {self.bodega.nombre} no admite productos de tipo {cat_nombre}.'
                )
