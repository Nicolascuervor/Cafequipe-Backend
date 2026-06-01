from rest_framework import viewsets, serializers
from apps.inventory.models import StockBodega
from .models import Receta, OrdenProduccion, ParametroCalidad, ControlCalidadLote, EstadoOrden, EstadoTicket
from .serializers import (
    RecetaSerializer, OrdenProduccionSerializer,
    ParametroCalidadSerializer, ControlCalidadLoteSerializer
)
from .permissions import IsJefeProduccionOrGerente, OperarioPuedeCrearYEditarOrdenes
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from apps.inventory.models import Bodega
from .models import TicketInsumo, DetalleTicketInsumo, EstadoTicket
from .serializers import TicketInsumoSerializer

class RecetaViewSet(viewsets.ModelViewSet):

    queryset = Receta.objects.all().select_related('producto_terminado').prefetch_related('ingredientes__producto_insumo')
    serializer_class = RecetaSerializer
    permission_classes = [IsJefeProduccionOrGerente]
    filterset_fields = ['activa', 'producto_terminado']
    search_fields = ['producto_terminado__nombre', 'instrucciones']
    ordering_fields = ['created_at', 'rendimiento_base']
    
    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

class OrdenProduccionViewSet(viewsets.ModelViewSet):

    queryset = OrdenProduccion.objects.all().select_related('receta__producto_terminado', 'responsable')
    serializer_class = OrdenProduccionSerializer
    permission_classes = [OperarioPuedeCrearYEditarOrdenes]
    filterset_fields = ['estado', 'receta__producto_terminado', 'codigo_lote']
    search_fields = ['codigo_lote']
    ordering_fields = ['created_at', 'fecha_vencimiento']

    def perform_create(self, serializer):
        orden = serializer.save(responsable=self.request.user)
        
        # Generación automática del Ticket de Insumos según la receta
        from .models import TicketInsumo, DetalleTicketInsumo
        ticket = TicketInsumo.objects.create(
            orden_produccion=orden
        )
        
        rendimiento_base = orden.receta.rendimiento_base
        factor = orden.cantidad_esperada / rendimiento_base
        
        for ingrediente in orden.receta.ingredientes.all():
            cantidad_req = ingrediente.cantidad_necesaria * factor
            DetalleTicketInsumo.objects.create(
                ticket=ticket,
                producto=ingrediente.producto_insumo,
                cantidad_solicitada=cantidad_req
            )

    def _validate_en_proceso(self, instance):
        if hasattr(instance, 'ticket_insumos') and instance.ticket_insumos.estado != EstadoTicket.ENTREGADO:
            raise serializers.ValidationError({"estado": "No se puede iniciar la producción (En Proceso) sin que el Ticket de Insumos haya sido aprobado y entregado."})

    def _validate_completada(self, instance, serializer):
        if hasattr(instance, 'ticket_insumos') and instance.ticket_insumos.estado != EstadoTicket.ENTREGADO:
            raise serializers.ValidationError({"estado": "No se puede completar la orden sin haber despachado (entregado) el Ticket de Insumos correspondiente."})

        if not hasattr(instance, 'control_calidad') or not instance.control_calidad.aprobado_final:
            raise serializers.ValidationError({"estado": "No se puede completar la orden sin un Control de Calidad Aprobado."})
        
        bodega_destino = serializer.validated_data.get('bodega_destino', instance.bodega_destino)
        cantidad_obtenida = serializer.validated_data.get('cantidad_obtenida', instance.cantidad_obtenida)

        if not bodega_destino:
            raise serializers.ValidationError({"bodega_destino": "Debe especificar una bodega de destino para el producto terminado al completar."})
        if not cantidad_obtenida or cantidad_obtenida <= 0:
            raise serializers.ValidationError({"cantidad_obtenida": "Debe especificar la cantidad real obtenida mayor a 0."})

        producto_terminado = instance.receta.producto_terminado
        stock, _ = StockBodega.objects.get_or_create(
            bodega=bodega_destino,
            producto=producto_terminado,
            codigo_lote=instance.codigo_lote,
            defaults={
                'stock_disponible': 0,
                'fecha_vencimiento': instance.fecha_vencimiento
            }
        )
        stock.stock_disponible += cantidad_obtenida
        stock.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        nuevo_estado = serializer.validated_data.get('estado', instance.estado)

        if nuevo_estado == EstadoOrden.EN_PROCESO and instance.estado != EstadoOrden.EN_PROCESO:
            self._validate_en_proceso(instance)

        if nuevo_estado == EstadoOrden.COMPLETADA and instance.estado != EstadoOrden.COMPLETADA:
            self._validate_completada(instance, serializer)

        serializer.save()

