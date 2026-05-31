from rest_framework import serializers
from .models import (
    Receta, IngredienteReceta, OrdenProduccion,
    ParametroCalidad, ControlCalidadLote, ValorParametroCalidad
)
from apps.inventory.models import Producto

class IngredienteRecetaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto_insumo.nombre')
    producto_unidad_medida_display = serializers.ReadOnlyField(source='producto_insumo.get_unidad_medida_display')
    categoria = serializers.ReadOnlyField(source='producto_insumo.categoria_principal')

    class Meta:
        model = IngredienteReceta
        fields = ['id', 'producto_insumo', 'producto_nombre', 'producto_unidad_medida_display', 'categoria', 'cantidad_necesaria']

class RecetaSerializer(serializers.ModelSerializer):
    ingredientes = IngredienteRecetaSerializer(many=True)
    producto_nombre = serializers.ReadOnlyField(source='producto_terminado.nombre')
    producto_unidad_medida_display = serializers.ReadOnlyField(source='producto_terminado.get_unidad_medida_display')

    class Meta:
        model = Receta
        fields = [
            'id', 'producto_terminado', 'producto_nombre', 'producto_unidad_medida_display', 
            'rendimiento_base', 'instrucciones', 'activa', 
            'ingredientes', 'created_at', 'updated_at'
        ]

    def validate_ingredientes(self, value):
        if not value:
            raise serializers.ValidationError("Una receta debe tener al menos un ingrediente.")
        return value

    def validate(self, data):
        producto = data.get('producto_terminado')
        if producto and getattr(producto, 'categoria_principal', None) != 'PR':
            raise serializers.ValidationError({"producto_terminado": "Solo se pueden crear recetas para Productos Terminados (PR)."})
        return data

    def create(self, validated_data):
        ingredientes_data = validated_data.pop('ingredientes')
        receta = Receta.objects.create(**validated_data)
        
        for ingrediente_data in ingredientes_data:
            producto_insumo = ingrediente_data['producto_insumo']
            if producto_insumo.categoria_principal not in ['MP', 'IN']:
                receta.delete()
                raise serializers.ValidationError(f"El ingrediente {producto_insumo.nombre} no es Materia Prima ni Insumo.")
            IngredienteReceta.objects.create(receta=receta, **ingrediente_data)
        
        return receta

    def update(self, instance, validated_data):
        ingredientes_data = validated_data.pop('ingredientes', None)
        
        instance.producto_terminado = validated_data.get('producto_terminado', instance.producto_terminado)
        instance.rendimiento_base = validated_data.get('rendimiento_base', instance.rendimiento_base)
        instance.instrucciones = validated_data.get('instrucciones', instance.instrucciones)
        instance.activa = validated_data.get('activa', instance.activa)
        instance.save()

        if ingredientes_data is not None:
            instance.ingredientes.all().delete()
            for ingrediente_data in ingredientes_data:
                producto_insumo = ingrediente_data['producto_insumo']
                if producto_insumo.categoria_principal not in ['MP', 'IN']:
                    raise serializers.ValidationError(f"El ingrediente {producto_insumo.nombre} no es Materia Prima ni Insumo.")
                IngredienteReceta.objects.create(receta=instance, **ingrediente_data)

        return instance

class OrdenProduccionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='receta.producto_terminado.nombre')
    responsable_nombre = serializers.ReadOnlyField(source='responsable.get_full_name')

    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'receta', 'producto_nombre', 'codigo_lote', 'estado',
            'cantidad_esperada', 'cantidad_obtenida', 'fecha_inicio',
            'fecha_fin', 'fecha_vencimiento', 'responsable', 'responsable_nombre',
            'bodega_destino', 'created_at', 'updated_at'
        ]
        read_only_fields = ['responsable']

    def to_internal_value(self, data):
        # Aseguramos que si el frontend envía un string vacío o null, lo eliminamos
        # para que Django use los valores por defecto (autogenerados).
        mutable_data = data.copy() if hasattr(data, 'copy') else data
        
        # Eliminar si viene null o string vacío
        if 'codigo_lote' in mutable_data and (mutable_data['codigo_lote'] is None or not str(mutable_data['codigo_lote']).strip()):
            mutable_data.pop('codigo_lote')
            
        if 'fecha_vencimiento' in mutable_data and (mutable_data['fecha_vencimiento'] is None or not str(mutable_data['fecha_vencimiento']).strip()):
            mutable_data.pop('fecha_vencimiento')
            
        # Parseo seguro: Reemplazar comas por puntos (ej: "3,00" -> "3.00")
        if 'cantidad_obtenida' in mutable_data and isinstance(mutable_data['cantidad_obtenida'], str):
            mutable_data['cantidad_obtenida'] = mutable_data['cantidad_obtenida'].replace(',', '.')

        # Parseo seguro: Si el frontend envía el nombre de la bodega ("Bodega Central") en lugar del ID (1)
        if 'bodega_destino' in mutable_data and isinstance(mutable_data['bodega_destino'], str) and not mutable_data['bodega_destino'].isdigit():
            from apps.inventory.models import Bodega
            bodega = Bodega.objects.filter(nombre__iexact=mutable_data['bodega_destino'].strip()).first()
            if bodega:
                mutable_data['bodega_destino'] = bodega.id
            
        return super().to_internal_value(mutable_data)

class ParametroCalidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametroCalidad
        fields = ['id', 'nombre', 'tipo_dato', 'activo']

class ValorParametroCalidadSerializer(serializers.ModelSerializer):
    parametro_nombre = serializers.ReadOnlyField(source='parametro.nombre')
    tipo_dato = serializers.ReadOnlyField(source='parametro.tipo_dato')

    class Meta:
        model = ValorParametroCalidad
        fields = ['id', 'parametro', 'parametro_nombre', 'tipo_dato', 'valor_booleano', 'valor_decimal', 'valor_texto']

class ControlCalidadLoteSerializer(serializers.ModelSerializer):
    valores = ValorParametroCalidadSerializer(many=True)

    class Meta:
        model = ControlCalidadLote
        fields = ['id', 'orden_produccion', 'aprobado_final', 'observaciones', 'valores']
        # Desactivamos el validador único por defecto de DRF para poder hacer "upsert"
        extra_kwargs = {
            'orden_produccion': {
                'validators': []
            }
        }

    def create(self, validated_data):
        valores_data = validated_data.pop('valores')
        orden = validated_data.pop('orden_produccion')
        
        # Upsert: Si ya existe una bitácora para esta orden, la actualizamos
        control, created = ControlCalidadLote.objects.update_or_create(
            orden_produccion=orden,
            defaults=validated_data
        )
        
        # Si ya existía, borramos las métricas anteriores para colocar las nuevas
        if not created:
            control.valores.all().delete()
            
        for val_data in valores_data:
            ValorParametroCalidad.objects.create(control=control, **val_data)
        return control

    def update(self, instance, validated_data):
        valores_data = validated_data.pop('valores', None)
        instance.aprobado_final = validated_data.get('aprobado_final', instance.aprobado_final)
        instance.observaciones = validated_data.get('observaciones', instance.observaciones)
        instance.save()

        if valores_data is not None:
            # Recreate values
            instance.valores.all().delete()
            for val_data in valores_data:
                ValorParametroCalidad.objects.create(control=instance, **val_data)
        return instance

from .models import TicketInsumo, DetalleTicketInsumo

class DetalleTicketInsumoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    id = serializers.IntegerField(required=False)

    class Meta:
        model = DetalleTicketInsumo
        fields = ['id', 'producto', 'producto_nombre', 'cantidad_solicitada', 'cantidad_entregada', 'lote_origen']
        read_only_fields = ['producto', 'cantidad_entregada', 'lote_origen']

class TicketInsumoSerializer(serializers.ModelSerializer):
    detalles = DetalleTicketInsumoSerializer(many=True)
    orden_codigo = serializers.ReadOnlyField(source='orden_produccion.codigo_lote')
    despachador_nombre = serializers.ReadOnlyField(source='despachador.get_full_name')
    solicitante_id = serializers.ReadOnlyField(source='orden_produccion.responsable.id')
    solicitante_nombre = serializers.ReadOnlyField(source='orden_produccion.responsable.get_full_name')

    class Meta:
        model = TicketInsumo
        fields = ['id', 'orden_produccion', 'orden_codigo', 'estado', 'fecha_solicitud', 'fecha_entrega', 'despachador', 'despachador_nombre', 'solicitante_id', 'solicitante_nombre', 'razon_rechazo', 'detalles']
        read_only_fields = ['orden_produccion', 'fecha_solicitud', 'fecha_entrega', 'despachador']

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        
        user = self.context['request'].user
        if user.rol == 'OPR' and instance.estado == 'REC':
            instance.estado = 'SOL'
            instance.razon_rechazo = None
            
        instance = super().update(instance, validated_data)
        
        for detalle_data in detalles_data:
            detalle_id = detalle_data.get('id')
            if detalle_id:
                try:
                    detalle = instance.detalles.get(id=detalle_id)
                    if 'cantidad_solicitada' in detalle_data:
                        detalle.cantidad_solicitada = detalle_data['cantidad_solicitada']
                        detalle.save()
                except DetalleTicketInsumo.DoesNotExist:
                    pass
                    
        return instance

