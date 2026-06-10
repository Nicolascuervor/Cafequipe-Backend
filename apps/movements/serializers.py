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
    class Meta:
        model = DetalleSolicitud
        fields = ['producto', 'cantidad']

class SolicitudInternaSerializer(serializers.ModelSerializer):
    detalles = DetalleSolicitudSerializer(many=True)

    class Meta:
        model = SolicitudInterna
        fields = ['id', 'estado', 'motivo', 'detalles']
        read_only_fields = ['id', 'estado']

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
