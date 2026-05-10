from rest_framework.permissions import BasePermission


class EsGerente(BasePermission):
    message = 'Solo el Gerente puede realizar esta acción.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.es_gerente
        )
