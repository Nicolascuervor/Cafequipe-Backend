import datetime
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.inventory.models import Bodega, Producto, SubCategoria, StockBodega, CategoriaPrincipal, UnidadMedida, ClasificacionABC
from apps.production.models import Receta, OrdenProduccion, TicketInsumo, DetalleTicketInsumo, EstadoTicket, EstadoOrden, ControlCalidadLote
from apps.notifications.models import SystemEmailConfiguration

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera datos simulados y dispara eventos para probar el envío de todos los correos.'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Iniciando Simulación de Correos ---")

        # 1. Configuración de Correo
        config = SystemEmailConfiguration.load()
        config.admin_email = 'nicocu1127+1@gmail.com'
        config.notify_alerts = True
        config.save()
        self.stdout.write("1. Configuración de email seteada (nicocu1127+1@gmail.com)")

        # 2. Usuarios
        jefe_bodega, _ = User.objects.get_or_create(email='nicocu1127+1@gmail.com', defaults={'first_name': 'Operario', 'last_name': 'Bodega', 'rol': 'JBD'})
        jefe_prod, _ = User.objects.get_or_create(email='allebasia20+6@gmail.com', defaults={'first_name': 'Jefe', 'last_name': 'Produccion', 'rol': 'JPR'})
        
        # 3. Bodega y Categorías
        bodega, _ = Bodega.objects.get_or_create(nombre='Bodega Central Test', defaults={'ubicacion': 'Sede Principal', 'administrador': jefe_bodega})
        subcat, _ = SubCategoria.objects.get_or_create(nombre='Insumos Básicos Test')
        
        # Productos
        prod_insumo, _ = Producto.objects.get_or_create(nombre='Insumo de Prueba', defaults={'categoria_principal': CategoriaPrincipal.INSUMO, 'sub_categoria': subcat})
        prod_terminado, _ = Producto.objects.get_or_create(nombre='Café Empacado Test', defaults={'categoria_principal': CategoriaPrincipal.PRODUCTO, 'sub_categoria': subcat})

        # 4. EVENTO: Stock Agotado
        self.stdout.write("-> Disparando: Stock Agotado")
        uid = str(uuid.uuid4())[:6]
        stock_agotado = StockBodega.objects.create(
            bodega=bodega,
            producto=prod_insumo,
            stock_disponible=0, # Esto dispara la señal de Stock Agotado
            codigo_lote=f'LOTE-AGOTADO-{uid}'
        )

        # 5. EVENTO: Producto Vencido
        self.stdout.write("-> Preparando: Producto Vencido")
        stock_vencido = StockBodega.objects.create(
            bodega=bodega,
            producto=prod_insumo,
            stock_disponible=50,
            codigo_lote=f'LOTE-VENCIDO-{uid}',
            fecha_vencimiento=timezone.now().date() - datetime.timedelta(days=5) # Vencido hace 5 días
        )
        # Llamamos explícitamente a la lógica del comando de vencimiento
        from apps.notifications.services import send_product_expired_email
        send_product_expired_email(stock_vencido)

        # 6. Preparación para Producción
        receta, _ = Receta.objects.get_or_create(producto_terminado=prod_terminado, defaults={'rendimiento_base': 100})
        
        orden = OrdenProduccion.objects.create(
            receta=receta,
            cantidad_esperada=100,
            responsable=jefe_prod,
            bodega_destino=bodega
        )

        # 7. EVENTO: Solicitud de Insumos
        self.stdout.write("-> Disparando: Solicitud de Insumos")
        ticket = TicketInsumo.objects.create(orden_produccion=orden, estado=EstadoTicket.SOLICITADO)
        
        # 8. EVENTO: Insumos Entregados
        self.stdout.write("-> Disparando: Insumos Entregados")
        ticket.estado = EstadoTicket.ENTREGADO
        ticket.despachador = jefe_bodega
        ticket.save() # Esto dispara la señal

        # 9. EVENTO: Control de Calidad Rechazado
        self.stdout.write("-> Disparando: Control Calidad Rechazado")
        qc = ControlCalidadLote.objects.create(
            orden_produccion=orden,
            aprobado_final=False, # Esto dispara la señal de Rechazo
            observaciones='El lote de prueba no cumple con la humedad deseada.'
        )

        # 10. EVENTO: Recepción de Producto Terminado
        self.stdout.write("-> Disparando: Producto Terminado")
        orden.estado = EstadoOrden.COMPLETADA
        orden.save() # Esto dispara la señal

        self.stdout.write(self.style.SUCCESS('--- Simulación finalizada con éxito. Revisa tus logs o bandeja de entrada ---'))
