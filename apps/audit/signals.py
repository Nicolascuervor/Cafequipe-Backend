# apps/audit/signals.py

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AuditLog
from .services import create_audit_log

User = get_user_model()


#Usuarios
@receiver(post_save, sender=User)
def audit_user_save(sender, instance, created, **kwargs):
    if created:
        create_audit_log(
            user=instance,
            action=AuditLog.Action.USER_CREATED,
            module=AuditLog.Module.USERS,
            description=f'Usuario {instance.email} creado con rol {instance.get_rol_display()}.',
        )
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields and set(update_fields) == {'last_login'}:
            return
        create_audit_log(
            user=instance,
            action=AuditLog.Action.USER_UPDATED,
            module=AuditLog.Module.USERS,
            description=f'Datos del usuario {instance.email} actualizados.',
        )
