from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.inventory.models import StockBodega
from apps.notifications.services import send_product_expired_email
from apps.notifications.models import NotificationLog

class Command(BaseCommand):
    help = 'Revisa los productos en stock que han vencido y emite una notificación.'

    def handle(self, *args, **options):
        now = timezone.now().date()
        
        # Buscar productos que vencen hoy o ya vencieron, y que tengan stock > 0
        expired_stocks = StockBodega.objects.filter(
            fecha_vencimiento__lte=now,
            stock_disponible__gt=0
        )
        
        notified_count = 0
        for stock in expired_stocks:
            # Evitar enviar notificaciones duplicadas para el mismo lote
            # Verificamos si ya existe una notificacion PRODUCT_EXPIRED con este lote en el subject
            already_notified = NotificationLog.objects.filter(
                notification_type=NotificationLog.NotificationType.PRODUCT_EXPIRED,
                subject__icontains=stock.codigo_lote
            ).exists()
            
            if not already_notified:
                send_product_expired_email(stock)
                notified_count += 1
                self.stdout.write(self.style.SUCCESS(f'Notificación enviada: Lote {stock.codigo_lote} vencido.'))

        self.stdout.write(self.style.SUCCESS(f'Finalizado. {notified_count} productos vencidos notificados.'))
