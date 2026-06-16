import os
import django
import random
from datetime import timedelta
from decimal import Decimal

# Configurar el entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from apps.users.models import User
from apps.inventory.models import Producto, Bodega
from apps.movements.models import Movimiento, TipoMovimiento, SolicitudInterna, EstadoSolicitud

def run():
    print("Iniciando la simulación de historial para el Dashboard...")
    
    usuario = User.objects.first()
    productos = list(Producto.objects.all())
    bodegas = list(Bodega.objects.all())

    if not usuario or not productos or not bodegas:
        print("Error: Necesitas al menos un usuario, un producto y una bodega creados.")
        return

    hoy = timezone.now()
    movimientos_creados = 0
    solicitudes_creadas = 0

    # 1. Simular Movimientos en los últimos 14 días
    print("Generando flujos de inventario (Entradas/Salidas)...")
    tipos = [TipoMovimiento.ENTRADA, TipoMovimiento.SALIDA, TipoMovimiento.TRASLADO]
    
    for dias_atras in range(14, -1, -1):
        fecha_simulada = hoy - timedelta(days=dias_atras)
        
        # Generar entre 4 y 12 movimientos diarios
        cantidad_movimientos_dia = random.randint(4, 12)
        
        for _ in range(cantidad_movimientos_dia):
            prod = random.choice(productos)
            bodega = random.choice(bodegas)
            tipo = random.choice(tipos)
            cantidad = Decimal(random.randint(10, 500))
            
            # Crear el movimiento
            mov = Movimiento.objects.create(
                tipo=tipo,
                producto=prod,
                bodega=bodega,
                cantidad=cantidad,
                usuario=usuario
            )
            # Truco para sobreescribir 'auto_now_add' de AuditModel
            Movimiento.objects.filter(id=mov.id).update(created_at=fecha_simulada)
            movimientos_creados += 1

    # 2. Simular Solicitudes Pendientes recientes
    print("Generando solicitudes internas pendientes...")
    cantidad_solicitudes = random.randint(3, 8)
    for _ in range(cantidad_solicitudes):
        fecha_simulada = hoy - timedelta(hours=random.randint(1, 48))
        sol = SolicitudInterna.objects.create(
            solicitante=usuario,
            estado=EstadoSolicitud.PENDIENTE,
            motivo="Solicitud generada por simulación automática"
        )
        SolicitudInterna.objects.filter(id=sol.id).update(created_at=fecha_simulada)
        solicitudes_creadas += 1

    print(f"\n¡Simulación completada con éxito!")
    print(f"-> Se generaron {movimientos_creados} movimientos históricos.")
    print(f"-> Se generaron {solicitudes_creadas} solicitudes pendientes.")
    print("Ya puedes recargar tu Dashboard en React para ver las gráficas y tablas llenas de vida.")

if __name__ == '__main__':
    run()
