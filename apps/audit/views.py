# apps/audit/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.users.permissions import EsGerente
from .models import AuditLog
from .serializers import AuditLogSerializer


@extend_schema(
    tags=['Auditoría'],
    summary='Listar registros de auditoría',
    description='Solo el Gerente puede consultar la auditoría del sistema. '
                'Soporta filtros por acción, módulo, usuario y rango de fechas.',
)
class AuditLogListView(generics.ListAPIView):
   
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
   
    filterset_fields = ['action', 'module', 'user']
    search_fields = ['user_email', 'description']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
