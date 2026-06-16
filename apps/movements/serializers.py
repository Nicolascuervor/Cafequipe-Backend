from rest_framework import serializers
from django.db import transaction
from .models import Recepcion, DetalleRecepcion, SolicitudInterna, DetalleSolicitud, Movimiento, TipoMovimiento, EstadoSolicitud
from apps.inventory.models import StockBodega, Producto

class DetalleRecepcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleRecepcion
        fields = ['producto', 'cantidad', 'costo_unitario_ingreso', 'lote_proveedor']

class RecepcionSerializer(serializers.ModelSerializer):
    detalles = DetalleRecepcionSerializer(many=True)

    class Meta:
        model = Recepcion
        fields = ['id', 'bodega', 'proveedor', 'observaciones', 'detalles']

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        bodega = validated_data['bodega']
        usuario = self.context['request'].user

        with transaction.atomic():
            recepcion = Recepcion.objects.create(registrado_por=usuario, **validated_data)
            
            for detalle in detalles_data:
                producto = detalle['producto']
                cantidad = detalle['cantidad']
                
                # Crear detalle recepción
                DetalleRecepcion.objects.create(recepcion=recepcion, **detalle)

                # Actualizar Stock
                stock, _ = StockBodega.objects.get_or_create(
                    bodega=bodega, producto=producto,
                    defaults={'codigo_lote': detalle.get('lote_proveedor', 'LOTE_INICIAL')}
                )
                stock.stock_disponible += cantidad
                stock.save()

                # Generar Movimiento Automático (CP-044)
                Movimiento.objects.create(
                    tipo=TipoMovimiento.ENTRADA,
                    producto=producto,
                    bodega=bodega,
                    cantidad=cantidad,
                    recepcion=recepcion,
                    usuario=usuario
                )
            
        return recepcion


class DetalleSolicitudSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_unidad = serializers.ReadOnlyField(source='producto.get_unidad_medida_display')

    class Meta:
        model = DetalleSolicitud
        fields = ['id', 'producto', 'producto_nombre', 'producto_unidad', 'cantidad']
        read_only_fields = ['id']

class SolicitudInternaSerializer(serializers.ModelSerializer):
    detalles = DetalleSolicitudSerializer(many=True)
    solicitante_nombre = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = SolicitudInterna
        fields = ['id', 'estado', 'motivo', 'detalles', 'solicitante_nombre', 'created_at']
        read_only_fields = ['id', 'estado', 'created_at']

    def get_solicitante_nombre(self, obj):
        return f"{obj.solicitante.first_name} {obj.solicitante.last_name}".strip() or obj.solicitante.username

    def validate_detalles(self, value):
        for det in value:
            if det['cantidad'] <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a cero.")
        return value

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        usuario = self.context['request'].user
        
        with transaction.atomic():
            solicitud = SolicitudInterna.objects.create(solicitante=usuario, **validated_data)
            for det in detalles_data:
                DetalleSolicitud.objects.create(solicitud=solicitud, **det)
        return solicitud

class MovimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimiento
        fields = '__all__'
