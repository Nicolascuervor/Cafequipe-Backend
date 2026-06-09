from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import StockBodega
from apps.notifications.services import send_out_of_stock_email

@receiver(pre_save, sender=StockBodega)
def track_old_stock(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = StockBodega.objects.get(pk=instance.pk)
            instance._old_stock = old_instance.stock_disponible
        except StockBodega.DoesNotExist:
            pass

@receiver(post_save, sender=StockBodega)
def trigger_stock_emails(sender, instance, created, **kwargs):
    if created and instance.stock_disponible <= 0:
        send_out_of_stock_email(instance)
    elif not created and hasattr(instance, '_old_stock'):
        if instance._old_stock > 0 and instance.stock_disponible <= 0:
            send_out_of_stock_email(instance)
