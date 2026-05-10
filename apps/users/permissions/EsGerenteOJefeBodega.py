from rest_framework.permissions import BasePermission


class EsGerenteOJefeBodega(BasePermission):
    message = 'Solo Gerente o Jefe de Bodega pueden realizar esta acción.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol in ['GER', 'JBD']
        )
