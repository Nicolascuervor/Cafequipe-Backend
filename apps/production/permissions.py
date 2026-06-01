from rest_framework import permissions

class IsJefeProduccionOrGerente(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.rol in ['JPR', 'GER']

class OperarioPuedeCrearYEditarOrdenes(permissions.BasePermission):

    message = 'Operarios solo pueden editar Tickets si han sido rechazados por Producción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.rol in ['JPR', 'GER']:
            return True
        if request.user.rol == 'OPR':
            if request.method in permissions.SAFE_METHODS or request.method in ['POST', 'PATCH', 'PUT']:
                return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.rol in ['JPR', 'GER']:
            return True
        if request.user.rol == 'OPR':
            if request.method in permissions.SAFE_METHODS:
                return True
            if request.method in ['PATCH', 'PUT']:
                # Check if it's a TicketInsumo (has orden_produccion and estado)
                if hasattr(obj, 'orden_produccion') and hasattr(obj, 'estado'):
                    if obj.orden_produccion.responsable == request.user and obj.estado == 'REC':
                        return True
        return False
