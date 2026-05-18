# apps/audit/services.py
"""
Servicio central de auditoría.
Todos los módulos del sistema usan esta función para registrar acciones.
NUNCA se debe crear un AuditLog directamente desde una vista o serializer.
"""
from .models import AuditLog


def get_client_ip(request):
    """Extrae la IP real del cliente, considerando proxies."""
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_audit_log(*, user, action, module, description, request=None):
    """
    Crea un registro inmutable de auditoría.

    Args:
        user:        Instancia del User que realizó la acción.
        action:      Valor de AuditLog.Action (ej. AuditLog.Action.LOGIN).
        module:      Valor de AuditLog.Module (ej. AuditLog.Module.AUTH).
        description: Texto breve describiendo la acción.
        request:     HttpRequest (opcional) para extraer la IP.
    """
    return AuditLog.objects.create(
        user=user,
        user_email=user.email if user else 'sistema',
        action=action,
        module=module,
        description=description,
        ip_address=get_client_ip(request),
    )
