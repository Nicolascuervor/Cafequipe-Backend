# apps/users/views.py

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from .permissions import EsGerente, EsGerenteOSoloLectura
from .serializers import (
    UserRegisterSerializer,
    UserListSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()


@extend_schema(
    tags=['Auth'],
    summary='Registrar usuario nuevo',
    description='Solo el Gerente puede crear cuentas. '
                'El username se asigna automáticamente igual al email.',
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
    permission_classes = [IsAuthenticated, EsGerenteOSoloLectura]
   
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_name', 'rol']
    filterset_fields = ['rol', 'is_active']


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
   
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, EsGerenteOSoloLectura]
    http_method_names = ['get', 'patch', 'delete']

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
