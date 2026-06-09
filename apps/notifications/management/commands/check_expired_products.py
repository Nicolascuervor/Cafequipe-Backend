from django.core.management.base import BaseCommand
from apps.inventory.models import StockBodega
from apps.notifications.models import NotificationLog
from apps.notifications.services import send_product_expired_email
from django.utils import timezone

class Command(BaseCommand):
    help = 'Revisa productos vencidos y envía alertas'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        vencidos = StockBodega.objects.filter(fecha_vencimiento__lte=today, stock_disponible__gt=0)
        count = 0
        
        for stock in vencidos:
            subject = f'Producto Vencido - {stock.producto.nombre} Lote {stock.codigo_lote}'
            already_sent = NotificationLog.objects.filter(
                notification_type=NotificationLog.NotificationType.PRODUCT_EXPIRED,
                subject=subject,
                created_at__date=today
            ).exists()

            if not already_sent:
                send_product_expired_email(stock)
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Proceso completado. {count} correos enviados por productos vencidos.'))
