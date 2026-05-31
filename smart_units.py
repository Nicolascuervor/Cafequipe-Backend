import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.inventory.models import Producto

def smart_update_units():
    productos = Producto.objects.all()
    actualizados = 0

    for p in productos:
        nombre = p.nombre.lower()
        nueva_unidad = None

        if 'leche' in nombre or 'líquida' in nombre or 'liquida' in nombre or 'agua' in nombre:
            nueva_unidad = 'L'
        elif 'azúcar' in nombre or 'azucar' in nombre or 'bicarbonato' in nombre or 'café' in nombre or 'cafe' in nombre or 'cultivo' in nombre or 'coco' in nombre or 'macadamia' in nombre or 'enzima' in nombre or 'sorbato' in nombre:
            # Si incluye "100 g", "500g" en el nombre podríamos pasarlo a gramos, 
            # pero típicamente los polvos/granos a granel se miden en Kilos o Gramos.
            if ' 100 g' in nombre or ' 500g' in nombre or '500 gramos' in nombre:
                # wait, actually doy packs are packages.
                nueva_unidad = 'PAQ'
            elif 'gramos' in nombre or ' g ' in nombre:
                nueva_unidad = 'G'
            else:
                nueva_unidad = 'KG'
        elif 'caja' in nombre:
            nueva_unidad = 'CAJ'
        elif 'bolsa' in nombre or 'doy pack' in nombre or 'bol ' in nombre or 'pouch' in nombre or 'guasca' in nombre:
            nueva_unidad = 'PAQ'
        elif 'etiqueta' in nombre or 'envase' in nombre or 'foil' in nombre:
            nueva_unidad = 'UND'
        elif 'mermelada' in nombre or 'arequipe' in nombre or 'galleta' in nombre or 'bebida' in nombre:
            nueva_unidad = 'UND'
        
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
