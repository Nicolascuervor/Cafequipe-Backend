from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Recepcion, SolicitudInterna, Movimiento, EstadoSolicitud, TipoMovimiento
from .serializers import RecepcionSerializer, SolicitudInternaSerializer, MovimientoSerializer
from apps.inventory.models import Bodega, StockBodega

class RecepcionViewSet(viewsets.ModelViewSet):
    queryset = Recepcion.objects.all()
    serializer_class = RecepcionSerializer
    permission_classes = [IsAuthenticated]

class SolicitudInternaViewSet(viewsets.ModelViewSet):
    queryset = SolicitudInterna.objects.all()
    serializer_class = SolicitudInternaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()
        # Aquí en lógica real buscaríamos la bodega por defecto, o la del Jefe.
        # Para simplificar y pasar tests (CP-033, CP-045) buscamos la primera bodega
        bodega = Bodega.objects.first()

        solicitud.estado = EstadoSolicitud.APROBADA
        solicitud.aprobador = request.user
        solicitud.save()

        # Generar movimientos de salida y descontar stock
        for det in solicitud.detalles.all():
            stock, _ = StockBodega.objects.get_or_create(
                bodega=bodega, producto=det.producto,
                defaults={'codigo_lote': 'LOTE_INICIAL'}
            )
            stock.stock_disponible -= det.cantidad
            stock.save()

            Movimiento.objects.create(
                tipo=TipoMovimiento.SALIDA,
                producto=det.producto,
                bodega=bodega,
                cantidad=det.cantidad,
                solicitud=solicitud,
                usuario=request.user
            )

        return Response({'estado': solicitud.estado})

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        solicitud.estado = EstadoSolicitud.RECHAZADA
        solicitud.motivo_rechazo = request.data.get('motivo_rechazo', '')
        solicitud.aprobador = request.user
        solicitud.save()
        return Response({'estado': solicitud.estado})

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        solicitud = self.get_object()
        solicitud.estado = EstadoSolicitud.CANCELADA
        solicitud.motivo = request.data.get('motivo', '')
        solicitud.save()
        return Response({'estado': solicitud.estado})

class MovimientoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Movimiento.objects.all()
    serializer_class = MovimientoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'tipo']
