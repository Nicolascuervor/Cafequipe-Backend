import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.inventory.models import Producto

def _determine_unit(nombre):
    if any(k in nombre for k in ['leche', 'líquida', 'liquida', 'agua']):
        return 'L'
    if any(k in nombre for k in ['azúcar', 'azucar', 'bicarbonato', 'café', 'cafe', 'cultivo', 'coco', 'macadamia', 'enzima', 'sorbato']):
        if any(k in nombre for k in [' 100 g', ' 500g', '500 gramos']):
            return 'PAQ'
        elif any(k in nombre for k in ['gramos', ' g ']):
            return 'G'
        return 'KG'
    if 'caja' in nombre:
        return 'CAJ'
    if any(k in nombre for k in ['bolsa', 'doy pack', 'bol ', 'pouch', 'guasca']):
        return 'PAQ'
    if any(k in nombre for k in ['etiqueta', 'envase', 'foil']):
        return 'UND'
    if any(k in nombre for k in ['mermelada', 'arequipe', 'galleta', 'bebida']):
        return 'UND'
    return None

def smart_update_units():
    productos = Producto.objects.all()
    actualizados = 0

    for p in productos:
        nombre = p.nombre.lower()
        nueva_unidad = _determine_unit(nombre)
        
        # Override for specific edge cases from the screenshot
        if 'envase' in nombre:
            nueva_unidad = 'UND'
        if 'caja' in nombre:
            nueva_unidad = 'CAJ'
        
        if nueva_unidad and p.unidad_medida != nueva_unidad:
            p.unidad_medida = nueva_unidad
            p.save()
            actualizados += 1
            print(f"[{nueva_unidad}] asignado a: {p.nombre}")

    print(f"\nProceso terminado. Se actualizaron {actualizados} productos de {productos.count()}.")

if __name__ == '__main__':
    smart_update_units()
