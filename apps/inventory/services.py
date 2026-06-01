from decimal import Decimal
from django.db import transaction
from apps.inventory.models import StockBodega

@transaction.atomic
def sumar_ordenes_atrasadas(producto, cantidad):
    if cantidad <= 0: return
    cantidad_restante = Decimal(str(cantidad))

    stocks = list(StockBodega.objects.filter(
        producto=producto,
        stock_disponible__gt=0
    ).order_by('-stock_disponible'))
    
    for stock in stocks:
        if cantidad_restante <= 0:
            break
        espacio_reserva = stock.stock_disponible - stock.ordenes_atrasadas
        if espacio_reserva > 0:
            reserva = min(espacio_reserva, cantidad_restante)
            stock.ordenes_atrasadas += reserva
            stock.save(update_fields=['ordenes_atrasadas'])
            cantidad_restante -= reserva

    if cantidad_restante > 0:
        stock = StockBodega.objects.filter(producto=producto).first()
        if stock:
            stock.ordenes_atrasadas += cantidad_restante
            stock.save(update_fields=['ordenes_atrasadas'])

@transaction.atomic
def restar_ordenes_atrasadas(producto, cantidad):
    if cantidad <= 0: return
    cantidad_restante = Decimal(str(cantidad))

    stocks = list(StockBodega.objects.filter(
        producto=producto,
        ordenes_atrasadas__gt=0
    ).order_by('-ordenes_atrasadas'))
    
    for stock in stocks:
        if cantidad_restante <= 0:
            break
        liberacion = min(stock.ordenes_atrasadas, cantidad_restante)
        stock.ordenes_atrasadas -= liberacion
        stock.save(update_fields=['ordenes_atrasadas'])
        cantidad_restante -= liberacion
