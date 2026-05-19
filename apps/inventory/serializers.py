# apps/inventory/serializers.py
from rest_framework import serializers
from .models import Categoria, Producto, Bodega, StockBodega



class CategoriaSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='inventory:categoria-detail')

    class Meta:
        model = Categoria
        fields = ['url', 'id', 'nombre', 'descripcion', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']



class ProductoListSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='inventory:producto-detail')
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    clasificacion_display = serializers.CharField(source='get_clasificacion_display', read_only=True)

    class Meta:
        model = Producto
        fields = [
            'url', 'id', 'codigo_barras', 'nombre',
            'categoria', 'categoria_nombre',
            'costo_unitario',
            'clasificacion', 'clasificacion_display',
            'inventario_seguridad', 'punto_reorden',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductoDetailSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='inventory:producto-detail')
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    clasificacion_display = serializers.CharField(source='get_clasificacion_display', read_only=True)

    class Meta:
        model = Producto
        fields = [
            'url', 'id', 'codigo_barras', 'nombre',
            'categoria', 'categoria_nombre',
            'costo_unitario',
            'clasificacion', 'clasificacion_display',
            'inventario_seguridad', 'punto_reorden',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BodegaListSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='inventory:bodega-detail')
    administrador_nombre = serializers.CharField(
        source='administrador.get_full_name', read_only=True,
    )

    class Meta:
        model = Bodega
        fields = [
            'url', 'id', 'nombre', 'ubicacion',
            'administrador', 'administrador_nombre',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BodegaDetailSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='inventory:bodega-detail')
    administrador_nombre = serializers.CharField(
        source='administrador.get_full_name', read_only=True,
    )

    class Meta:
        model = Bodega
        fields = [
            'url', 'id', 'nombre', 'ubicacion',
            'administrador', 'administrador_nombre',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_administrador(self, value):
        if value.rol not in ['JBD', 'GER']:
            raise serializers.ValidationError(
                'El usuario asignado debe ser Jefe de Bodega (JBD) o Gerente (GER).'
            )
        return value



class StockBodegaSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='inventory:stock-detail')
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    bodega_nombre = serializers.CharField(source='bodega.nombre', read_only=True)
    posicion_inventario = serializers.IntegerField(read_only=True)
    requiere_reorden = serializers.BooleanField(read_only=True)

    class Meta:
        model = StockBodega
        fields = [
            'url', 'id',
            'bodega', 'bodega_nombre',
            'producto', 'producto_nombre',
            'stock_disponible',
            'pedidos_abiertos',
            'ordenes_atrasadas',
            'posicion_inventario',
            'requiere_reorden',
            'updated_at',
        ]
        read_only_fields = ['id', 'posicion_inventario', 'requiere_reorden', 'updated_at']
