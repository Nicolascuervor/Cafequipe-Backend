# apps/inventory/views.py
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import F
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.users.permissions import EsGerente, EsGerenteOJefeBodega, EsGerenteOSoloLectura, EsGerenteOJefeBodegaPeroSoloGerenteElimina
from .models import SubCategoria, Producto, Bodega, StockBodega
from .serializers import (
    SubCategoriaSerializer,
    ProductoListSerializer,
    ProductoDetailSerializer,
    BodegaListSerializer,
    BodegaDetailSerializer,
    StockBodegaSerializer,
)


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Listar categorías'),
    post=extend_schema(tags=['Inventario'], summary='Crear categoría'),
)
class SubCategoriaListCreateView(generics.ListCreateAPIView):
    queryset = SubCategoria.objects.all()
    serializer_class = SubCategoriaSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'created_at']

    def perform_create(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.CATEGORIA_CREATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Categoría "{instance.nombre}" creada.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Detalle de categoría'),
    patch=extend_schema(tags=['Inventario'], summary='Editar categoría'),
    delete=extend_schema(tags=['Inventario'], summary='Eliminar categoría'),
)
class SubCategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategoria.objects.all()
    serializer_class = SubCategoriaSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodegaPeroSoloGerenteElimina]
    http_method_names = ['get', 'patch', 'delete']

    def perform_update(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.CATEGORIA_UPDATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Categoría "{instance.nombre}" actualizada.',
            request=self.request,
        )

    def perform_destroy(self, instance):
        nombre = instance.nombre
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.CATEGORIA_DELETED,
            module=AuditLog.Module.INVENTORY,
            description=f'Categoría "{nombre}" eliminada.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Listar productos'),
    post=extend_schema(tags=['Inventario'], summary='Crear producto'),
)
class ProductoListCreateView(generics.ListCreateAPIView):
    queryset = Producto.objects.select_related('sub_categoria').all()
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
    search_fields = ['nombre']
    filterset_fields = ['sub_categoria', 'categoria_principal', 'clasificacion']
    ordering_fields = ['nombre', 'costo_unitario', 'clasificacion', 'created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductoDetailSerializer
        return ProductoListSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.PRODUCTO_CREATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Producto "{instance.nombre}" creado en subcategoría {instance.sub_categoria.nombre}.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Detalle de producto'),
    patch=extend_schema(tags=['Inventario'], summary='Editar producto'),
    delete=extend_schema(tags=['Inventario'], summary='Eliminar producto'),
)
class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related('sub_categoria').all()
    serializer_class = ProductoDetailSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodegaPeroSoloGerenteElimina]
    http_method_names = ['get', 'patch', 'delete']

    def perform_update(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.PRODUCTO_UPDATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Producto "{instance.nombre}" actualizado.',
            request=self.request,
        )

    def perform_destroy(self, instance):
        nombre = instance.nombre
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.PRODUCTO_DELETED,
            module=AuditLog.Module.INVENTORY,
            description=f'Producto "{nombre}" eliminado del catálogo.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Listar bodegas'),
    post=extend_schema(tags=['Inventario'], summary='Crear bodega'),
)
class BodegaListCreateView(generics.ListCreateAPIView):
    queryset = Bodega.objects.select_related('administrador').all()
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
    search_fields = ['nombre', 'ubicacion']
    ordering_fields = ['nombre', 'created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BodegaDetailSerializer
        return BodegaListSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.BODEGA_CREATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Bodega "{instance.nombre}" creada, administrador: {instance.administrador.email}.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Detalle de bodega'),
    patch=extend_schema(tags=['Inventario'], summary='Editar bodega'),
    delete=extend_schema(tags=['Inventario'], summary='Eliminar bodega'),
)
class BodegaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bodega.objects.select_related('administrador').all()
    serializer_class = BodegaDetailSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodegaPeroSoloGerenteElimina]
    http_method_names = ['get', 'patch', 'delete']

    def perform_update(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.BODEGA_UPDATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Bodega "{instance.nombre}" actualizada.',
            request=self.request,
        )

    def perform_destroy(self, instance):
        nombre = instance.nombre
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.BODEGA_DELETED,
            module=AuditLog.Module.INVENTORY,
            description=f'Bodega "{nombre}" eliminada.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(
        tags=['Inventario'],
        summary='Listar stock de una bodega',
        description='Devuelve el stock aislado por bodega. '
                    'Filtre por bodega para obtener el Kardex específico.',
    ),
    post=extend_schema(tags=['Inventario'], summary='Registrar stock en bodega'),
)
class StockBodegaListCreateView(generics.ListCreateAPIView):
    serializer_class = StockBodegaSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
    filterset_fields = ['bodega', 'producto', 'producto__categoria_principal', 'producto__clasificacion']
    search_fields = ['producto__nombre']
    ordering_fields = ['stock_disponible', 'updated_at']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    def get_queryset(self):
        return StockBodega.objects.select_related(
            'bodega', 'producto',
        ).all()

    def perform_create(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.STOCK_CREATED,
            module=AuditLog.Module.INVENTORY,
            description=f'{instance.producto.nombre} registrado en {instance.bodega.nombre} con {instance.stock_disponible} und.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Detalle de stock'),
    patch=extend_schema(tags=['Inventario'], summary='Actualizar stock'),
    delete=extend_schema(tags=['Inventario'], summary='Eliminar registro de stock'),
)
class StockBodegaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StockBodegaSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodegaPeroSoloGerenteElimina]
    http_method_names = ['get', 'patch', 'delete']

    def get_queryset(self):
        return StockBodega.objects.select_related(
            'bodega', 'producto',
        ).all()

    def perform_update(self, serializer):
        instance = serializer.save()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.STOCK_UPDATED,
            module=AuditLog.Module.INVENTORY,
            description=f'Stock de {instance.producto.nombre} en {instance.bodega.nombre} actualizado a {instance.stock_disponible} und.',
            request=self.request,
        )

    def perform_destroy(self, instance):
        desc = f'{instance.producto.nombre} eliminado de {instance.bodega.nombre}.'
        instance.delete()
        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.STOCK_DELETED,
            module=AuditLog.Module.INVENTORY,
            description=desc,
            request=self.request,
        )


