# apps/users/models.py
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import FileExtensionValidator
from .validators import validate_file_size


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'GER')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('correo electrónico', unique=True)

    class Rol(models.TextChoices):
        GERENTE         = 'GER', 'Gerente'
        JEFE_BODEGA     = 'JBD', 'Jefe de Bodega'
        JEFE_PRODUCCION = 'JPR', 'Jefe de Producción'
        OPERARIO        = 'OPR', 'Operario'

    rol = models.CharField(
        max_length=3,
        choices=Rol.choices,
        default=Rol.OPERARIO
    )
    telefono = models.CharField(max_length=20, blank=True)
    foto_perfil = models.ImageField(
        'foto de perfil',
        upload_to='users/profiles/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_file_size,
        ],
        help_text='Sube una imagen (JPG, PNG o WEBP). Máximo 5MB.'
    )
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"

    @property
    def es_gerente(self):
        return self.rol == self.Rol.GERENTE

    @property
    def es_jefe_bodega(self):
        return self.rol == self.Rol.JEFE_BODEGA

    @property
    def es_jefe_operario(self):
        return self.rol == self.Rol.OPERARIO

    @property
    def puede_aprobar_traslados(self):
        return self.rol in [self.Rol.JEFE_BODEGA, self.Rol.GERENTE]