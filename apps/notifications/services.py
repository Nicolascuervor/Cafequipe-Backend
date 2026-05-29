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

def send_async_email(user, subject, template_name, context, notification_type):
    """
    Sends an email asynchronously using threading to avoid blocking the HTTP request.
    Creates a NotificationLog entry before sending to track the status.
    """
    # 1. Create the log entry as PENDING
    log_entry = NotificationLog.objects.create(
        user=user,
        notification_type=notification_type,
        subject=subject,
        status=NotificationLog.Status.PENDING
    )

    # 2. Render templates
    html_content = render_to_string(f'emails/{template_name}.html', context)
    text_content = render_to_string(f'emails/{template_name}.txt', context)

    # 3. Start the thread
    EmailThread(
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        recipient_list=[user.email],
        notification_log_id=log_entry.id
    ).start()

def send_registration_email(user):
    subject = '¡Bienvenido a Cafequipe!'
    context = {
        'user': user,
        'frontend_url': settings.CORS_ALLOWED_ORIGINS[0] if hasattr(settings, 'CORS_ALLOWED_ORIGINS') else 'http://localhost:5173'
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
    context = {
        'user': user,
        'ip_address': ip_address,
        'user_agent': user_agent
    }
    send_async_email(
        user=user,
        subject=subject,
        template_name='login_alert',
        context=context,
        notification_type=NotificationLog.NotificationType.LOGIN_ALERT
    )
