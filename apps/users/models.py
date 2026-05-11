# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    email = models.EmailField(unique=True)

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
    updated_at = models.DateTimeField(auto_now=True)

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