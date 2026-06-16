import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, F, Q

from apps.inventory.models import Producto, Bodega, StockBodega
from apps.users.models import User
from apps.movements.models import SolicitudInterna, Movimiento, DetalleSolicitud

def get_inventory_stats():
    try:
        return json.dumps({
            'total_productos': Producto.objects.count(),
            'por_clasificacion': {
                'A': Producto.objects.filter(clasificacion='A').count(),
                'B': Producto.objects.filter(clasificacion='B').count(),
                'C': Producto.objects.filter(clasificacion='C').count(),
            },
            'por_categoria': {
                'Materia Prima': Producto.objects.filter(categoria_principal='MP').count(),
                'Insumo': Producto.objects.filter(categoria_principal='IN').count(),
                'Producto Terminado': Producto.objects.filter(categoria_principal='PR').count(),
            }
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_warehouse_stats():
    try:
        bodegas = Bodega.objects.all()
        result = []
        for b in bodegas:
            result.append({
                'nombre': b.nombre,
                'ubicacion': b.ubicacion,
                'catalogo_admitido': b.catalogo_admitido
            })
        return json.dumps({"bodegas": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

def search_products(keyword):
    try:
        productos = Producto.objects.filter(nombre__icontains=keyword)[:15]
        if productos.exists():
            resultados = []
            for p in productos:
                resultados.append({
                    'nombre': p.nombre,
                    'clasificacion': p.get_clasificacion_display(),
                    'categoria': p.get_categoria_principal_display(),
                    'unidad_medida': p.get_unidad_medida_display(),
                })
            return json.dumps({
                "mensaje": f"Se encontraron {productos.count()} productos que coinciden con '{keyword}'",
                "productos": resultados
            })
        return json.dumps({"error": f"No se encontraron productos que coincidan con '{keyword}'"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_users_stats():
    try:
        return json.dumps({
            'total_usuarios': User.objects.count(),
            'por_rol': {
                'Gerente': User.objects.filter(rol='GER').count(),
                'Jefe de Bodega': User.objects.filter(rol='JBD').count(),
                'Jefe de Producción': User.objects.filter(rol='JPR').count(),
                'Operario': User.objects.filter(rol='OPR').count(),
            }
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_zero_stock_products():
    try:
        stocks_zero = StockBodega.objects.filter(stock_disponible__lte=0)[:15]
        total_zero = StockBodega.objects.filter(stock_disponible__lte=0).count()
        if stocks_zero.exists():
            resultados = []
            for s in stocks_zero:
                resultados.append({
                    'producto': s.producto.nombre,
                    'bodega': s.bodega.nombre,
                    'lote': s.codigo_lote,
                    'stock_actual': str(s.stock_disponible)
                })
            return json.dumps({"mensaje": f"Existen {total_zero} registros con stock agotado.", "detalles": resultados})
        return json.dumps({"mensaje": "No hay stock agotado."})
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- NUEVAS SUPER-HERRAMIENTAS ---

def get_reorder_alerts():
    try:
        alerts = StockBodega.objects.annotate(
            proyectado=F('stock_disponible') + F('pedidos_abiertos') - F('ordenes_atrasadas')
        ).filter(proyectado__lte=F('producto__punto_reorden'))[:15]
        
        resultados = []
        for s in alerts:
            resultados.append({
                'producto': s.producto.nombre,
                'bodega': s.bodega.nombre,
                'stock_proyectado': str(s.proyectado),
                'punto_reorden': str(s.producto.punto_reorden)
            })
        if resultados:
            return json.dumps({"mensaje": f"Hay {alerts.count()} alertas de reorden.", "alertas": resultados})
        return json.dumps({"mensaje": "No hay productos bajo su punto de reorden."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_expiring_batches(dias=30):
    try:
        limite = timezone.now().date() + timedelta(days=int(dias))
        lotes = StockBodega.objects.filter(
            fecha_vencimiento__lte=limite, 
            fecha_vencimiento__gte=timezone.now().date(), 
            stock_disponible__gt=0
        ).order_by('fecha_vencimiento')[:15]
        
        resultados = []
        for l in lotes:
            resultados.append({
                'producto': l.producto.nombre,
                'lote': l.codigo_lote,
                'vencimiento': l.fecha_vencimiento.strftime('%Y-%m-%d'),
                'stock_actual': str(l.stock_disponible)
            })
        return json.dumps({"lotes_por_vencer": resultados})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_delayed_orders_stats():
    try:
        atrasadas = StockBodega.objects.filter(ordenes_atrasadas__gt=0)[:15]
        resultados = []
        for s in atrasadas:
            resultados.append({
                'producto': s.producto.nombre,
                'bodega': s.bodega.nombre,
                'cantidad_atrasada': str(s.ordenes_atrasadas)
            })
        return json.dumps({"ordenes_atrasadas": resultados})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_lot_location(lote_codigo):
    try:
        lotes = StockBodega.objects.filter(codigo_lote__icontains=lote_codigo)[:5]
        if lotes.exists():
            resultados = []
            for l in lotes:
                resultados.append({
                    'producto': l.producto.nombre,
                    'lote': l.codigo_lote,
                    'bodega': l.bodega.nombre,
                    'ubicacion': l.coordenada_fisica,
                    'stock': str(l.stock_disponible)
                })
            return json.dumps({"ubicaciones": resultados})
        return json.dumps({"mensaje": f"No se encontró el lote {lote_codigo} en ninguna bodega."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_projected_inventory(product_name):
    try:
        stocks = StockBodega.objects.filter(producto__nombre__icontains=product_name)[:10]
        if not stocks.exists():
            return json.dumps({"mensaje": f"No hay inventario registrado para {product_name}."})
            
        resultados = []
        for s in stocks:
            resultados.append({
                'producto': s.producto.nombre,
                'bodega': s.bodega.nombre,
                'disponible': str(s.stock_disponible),
                'proyectado': str(s.stock_proyectado)
            })
        return json.dumps({"inventario": resultados})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_requests_status(estado="PENDIENTE"):
    try:
        solicitudes = SolicitudInterna.objects.filter(estado__iexact=estado)[:10]
        total = SolicitudInterna.objects.filter(estado__iexact=estado).count()
        if solicitudes.exists():
            resultados = []
            for sol in solicitudes:
                resultados.append({
                    'id': str(sol.id),
                    'solicitante': sol.solicitante.get_full_name(),
                    'fecha': sol.created_at.strftime('%Y-%m-%d')
                })
            return json.dumps({
                "mensaje": f"Hay {total} solicitudes en estado {estado}.",
                "ejemplos": resultados
            })
        return json.dumps({"mensaje": f"No hay solicitudes en estado {estado}."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_recent_movements(bodega_nombre):
    try:
        limite = timezone.now() - timedelta(days=2)
        movs = Movimiento.objects.filter(bodega__nombre__icontains=bodega_nombre, created_at__gte=limite)
        entradas = movs.filter(tipo='ENTRADA').count()
        salidas = movs.filter(tipo='SALIDA').count()
        return json.dumps({
            "mensaje": f"Movimientos recientes (48h) en bodega '{bodega_nombre}':",
            "entradas": entradas,
            "salidas": salidas
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_inventory_analytics():
    try:
        bodega_referencias = StockBodega.objects.values('bodega__nombre').annotate(total_ref=Count('producto', distinct=True)).order_by('-total_ref').first()
        total_prods = Producto.objects.count()
        if total_prods == 0: return json.dumps({"mensaje": "No hay productos registrados."})
        mp = Producto.objects.filter(categoria_principal='MP').count()
        pr = Producto.objects.filter(categoria_principal='PR').count()
        ins = Producto.objects.filter(categoria_principal='IN').count()
        
        return json.dumps({
            "analiticas": {
                "bodega_mas_referencias": bodega_referencias,
                "porcentaje_materia_prima": f"{(mp/total_prods)*100:.1f}%",
                "porcentaje_producto_terminado": f"{(pr/total_prods)*100:.1f}%",
                "porcentaje_insumos": f"{(ins/total_prods)*100:.1f}%"
            }
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


AVAILABLE_TOOLS = {
    "get_inventory_stats": get_inventory_stats,
    "get_warehouse_stats": get_warehouse_stats,
    "search_products": search_products,
    "get_users_stats": get_users_stats,
    "get_zero_stock_products": get_zero_stock_products,
    "get_reorder_alerts": get_reorder_alerts,
    "get_expiring_batches": get_expiring_batches,
    "get_delayed_orders_stats": get_delayed_orders_stats,
    "get_lot_location": get_lot_location,
    "get_projected_inventory": get_projected_inventory,
    "get_requests_status": get_requests_status,
    "get_recent_movements": get_recent_movements,
    "get_inventory_analytics": get_inventory_analytics,
}

ASSISTANT_TOOLS = [
    {
        "type": "function",
        "function": {"name": "get_inventory_stats", "description": "Obtiene estadísticas generales del inventario (total productos, clases ABC).", "parameters": {"type": "object", "properties": {}}}
    },
    {
        "type": "function",
        "function": {"name": "get_warehouse_stats", "description": "Obtiene lista de bodegas activas y catálogos.", "parameters": {"type": "object", "properties": {}}}
    },
    {
        "type": "function",
        "function": {"name": "search_products", "description": "Busca productos por palabra clave (ej. 'Leche').", "parameters": {"type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]}}
    },
    {
        "type": "function",
        "function": {"name": "get_users_stats", "description": "Obtiene conteo de usuarios por rol.", "parameters": {"type": "object", "properties": {}}}
    },
    {
        "type": "function",
        "function": {"name": "get_zero_stock_products", "description": "Identifica productos con stock disponible 0 o agotado.", "parameters": {"type": "object", "properties": {}}}
    },
    {
        "type": "function",
        "function": {"name": "get_reorder_alerts", "description": "Busca alertas de productos que están por debajo de su punto de reorden.", "parameters": {"type": "object", "properties": {}}}
    },
    {
        "type": "function",
        "function": {"name": "get_expiring_batches", "description": "Identifica lotes próximos a vencer en N días.", "parameters": {"type": "object", "properties": {"dias": {"type": "integer", "description": "Días a futuro para revisar vencimiento. Default 30."}}}}
    },
    {
        "type": "function",
        "function": {"name": "get_delayed_orders_stats", "description": "Encuentra productos con órdenes atrasadas que no han sido entregadas.", "parameters": {"type": "object", "properties": {}}}
    },
    {
        "type": "function",
        "function": {"name": "get_lot_location", "description": "Busca la ubicación exacta (Bodega, Rack, Estiba) de un código de lote.", "parameters": {"type": "object", "properties": {"lote_codigo": {"type": "string"}}, "required": ["lote_codigo"]}}
    },
    {
        "type": "function",
        "function": {"name": "get_projected_inventory", "description": "Calcula el inventario proyectado (stock físico + pedidos - atrasos) de un producto.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}
    },
    {
        "type": "function",
        "function": {"name": "get_requests_status", "description": "Busca solicitudes internas por estado (ej. 'PENDIENTE', 'APROBADA').", "parameters": {"type": "object", "properties": {"estado": {"type": "string"}}, "required": ["estado"]}}
    },
    {
        "type": "function",
        "function": {"name": "get_recent_movements", "description": "Resumen de entradas y salidas recientes (últimas 48h) de una bodega.", "parameters": {"type": "object", "properties": {"bodega_nombre": {"type": "string"}}, "required": ["bodega_nombre"]}}
    },
    {
        "type": "function",
        "function": {"name": "get_inventory_analytics", "description": "Datos analíticos avanzados: bodega con más referencias y porcentajes de inventario (MP vs Terminado).", "parameters": {"type": "object", "properties": {}}}
    }
]
