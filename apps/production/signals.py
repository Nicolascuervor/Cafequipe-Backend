from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import TicketInsumo, DetalleTicketInsumo, EstadoTicket, OrdenProduccion, ControlCalidadLote, EstadoOrden
from apps.inventory.services import sumar_ordenes_atrasadas, restar_ordenes_atrasadas
from apps.notifications.services import (
    send_supply_request_email,
    send_supply_delivered_email,
    send_qc_rejected_email,
    send_finished_product_email
)



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

        if old_estado != new_estado:
            if new_estado == EstadoTicket.SOLICITADO:
                send_supply_request_email(instance)
            elif new_estado == EstadoTicket.ENTREGADO:
                send_supply_delivered_email(instance)

    elif created and instance.estado == EstadoTicket.SOLICITADO:
        send_supply_request_email(instance)


@receiver(pre_save, sender=OrdenProduccion)
def track_old_orden_estado(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = OrdenProduccion.objects.get(pk=instance.pk)
            instance._old_estado = old_instance.estado
        except OrdenProduccion.DoesNotExist:
            pass

@receiver(post_save, sender=OrdenProduccion)
def trigger_orden_emails(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_old_estado'):
        if instance._old_estado != instance.estado and instance.estado == EstadoOrden.COMPLETADA:
            send_finished_product_email(instance)


@receiver(pre_save, sender=ControlCalidadLote)
def track_old_qc_estado(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = ControlCalidadLote.objects.get(pk=instance.pk)
            instance._old_aprobado = old_instance.aprobado_final
        except ControlCalidadLote.DoesNotExist:
            pass

@receiver(post_save, sender=ControlCalidadLote)
def trigger_qc_emails(sender, instance, created, **kwargs):
    if created and not instance.aprobado_final:
        send_qc_rejected_email(instance)
    elif not created and hasattr(instance, '_old_aprobado'):
        if instance._old_aprobado and not instance.aprobado_final:
            send_qc_rejected_email(instance)