@extend_schema(
    tags=['Inventario'],
    summary='Alertas inteligentes de stock',
    description='Devuelve tres listas optimizadas: stock crítico (por debajo del 60% del mínimo), '
                'stock bajo (cerca del punto de reorden) y lotes por vencer en 30 días.'
)
class AlertasStockView(APIView):
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]

    def get(self, request, *args, **kwargs):
        hoy = timezone.now().date()
        limite_vencimiento = hoy + timedelta(days=30)

        # 1. Stock crítico: disponible < (inventario_seguridad * 0.6)
        stock_critico = StockBodega.objects.select_related('bodega', 'producto').filter(
            stock_disponible__lt=F('producto__inventario_seguridad') * 0.6
        )

        # 2. Por vencer: fecha_vencimiento <= 30 días y hay stock (incluye ya vencidos)
        por_vencer = StockBodega.objects.select_related('bodega', 'producto').filter(
            fecha_vencimiento__lte=limite_vencimiento,
            stock_disponible__gt=0
        )

        # 3. Stock bajo: (inventario_seguridad * 0.6) <= disponible <= punto_reorden
        stock_bajo = StockBodega.objects.select_related('bodega', 'producto').filter(
            stock_disponible__lte=F('producto__punto_reorden'),
            stock_disponible__gte=F('producto__inventario_seguridad') * 0.6
        )

        def map_alerta(item):
            return {
                "id": item.id,
                "producto_nombre": item.producto.nombre,
                "bodega_nombre": item.bodega.nombre,
                "stock_disponible": item.stock_disponible,
                "unidad_medida_display": item.producto.get_unidad_medida_display(),
                "coordenada_fisica": item.coordenada_fisica,
                "fecha_vencimiento": item.fecha_vencimiento
            }

        return Response({
            'stock_critico': [map_alerta(i) for i in stock_critico],
            'por_vencer': [map_alerta(i) for i in por_vencer],
            'stock_bajo': [map_alerta(i) for i in stock_bajo]
        })