class ParametroCalidadViewSet(viewsets.ModelViewSet):
    queryset = ParametroCalidad.objects.all()
    serializer_class = ParametroCalidadSerializer
    permission_classes = [IsJefeProduccionOrGerente]
    filterset_fields = ['activo']

class ControlCalidadLoteViewSet(viewsets.ModelViewSet):
    queryset = ControlCalidadLote.objects.all().select_related('orden_produccion').prefetch_related('valores__parametro')
    serializer_class = ControlCalidadLoteSerializer
    permission_classes = [IsJefeProduccionOrGerente]


class TicketInsumoViewSet(viewsets.ModelViewSet):
    queryset = TicketInsumo.objects.all().select_related('orden_produccion', 'despachador').prefetch_related('detalles__producto')
    serializer_class = TicketInsumoSerializer
    permission_classes = [OperarioPuedeCrearYEditarOrdenes]
    filterset_fields = ['estado', 'orden_produccion__responsable']

    def _procesar_detalle_ticket(self, detalle, bodega_origen):
        cantidad_pendiente = detalle.cantidad_solicitada

        stocks = StockBodega.objects.filter(
            bodega=bodega_origen,
            producto=detalle.producto,
            stock_disponible__gt=0
        ).order_by('fecha_vencimiento')

        lotes_usados = []
        
        for stock in stocks:
            if cantidad_pendiente <= 0:
                break
            if stock.stock_disponible >= cantidad_pendiente:
                stock.stock_disponible -= cantidad_pendiente
                lotes_usados.append(f"{stock.codigo_lote} ({cantidad_pendiente})")
                stock.save()
                cantidad_pendiente = 0
            else:
                cantidad_pendiente -= stock.stock_disponible
                lotes_usados.append(f"{stock.codigo_lote} ({stock.stock_disponible})")
                stock.stock_disponible = 0
                stock.save()

        if cantidad_pendiente > 0:
            if bodega_origen.permite_stock_negativo:
                stock_gen, _ = StockBodega.objects.get_or_create(
                    bodega=bodega_origen,
                    producto=detalle.producto,
                    codigo_lote="DIFERIDO_AUTO",
                    defaults={'stock_disponible': 0}
                )
                stock_gen.stock_disponible -= cantidad_pendiente
                stock_gen.save()
                lotes_usados.append(f"Diferido_Auto ({cantidad_pendiente})")
                cantidad_pendiente = 0
            else:
                raise ValueError(f"Stock insuficiente para {detalle.producto.nombre}. Faltan {cantidad_pendiente} y la bodega no permite stock negativo.")
        
        detalle.cantidad_entregada = detalle.cantidad_solicitada - cantidad_pendiente
        detalle.lote_origen = ", ".join(lotes_usados)
        detalle.save()

    @action(detail=True, methods=['post'])
    def entregar(self, request, pk=None):
        ticket = self.get_object()
        if ticket.estado == EstadoTicket.ENTREGADO:
            return Response({'detail': 'El ticket ya ha sido entregado.'}, status=status.HTTP_400_BAD_REQUEST)
        
        bodega_id = request.data.get('bodega_origen_id')
        if not bodega_id:
            return Response({'detail': 'Debe especificar la bodega de origen (bodega_origen_id).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bodega_origen = Bodega.objects.get(id=bodega_id)
        except Bodega.DoesNotExist:
            return Response({'detail': 'Bodega no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                for detalle in ticket.detalles.all():
                    self._procesar_detalle_ticket(detalle, bodega_origen)

                ticket.estado = EstadoTicket.ENTREGADO
                ticket.fecha_entrega = timezone.now()
                ticket.despachador = request.user
                ticket.save()
                
            return Response({'status': 'Ticket entregado y stock descontado con éxito.'})
            
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

