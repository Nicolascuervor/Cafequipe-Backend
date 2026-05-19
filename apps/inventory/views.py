# apps/inventory/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.users.permissions import EsGerente, EsGerenteOJefeBodega, EsGerenteOSoloLectura
from .models import Categoria, Producto, Bodega, StockBodega
from .serializers import (
    CategoriaSerializer,
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
class CategoriaListCreateView(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
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
class CategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
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
    queryset = Producto.objects.select_related('categoria').all()
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
    search_fields = ['nombre', 'codigo_barras']
    filterset_fields = ['categoria', 'clasificacion']
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
            description=f'Producto "{instance.nombre}" creado en categoría {instance.categoria.nombre}.',
            request=self.request,
        )


@extend_schema_view(
    get=extend_schema(tags=['Inventario'], summary='Detalle de producto'),
    patch=extend_schema(tags=['Inventario'], summary='Editar producto'),
    delete=extend_schema(tags=['Inventario'], summary='Eliminar producto'),
)
class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related('categoria').all()
    serializer_class = ProductoDetailSerializer
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
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
    permission_classes = [IsAuthenticated, EsGerente]
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
    filterset_fields = ['bodega', 'producto']
    search_fields = ['producto__nombre']
    ordering_fields = ['stock_disponible', 'updated_at']

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
    permission_classes = [IsAuthenticated, EsGerenteOJefeBodega]
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
