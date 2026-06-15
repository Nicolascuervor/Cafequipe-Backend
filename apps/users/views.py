# apps/users/views.py

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from drf_spectacular.utils import extend_schema, extend_schema_view

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from apps.notifications.services import send_password_reset_email

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from .permissions import EsGerente, EsGerenteOSoloLectura
from .serializers import (
    UserRegisterSerializer,
    UserListSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    TrustedDeviceSerializer,
)

from .models import TrustedDevice

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


@extend_schema(
    tags=['Auth'],
    summary='Solicitar recuperación de contraseña',
    description='Envía un correo con un enlace para restablecer la contraseña si el email existe.',
)
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        user = User.objects.filter(email=email).first()
        if user:
            # Generar token y uidb64
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Construir enlace al frontend
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173/reset-password')
            reset_link = f"{frontend_url}?uidb64={uidb64}&token={token}"
            
            # Enviar correo asíncrono
            send_password_reset_email(user, reset_link)

            # Auditar la solicitud
            create_audit_log(
                user=user,
                action=AuditLog.Action.PASSWORD_RESET_REQUESTED,
                module=AuditLog.Module.AUTH,
                description='Solicitud de recuperación de contraseña enviada.',
                request=request,
            )

        return Response(
            {"detail": "Revisa tu bandeja de entrada o carpeta de spam."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Auth'],
    summary='Confirmar nueva contraseña',
    description='Recibe el uidb64, el token y la nueva contraseña para actualizarla. Retorna 400 si el token es inválido o expiró.',
)
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            # --- NUEVA LOGICA: Invalidar todas las sesiones existentes ---
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
                tokens = OutstandingToken.objects.filter(user=user)
                for t in tokens:
                    BlacklistedToken.objects.get_or_create(token=t)
            except Exception as e:
                # Si hay problemas con el log de tokens (ej. no está instalado correctamente), loggear y continuar
                print(f"Error blacklisting tokens: {e}")
            
            # Auditar el reseteo
            create_audit_log(
                user=user,
                action=AuditLog.Action.PASSWORD_CHANGED,
                module=AuditLog.Module.AUTH,
                description='Contraseña restablecida exitosamente mediante token de recuperación.',
                request=request,
            )

            return Response(
                {"detail": "La contraseña ha sido restablecida correctamente."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "El enlace de recuperación no es válido o ha expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )

@extend_schema(tags=['Dispositivos'])
class TrustedDeviceListView(generics.ListAPIView):
    serializer_class = TrustedDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedDevice.objects.filter(user=self.request.user)

@extend_schema(tags=['Dispositivos'])
class TrustedDeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TrustedDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedDevice.objects.filter(user=self.request.user)

class UnrecognizedDeviceView(APIView):
    """
    Vista llamada cuando el usuario hace clic en 'No reconozco este dispositivo'.
    Espera un token temporal para autenticar la acción sin pedir contraseña (el mismo del reset).
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        device_id = request.data.get('device_id')
        
        if not uidb64 or not token:
            return Response({"detail": "Faltan credenciales."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            
        if user is not None and default_token_generator.check_token(user, token):
            # 1. Invalidar todas las sesiones
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
                tokens = OutstandingToken.objects.filter(user=user)
                for t in tokens:
                    BlacklistedToken.objects.get_or_create(token=t)
            except Exception as e:
                pass
                
            # 2. Marcar el dispositivo como NO confiable si se provee
            if device_id:
                device = TrustedDevice.objects.filter(user=user, device_id=device_id).first()
                if device:
                    device.is_trusted = False
                    device.save(update_fields=['is_trusted'])
                    
            create_audit_log(
                user=user,
                action=AuditLog.Action.USER_UPDATED,
                module=AuditLog.Module.AUTH,
                description=f'Dispositivo no reconocido reportado ({device_id}). Sesiones cerradas.',
                request=request,
            )

            return Response(
                {"detail": "Sesiones cerradas. Por favor, restablece tu contraseña."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "El enlace no es válido o ha expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )
