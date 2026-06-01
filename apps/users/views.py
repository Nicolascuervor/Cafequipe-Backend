# apps/users/views.py

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from .permissions import EsGerente, EsGerenteOSoloLectura
from .serializers import (
    UserRegisterSerializer,
    UserListSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer,
)

from django.core.cache import cache
from .throttles import LoginFailedThrottle

User = get_user_model()


@extend_schema(
    tags=['Auth'],
    summary='Iniciar sesión',
    description='Autentica al usuario y devuelve los tokens JWT. '
                'Registra la acción en el log de auditoría. Aplica bloqueo temporal tras 5 intentos fallidos.',
)
class AuditedLoginView(TokenObtainPairView):

    throttle_classes = [LoginFailedThrottle]

    def post(self, request, *args, **kwargs):
        # Obtener IP para el cache de intentos fallidos
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        cache_key = f"login_failed_count_{ip}"

        email = request.data.get('email', '')

        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                # Éxito: Limpiar contador de intentos fallidos
                cache.delete(cache_key)

                # El serializer ya validó las credenciales y el user está disponible
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid()
                user = serializer.user
                create_audit_log(
                    user=user,
                    action=AuditLog.Action.LOGIN,
                    module=AuditLog.Module.AUTH,
                    description='Inicio de sesión exitoso.',
                    request=request,
                )
                
                # Emitir señal estándar de login para que notificaciones (y otros) puedan escuchar
                from django.contrib.auth.signals import user_logged_in
                user_logged_in.send(sender=user.__class__, request=request, user=user)

            return response
        except Exception as e:

            failed_count = cache.get(cache_key, 0)
            cache.set(cache_key, failed_count + 1, 900)
            user_inst = None
            if email:
                try:
                    user_inst = User.objects.filter(email=email).first()
                except Exception:
                    pass

            create_audit_log(
                user=user_inst,
                user_email=email or 'desconocido',
                action=AuditLog.Action.LOGIN_FAILED,
                module=AuditLog.Module.AUTH,
                description='Intento de inicio de sesión fallido.',
                request=request,
            )

            raise e


@extend_schema(
    tags=['Auth'],
    summary='Cerrar sesión',
    description='Invalida el refresh token y registra la acción en auditoría.',
)
class AuditedLogoutView(TokenBlacklistView):
    """Logout que registra la acción en auditoría."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            create_audit_log(
                user=request.user,
                action=AuditLog.Action.LOGOUT,
                module=AuditLog.Module.AUTH,
                description='Cierre de sesión.',
                request=request,
            )
        return response


@extend_schema(
    tags=['Auth'],
    summary='Registrar usuario nuevo',
    description='Solo el Gerente puede crear cuentas. '
                'El email es el identificador único de autenticación.',
)
class UserRegisterView(generics.CreateAPIView):
   
    serializer_class = UserRegisterSerializer
    permission_classes = [IsAuthenticated, EsGerente]

@extend_schema_view(
    get=extend_schema(
        tags=['Auth'],
        summary='Ver mi perfil',
        description='Devuelve los datos del usuario autenticado.',
    ),
    patch=extend_schema(
        tags=['Auth'],
        summary='Actualizar mi perfil',
        description='Permite actualizar nombre, apellido y teléfono. '
                    'El rol y el email NO se pueden cambiar desde aquí.',
    ),
)
class UserMeView(generics.RetrieveUpdateAPIView):
    
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch'] 

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['Auth'],
    summary='Cambiar contraseña',
    description='Requiere la contraseña actual y la nueva contraseña. '
                'La nueva contraseña debe cumplir las reglas de validación.',
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request} 
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])

        return Response(
            {'detail': 'Contraseña actualizada correctamente.'},
            status=status.HTTP_200_OK
        )

@extend_schema_view(
    list=extend_schema(
        tags=['Usuarios'],
        summary='Listar usuarios',
        description='Gerente ve todos. Otros roles solo lectura.',
    ),
    retrieve=extend_schema(
        tags=['Usuarios'],
        summary='Detalle de usuario',
    ),
    partial_update=extend_schema(
        tags=['Usuarios'],
        summary='Editar usuario',
        description='Solo el Gerente puede editar datos de otros usuarios, '
                    'incluyendo cambiar roles y activar/desactivar cuentas.',
    ),
    destroy=extend_schema(
        tags=['Usuarios'],
        summary='Desactivar usuario',
        description='Soft delete: desactiva la cuenta en lugar de borrarla. '
                    'Los datos se preservan para auditoría.',
    ),
)
class UserListView(generics.ListAPIView):
  
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, EsGerente]
   
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_name', 'rol']
    filterset_fields = ['rol', 'is_active']


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
   
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, EsGerente]
    http_method_names = ['get', 'patch', 'delete']

    def perform_destroy(self, instance):
        from apps.audit.models import AuditLog
        from apps.audit.services import create_audit_log

        instance.is_active = False
        instance.save(update_fields=['is_active'])

        create_audit_log(
            user=self.request.user,
            action=AuditLog.Action.USER_DEACTIVATED,
            module=AuditLog.Module.USERS,
            description=f'Usuario {instance.email} desactivado por {self.request.user.email}.',
            request=self.request,
        )

