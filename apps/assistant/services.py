from apps.inventory.models import Producto, Bodega, StockBodega
from apps.users.models import User


def get_system_context():
    """
    Obtiene datos agregados del sistema para el contexto del asistente.
    No incluye información sensible de usuarios.
    """
    context = {
        'productos': {
            'total': Producto.objects.count(),
            'por_clasificacion': {
                'A': Producto.objects.filter(clasificacion='A').count(),
                'B': Producto.objects.filter(clasificacion='B').count(),
                'C': Producto.objects.filter(clasificacion='C').count(),
            },
            'por_categoria': {
                'Materia Prima': Producto.objects.filter(categoria_principal='MP').count(),
                'Insumo': Producto.objects.filter(categoria_principal='IN').count(),
                'Producto': Producto.objects.filter(categoria_principal='PR').count(),
            }
        },
        'bodegas': {
            'total': Bodega.objects.count(),
        },
        'usuarios': {
            'total': User.objects.count(),
            'por_rol': {
                'Gerente': User.objects.filter(rol='GER').count(),
                'Jefe de Bodega': User.objects.filter(rol='JBD').count(),
                'Jefe de Producción': User.objects.filter(rol='JPR').count(),
                'Operario': User.objects.filter(rol='OPR').count(),
            }
        },
        'stock': {
            'total_registros': StockBodega.objects.count(),
        }
    }
    return context


def get_product_info(product_name):
    """
    Obtiene información básica de un producto sin datos sensibles.
    """
    try:
        producto = Producto.objects.filter(nombre__icontains=product_name).first()
        if producto:
            return {
                'nombre': producto.nombre,
                'clasificacion': producto.get_clasificacion_display(),
                'categoria': producto.get_categoria_principal_display(),
                'unidad_medida': producto.get_unidad_medida_display(),
                'costo_unitario': str(producto.costo_unitario),
                'inventario_seguridad': str(producto.inventario_seguridad),
                'punto_reorden': str(producto.punto_reorden),
            }
    except Exception:
        pass
    return None


def needs_system_data(message):
    """
    Detecta si la pregunta requiere datos del sistema.
    """
    message_lower = message.lower()

    keywords = [
        'cuántos productos', 'cuantos productos',
        'clasificación', 'clasificacion',
        'categoría', 'categoria',
        'cuántos usuarios', 'cuantos usuarios',
        'inventario', 'stock',
        'bodega', 'bodegas',
        'producto', 'productos',
        'usuarios', 'usuario',
    ]

    return any(keyword in message_lower for keyword in keywords)


def get_fallback_response(message):
    """
    Responde preguntas básicas del sistema sin necesitar OpenRouter.
    Retorna None si la pregunta no puede resolverse localmente.
    """
    msg = message.lower()

    # --- Productos: totales ---
    if any(k in msg for k in [
        'cuántos productos', 'cuantos productos',
        'productos hay', 'hay productos', 'total de productos', 'total productos',
    ]):
        ctx = get_system_context()
        p = ctx['productos']
        return (
            f"El sistema tiene {p['total']} productos registrados en total. "
            f"Por clasificación: {p['por_clasificacion']['A']} de clase A, "
            f"{p['por_clasificacion']['B']} de clase B y "
            f"{p['por_clasificacion']['C']} de clase C. "
            f"Por categoría: {p['por_categoria']['Materia Prima']} materias primas, "
            f"{p['por_categoria']['Insumo']} insumos y "
            f"{p['por_categoria']['Producto']} productos terminados."
        )

    # --- Productos: por clasificación ---
    if 'clasificaci' in msg:
        if ' a' in msg or msg.endswith('a'):
            count = Producto.objects.filter(clasificacion='A').count()
            return f"Hay {count} productos de clasificación A en el sistema."
        if ' b' in msg or msg.endswith('b'):
            count = Producto.objects.filter(clasificacion='B').count()
            return f"Hay {count} productos de clasificación B en el sistema."
        if ' c' in msg or msg.endswith('c'):
            count = Producto.objects.filter(clasificacion='C').count()
            return f"Hay {count} productos de clasificación C en el sistema."

    # --- Productos: por categoría ---
    if any(k in msg for k in ['materia prima', 'materias primas']):
        count = Producto.objects.filter(categoria_principal='MP').count()
        return f"El sistema tiene {count} materias primas registradas."

    if 'insumo' in msg:
        count = Producto.objects.filter(categoria_principal='IN').count()
        return f"El sistema tiene {count} insumos registrados."

    # --- Bodegas ---
    if any(k in msg for k in [
        'cuántas bodegas', 'cuantas bodegas', 'bodegas hay', 'hay bodegas',
        'total bodegas', 'total de bodegas',
    ]):
        count = Bodega.objects.count()
        return f"El sistema tiene {count} bodegas registradas."

    # --- Usuarios ---
    if any(k in msg for k in [
        'cuántos usuarios', 'cuantos usuarios', 'usuarios hay', 'hay usuarios',
        'total usuarios', 'total de usuarios',
    ]):
        ctx = get_system_context()
        u = ctx['usuarios']
        return (
            f"El sistema tiene {u['total']} usuarios registrados. "
            f"Por rol: {u['por_rol']['Gerente']} gerentes, "
            f"{u['por_rol']['Jefe de Bodega']} jefes de bodega, "
            f"{u['por_rol']['Jefe de Producción']} jefes de producción y "
            f"{u['por_rol']['Operario']} operarios."
        )

    # --- Stock ---
    if any(k in msg for k in ['cuánto stock', 'cuanto stock', 'registros de stock', 'stock hay']):
        ctx = get_system_context()
        return f"El sistema tiene {ctx['stock']['total_registros']} registros de stock en las bodegas."

    # --- Producto específico por nombre ---
    if any(k in msg for k in ['información de', 'informacion de', 'info de', 'detalles de', 'busca', 'buscar']):
        words = [w for w in msg.split() if len(w) > 4]
        for word in words:
            info = get_product_info(word)
            if info:
                return (
                    f"Encontré información sobre {info['nombre']}: "
                    f"clasificación {info['clasificacion']}, "
                    f"categoría {info['categoria']}, "
                    f"unidad de medida {info['unidad_medida']}, "
                    f"costo unitario ${info['costo_unitario']}, "
                    f"inventario de seguridad {info['inventario_seguridad']} unidades y "
                    f"punto de reorden {info['punto_reorden']} unidades."
                )

    return None
