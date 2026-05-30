from rest_framework import permissions

class IsJefeProduccionOrGerente(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.rol in ['JPR', 'GER']
