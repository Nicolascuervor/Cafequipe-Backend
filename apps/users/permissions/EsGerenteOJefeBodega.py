from rest_framework.permissions import BasePermission, SAFE_METHODS

class EsGerenteOJefeBodega(BasePermission):
    message = 'Solo Gerente o Jefe de Bodega pueden realizar esta acción. Operarios solo lectura.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.rol in ['GER', 'JBD']:
            return True
        if request.user.rol == 'OPR' and request.method in SAFE_METHODS:
            return True
        return False
