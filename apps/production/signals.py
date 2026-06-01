from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import TicketInsumo, DetalleTicketInsumo, EstadoTicket
from apps.inventory.services import sumar_ordenes_atrasadas, restar_ordenes_atrasadas



@receiver(pre_save, sender=DetalleTicketInsumo)
def track_old_cantidad(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = DetalleTicketInsumo.objects.get(pk=instance.pk)
            instance._old_cantidad_solicitada = old_instance.cantidad_solicitada
        except DetalleTicketInsumo.DoesNotExist:
            pass

@receiver(post_save, sender=DetalleTicketInsumo)
def update_reserva_on_edit(sender, instance, created, **kwargs):
    if instance.ticket.estado == EstadoTicket.SOLICITADO:
        if created:
            sumar_ordenes_atrasadas(instance.producto, instance.cantidad_solicitada)
        elif hasattr(instance, '_old_cantidad_solicitada'):
            diff = instance.cantidad_solicitada - instance._old_cantidad_solicitada
            if diff > 0:
                sumar_ordenes_atrasadas(instance.producto, diff)
            elif diff < 0:
                restar_ordenes_atrasadas(instance.producto, abs(diff))


@receiver(pre_save, sender=TicketInsumo)
def track_old_ticket_estado(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = TicketInsumo.objects.get(pk=instance.pk)
            instance._old_estado = old_instance.estado
        except TicketInsumo.DoesNotExist:
            pass

@receiver(post_save, sender=TicketInsumo)
def update_reserva_on_ticket_estado(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_old_estado'):
        old_estado = instance._old_estado
        new_estado = instance.estado

        if old_estado == EstadoTicket.SOLICITADO and new_estado in [EstadoTicket.RECHAZADO, EstadoTicket.ENTREGADO]:
            for detalle in instance.detalles.all():
                restar_ordenes_atrasadas(detalle.producto, detalle.cantidad_solicitada)

        elif old_estado == EstadoTicket.RECHAZADO and new_estado == EstadoTicket.SOLICITADO:
            for detalle in instance.detalles.all():
                sumar_ordenes_atrasadas(detalle.producto, detalle.cantidad_solicitada)
