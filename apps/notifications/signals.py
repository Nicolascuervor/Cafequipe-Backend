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


from django.utils import timezone
from apps.users.models import TrustedDevice
import hashlib
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

@receiver(user_logged_in)
def send_login_alert(sender, request, user, **kwargs):
    """
    Escucha el inicio de sesión exitoso y envía una alerta de seguridad al usuario
    solo si el dispositivo no está en la lista blanca (confiable).
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
        
        # Intentar obtener device_id del request.data (solo si DRF Request)
        request_data = getattr(request, 'data', {})
        device_id = request_data.get('device_id')
        device_name = request_data.get('device_name', user_agent[:250])
        
        # Si el frontend no mandó device_id, generamos uno basado en User-Agent
        if not device_id:
            raw_id = f"fallback-{user_agent}"
            device_id = hashlib.sha256(raw_id.encode()).hexdigest()

        device, created = TrustedDevice.objects.get_or_create(
            user=user,
            device_id=device_id,
            defaults={
                'device_name': device_name,
                'ip_address': ip_address,
                'is_trusted': True  # Por requerimiento, se asume confiable al primer uso exitoso
            }
        )

        if not created:
            device.last_login = timezone.now()
            device.ip_address = ip_address
            device.save(update_fields=['last_login', 'ip_address'])
            
            # Si el dispositivo ya es confiable, se omite el envío del correo
            if device.is_trusted:
                return

        # Generar token para reporte de dispositivo no reconocido
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Si el dispositivo es nuevo o is_trusted=False, enviamos la alerta
        send_login_alert_email(
            user=user, 
            ip_address=ip_address, 
            user_agent=user_agent, 
            uidb64=uidb64, 
            token=token, 
            device_id=device_id
        )
