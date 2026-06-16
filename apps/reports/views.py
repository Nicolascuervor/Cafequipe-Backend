from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import HttpResponse
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from decimal import Decimal
from datetime import timedelta

from apps.inventory.models import Producto, StockBodega
from apps.production.models import OrdenProduccion, EstadoOrden
from apps.movements.models import Movimiento, SolicitudInterna

class ABCAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Agrupar productos y calcular el valor total del inventario disponible
        productos = Producto.objects.annotate(
            total_stock=Coalesce(Sum('existencias_bodega__stock_disponible'), Decimal('0.0000'), output_field=DecimalField())
        ).annotate(
            total_value=ExpressionWrapper(F('total_stock') * F('costo_unitario'), output_field=DecimalField())
        ).filter(total_value__gt=0).order_by('-total_value')

        total_inventory_value = sum(p.total_value for p in productos)
        if total_inventory_value == 0:
            return Response({"total_inventory_value": 0, "clasificacion": {"A": [], "B": [], "C": []}})

        cumulative_value = Decimal('0.0')
        abc_data = {"A": [], "B": [], "C": []}

        for p in productos:
            cumulative_value += p.total_value
            percentage = cumulative_value / total_inventory_value
            
            item_data = {
                "id": p.id,
                "nombre": p.nombre,
                "unidad": p.unidad_medida,
                "stock_total": p.total_stock,
                "costo_unitario": p.costo_unitario,
                "valor_total": p.total_value,
                "porcentaje_acumulado": round(percentage * 100, 2)
            }

            if percentage <= Decimal('0.80'):
                item_data["categoria_abc"] = "A"
                abc_data["A"].append(item_data)
            elif percentage <= Decimal('0.95'):
                item_data["categoria_abc"] = "B"
                abc_data["B"].append(item_data)
            else:
                item_data["categoria_abc"] = "C"
                abc_data["C"].append(item_data)

        return Response({
            "total_inventory_value": total_inventory_value,
            "clasificacion": abc_data
        })


class InventoryKPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hoy = timezone.now().date()
        
        # 1. Pérdida por producto vencido
        lotes_vencidos = StockBodega.objects.filter(
            fecha_vencimiento__lt=hoy, 
            stock_disponible__gt=0
        ).select_related('producto')
        
        perdida_vencidos = Decimal('0.0')
        detalles_vencidos = []
        for lote in lotes_vencidos:
            costo_perdida = lote.stock_disponible * lote.producto.costo_unitario
            perdida_vencidos += costo_perdida
            detalles_vencidos.append({
                "producto": lote.producto.nombre,
                "lote": lote.codigo_lote,
                "cantidad": lote.stock_disponible,
                "costo_perdida": costo_perdida,
                "fecha_vencimiento": lote.fecha_vencimiento
            })
            
        # 2. Precisión del Inventario (Placeholder, falta módulo tomas físicas)
        precision_inventario = 100.0
        
        return Response({
            "kpi_perdida_vencidos": {
                "total_perdida_dinero": perdida_vencidos,
                "detalles": detalles_vencidos
            },
            "kpi_precision_inventario": {
                "valor": precision_inventario,
                "nota": "Se asume 100% al no contar con un submódulo de tomas físicas recurrentes."
            }
        })


class ProductionKPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ordenes_completadas = OrdenProduccion.objects.filter(
            estado=EstadoOrden.COMPLETADA,
            cantidad_obtenida__isnull=False
        )
        
        total_ordenes = ordenes_completadas.count()
        if total_ordenes == 0:
            return Response({"detail": "No hay órdenes completadas con datos para calcular KPIs."})
            
        sum_rendimiento = Decimal('0.0')
        sum_desperdicio = Decimal('0.0')
        ordenes_con_faltantes = 0
        
        detalles = []
        
        for orden in ordenes_completadas:
            esperado = orden.cantidad_esperada
            obtenido = orden.cantidad_obtenida
            
            # Rendimiento = (obtenido / esperado) * 100
            rendimiento = (obtenido / esperado) * 100 if esperado > 0 else Decimal('0.0')
            
            # Merma / Desperdicio (Si se obtuvo menos de lo esperado)
            merma = Decimal('0.0')
            if obtenido < esperado:
                merma = ((esperado - obtenido) / esperado) * 100
                ordenes_con_faltantes += 1
                
            sum_rendimiento += rendimiento
            sum_desperdicio += merma
            
            detalles.append({
                "lote": orden.codigo_lote,
                "producto": orden.receta.producto_terminado.nombre,
                "esperado": esperado,
                "obtenido": obtenido,
                "rendimiento_porcentaje": round(rendimiento, 2),
                "merma_porcentaje": round(merma, 2)
            })
            
        rendimiento_promedio = sum_rendimiento / total_ordenes
        desperdicio_promedio = sum_desperdicio / total_ordenes
        tasa_faltantes = (Decimal(ordenes_con_faltantes) / Decimal(total_ordenes)) * 100
        
        return Response({
            "kpi_produccion": {
                "total_ordenes_analizadas": total_ordenes,
                "rendimiento_promedio": round(rendimiento_promedio, 2),
                "desperdicio_promedio": round(desperdicio_promedio, 2),
                "tasa_ordenes_con_faltantes": round(tasa_faltantes, 2),
                "detalles_lotes": detalles
            }
        })


class ExportExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte_inventario.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventario"
        ws.append(["Producto", "Bodega", "Stock Disponible", "Costo Unitario", "Valor Total", "Lote", "Vencimiento"])
        
        stocks = StockBodega.objects.select_related('producto', 'bodega').all()
        for stock in stocks:
            valor = stock.stock_disponible * stock.producto.costo_unitario
            ws.append([
                stock.producto.nombre,
                stock.bodega.nombre,
                float(stock.stock_disponible),
                float(stock.producto.costo_unitario),
                float(valor),
                stock.codigo_lote,
                str(stock.fecha_vencimiento) if stock.fecha_vencimiento else ""
            ])
            
        wb.save(response)
        return response

class ExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_inventario.pdf"'
        
        p = canvas.Canvas(response, pagesize=letter)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 750, "Reporte de Inventario")
        
        p.setFont("Helvetica", 10)
        y = 720
        stocks = StockBodega.objects.select_related('producto', 'bodega').all()
        
        for stock in stocks:
            texto = f"{stock.producto.nombre} | Bodega: {stock.bodega.nombre} | Stock: {stock.stock_disponible}"
            p.drawString(50, y, texto)
            y -= 20
            if y < 50:
                p.showPage()
                y = 750
                
        p.showPage()
        p.save()
        return response

class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. KPIs
        total_skus = Producto.objects.count()
        total_stock = StockBodega.objects.aggregate(total=Sum('stock_disponible'))['total'] or Decimal('0.0')
        
        alertas = StockBodega.objects.annotate(
            proyectado=F('stock_disponible') + F('pedidos_abiertos') - F('ordenes_atrasadas')
        ).filter(Q(stock_disponible__lte=F('producto__inventario_seguridad')) | Q(proyectado__lte=F('producto__punto_reorden'))).count()
        
        solicitudes_pendientes = SolicitudInterna.objects.filter(estado='PENDIENTE').count()

        # 2. Flujo 7 días
        hoy = timezone.now().date()
        flujo_data = []
        dias_espanol = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        
        for i in range(6, -1, -1):
            fecha_dia = hoy - timedelta(days=i)
            movs_dia = Movimiento.objects.filter(created_at__date=fecha_dia)
            entradas = movs_dia.filter(tipo='ENTRADA').aggregate(t=Sum('cantidad'))['t'] or Decimal('0.0')
            salidas = movs_dia.filter(tipo='SALIDA').aggregate(t=Sum('cantidad'))['t'] or Decimal('0.0')
            
            flujo_data.append({
                "d": dias_espanol[fecha_dia.weekday()],
                "entradas": float(entradas),
                "salidas": float(salidas)
            })

        # 3. ABC Data
        abc_counts = Producto.objects.values('clasificacion').annotate(c=Count('id'))
        abc_dict = {item['clasificacion']: item['c'] for item in abc_counts}
        abc_data = [
            {"name": "Clase A", "value": abc_dict.get('A', 0), "color": "var(--caramel)"},
            {"name": "Clase B", "value": abc_dict.get('B', 0), "color": "var(--coffee-medium)"},
            {"name": "Clase C", "value": abc_dict.get('C', 0), "color": "var(--beige)"},
        ]

        # 4. Movimientos recientes
        movimientos_qs = Movimiento.objects.select_related('producto', 'bodega', 'usuario').order_by('-created_at')[:7]
        movimientos_recientes = []
        for m in movimientos_qs:
            movimientos_recientes.append({
                "id": str(m.id)[:8].upper(),
                "type": m.get_tipo_display(),
                "product": m.producto.nombre,
                "warehouse": m.bodega.nombre,
                "qty": float(m.cantidad),
                "unit": m.producto.get_unidad_medida_display(),
                "user": m.usuario.get_full_name() or m.usuario.username
            })

        return Response({
            "kpis": {
                "skus": total_skus,
                "stock": float(total_stock),
                "alertas": alertas,
                "solicitudes_pendientes": solicitudes_pendientes
            },
            "flujo": flujo_data,
            "abc": abc_data,
            "movimientos": movimientos_recientes
        })
