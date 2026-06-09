import threading
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import NotificationLog

class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, text_content, recipient_list, notification_log_id):
        self.subject = subject
        self.html_content = html_content
        self.text_content = text_content
        self.recipient_list = recipient_list
        self.notification_log_id = notification_log_id
        threading.Thread.__init__(self)

    def run(self):
        try:
            msg = EmailMultiAlternatives(
                subject=self.subject,
                body=self.text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=self.recipient_list
            )
            msg.attach_alternative(self.html_content, "text/html")
            msg.send()
            
            # Update log as SENT
            NotificationLog.objects.filter(id=self.notification_log_id).update(status=NotificationLog.Status.SENT)
        except Exception as e:
            # Update log as FAILED
            NotificationLog.objects.filter(id=self.notification_log_id).update(
                status=NotificationLog.Status.FAILED,
                error_message=str(e)
            )

def send_async_email(user, subject, template_name, context, notification_type, recipient_email=None):
    """
    Sends an email asynchronously using threading to avoid blocking the HTTP request.
    Creates a NotificationLog entry before sending to track the status.
    """
    # Si no se provee recipient_email, se usa el del user
    final_email = recipient_email if recipient_email else (user.email if user else '')

    # 1. ALWAYS create the log entry as PENDING
    log_entry = NotificationLog.objects.create(
        user=user,
        recipient_email=final_email,
        notification_type=notification_type,
        subject=subject,
        status=NotificationLog.Status.PENDING if final_email else NotificationLog.Status.FAILED,
        error_message="No se configuró un correo de destino." if not final_email else ""
    )

    if not final_email:
        return # No hay a quién enviar, pero ya se guardó en BD para el Frontend

    # 2. Render templates
    html_content = render_to_string(f'emails/{template_name}.html', context)
    text_content = render_to_string(f'emails/{template_name}.txt', context)

    # 3. Start the thread
    EmailThread(
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        recipient_list=[final_email],
        notification_log_id=log_entry.id
    ).start()

def send_registration_email(user):
    subject = '¡Bienvenido a Cafequipe!'
    frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if hasattr(settings, 'CORS_ALLOWED_ORIGINS') else 'http://localhost:5173'
    context = {
        'user': user,
        'login_url': f"{frontend_url}/login"
    }
    send_async_email(
        user=user,
        subject=subject,
        template_name='registration_welcome',
        context=context,
        notification_type=NotificationLog.NotificationType.REGISTRATION
    )

def send_login_alert_email(user, ip_address, user_agent):
    subject = 'Alerta de Inicio de Sesión - Cafequipe'
    frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if hasattr(settings, 'CORS_ALLOWED_ORIGINS') else 'http://localhost:5173'
    context = {
        'user': user,
        'ip_address': ip_address,
        'device_info': user_agent,
        'reset_url': f"{frontend_url}/forgot-password"
    }
    send_async_email(
        user=user,
        subject=subject,
        template_name='login_alert',
        context=context,
        notification_type=NotificationLog.NotificationType.LOGIN_ALERT
    )

def send_password_reset_email(user, reset_link):
    subject = 'Recuperación de contraseña - Cafequipe'
    context = {
        'user': user,
        'reset_url': reset_link
    }
    send_async_email(
        user=user,
        subject=subject,
        template_name='password_reset',
        context=context,
        notification_type=NotificationLog.NotificationType.PASSWORD_RESET
    )

def _get_admin_email():
    from .models import SystemEmailConfiguration
    config = SystemEmailConfiguration.load()
    return config.admin_email if config.notify_alerts else None

def send_supply_request_email(ticket):
    admin_email = _get_admin_email()
    subject = f'Solicitud de Insumos - Orden {ticket.orden_produccion.codigo_lote}'
    context = {'ticket': ticket}
    send_async_email(
        user=None, subject=subject, template_name='supply_request', context=context,
        notification_type=NotificationLog.NotificationType.SUPPLY_REQUEST, recipient_email=admin_email
    )

def send_supply_delivered_email(ticket):
    responsable = ticket.orden_produccion.responsable
    subject = f'Insumos Entregados - Orden {ticket.orden_produccion.codigo_lote}'
    context = {'ticket': ticket}
    send_async_email(
        user=responsable, subject=subject, template_name='supply_delivered', context=context,
        notification_type=NotificationLog.NotificationType.SUPPLY_DELIVERED, recipient_email=responsable.email
    )

def send_qc_rejected_email(control_calidad):
    responsable = control_calidad.orden_produccion.responsable
    subject = f'Control de Calidad RECHAZADO - Orden {control_calidad.orden_produccion.codigo_lote}'
    context = {'control_calidad': control_calidad}
    send_async_email(
        user=responsable, subject=subject, template_name='qc_rejected', context=context,
        notification_type=NotificationLog.NotificationType.QC_REJECTED, recipient_email=responsable.email
    )

def send_finished_product_email(orden):
    admin_email = _get_admin_email()
    subject = f'Recepción de Producto Terminado - Orden {orden.codigo_lote}'
    context = {'orden': orden}
    send_async_email(
        user=None, subject=subject, template_name='finished_product', context=context,
        notification_type=NotificationLog.NotificationType.FINISHED_PRODUCT, recipient_email=admin_email
    )

def send_out_of_stock_email(stock):
    admin_email = _get_admin_email()
    subject = f'Stock Agotado - {stock.producto.nombre}'
    context = {'stock': stock}
    send_async_email(
        user=None, subject=subject, template_name='out_of_stock', context=context,
        notification_type=NotificationLog.NotificationType.OUT_OF_STOCK, recipient_email=admin_email
    )

def send_product_expired_email(stock):
    admin_email = _get_admin_email()
    subject = f'Producto Vencido - {stock.producto.nombre} Lote {stock.codigo_lote}'
    context = {'stock': stock}
    send_async_email(
        user=None, subject=subject, template_name='product_expired', context=context,
        notification_type=NotificationLog.NotificationType.PRODUCT_EXPIRED, recipient_email=admin_email
    )