from rest_framework.permissions import BasePermission


class EsGerenteOJefeBodegaPeroSoloGerenteElimina(BasePermission):
    message = 'Solo el Gerente puede eliminar este recurso. Jefes de Bodega solo pueden consultar o modificar.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False


        if request.method == 'DELETE':
            return request.user.rol == 'GER'

        return request.user.rol in ['GER', 'JBD']
