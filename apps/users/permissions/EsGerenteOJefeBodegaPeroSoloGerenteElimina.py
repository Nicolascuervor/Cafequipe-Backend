from rest_framework.permissions import BasePermission


class EsGerenteOJefeBodegaPeroSoloGerenteElimina(BasePermission):
    message = 'Solo el Gerente puede eliminar este recurso. Jefes de Bodega solo pueden consultar o modificar.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # El DELETE es la operación más destructiva, restringida al Gerente (Admin)
        if request.method == 'DELETE':
            return request.user.rol == 'GER'

        # Para otros métodos (GET, POST, PATCH, PUT), permitimos a Gerente o Jefe de Bodega
        return request.user.rol in ['GER', 'JBD']
