from rest_framework.permissions import BasePermission


class EsGerenteOSoloLectura(BasePermission):
    message = 'Solo el Gerente puede modificar. Otros roles solo lectura.'

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user and request.user.is_authenticated
        return (
            request.user
            and request.user.is_authenticated
            and request.user.es_gerente
        )
