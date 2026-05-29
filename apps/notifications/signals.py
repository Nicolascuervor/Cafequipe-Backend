from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .services import send_registration_email, send_login_alert_email

User = get_user_model()

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Escucha la creación de un nuevo usuario y envía el correo de bienvenida.
    """
    if created and instance.email:
        # Aquí se dispara el hilo asíncrono
        send_registration_email(instance)


@receiver(user_logged_in)
def send_login_alert(sender, request, user, **kwargs):
    """
    Escucha el inicio de sesión exitoso y envía una alerta de seguridad al usuario.
    """
    if user and user.email:
        # Obtener IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
        # Obtener User Agent
        user_agent = request.META.get('HTTP_USER_AGENT', 'Desconocido')
        
        # Aquí se dispara el hilo asíncrono
        send_login_alert_email(user, ip_address, user_agent)
