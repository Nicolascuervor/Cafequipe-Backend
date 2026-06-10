import pytest
from rest_framework import status
from apps.audit.models import AuditLog

@pytest.mark.django_db
class TestMovementsFlow:
    """
    Suite de pruebas para el flujo de Movimientos de Inventario.
    Nota (TDD/QA): La aplicación 'movements' aún está vacía. Estas pruebas
    guiarán el desarrollo y fallarán con propósito hasta que se implemente la lógica.
    """

    def test_entrada_insumos_suma_stock(self, api_client, test_jefe_bodega):
        """
        Test 13: Verifica que un movimiento de ENTRADA aumente el stock
        físico de la bodega destino en la cantidad especificada.
        """
        from apps.inventory.models import SubCategoria, Producto, Bodega, StockBodega
        
        # 1. Preparar el terreno
        categoria = SubCategoria.objects.create(nombre="Insumos")
        producto = Producto.objects.create(nombre="Vaso Cartón", sub_categoria=categoria, costo_unitario="0.10", inventario_seguridad="10", punto_reorden="20")
        bodega = Bodega.objects.create(nombre="Bodega Insumos")
        stock = StockBodega.objects.create(producto=producto, bodega=bodega, cantidad="0.00")
        
        # 2. Autenticar
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_jefe_bodega.email, 'password': 'JefePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        # Asumimos que la URL será /api/v1/movements/ según los estándares REST observados en config/urls.py
        url_movements = '/api/v1/movements/'
        
        payload_entrada = {
            "tipo_movimiento": "ENTRADA", # Asumimos opciones: ENTRADA, SALIDA, TRASLADO
            "producto": str(producto.id),
            "bodega_origen": None,
            "bodega_destino": str(bodega.id),
            "cantidad": "150.00",
            "observaciones": "Compra a proveedor XYZ"
        }
        
        # 3. Ejecutar POST
        res_movimiento = api_client.post(url_movements, payload_entrada, format='json')
        assert res_movimiento.status_code == status.HTTP_201_CREATED, "FAIL TDD: El endpoint de movimientos no existe o falló al crear el registro."
        
        # 4. Validar suma automática de stock (La magia detrás del movimiento)
        stock.refresh_from_db()
        assert stock.cantidad == 150, f"FAIL TDD: El stock debería ser 150, pero sigue en {stock.cantidad}. Falta implementar la señal o reescritura del save() para la sumatoria."
        
        # 5. Validar Auditoría
        # Asumimos que existirá una acción MOVIMIENTO_CREATED o similar en el modelo AuditLog
        logs = AuditLog.objects.filter(user=test_jefe_bodega)
        assert logs.filter(action__icontains="MOVIMIENTO").exists(), "FAIL TDD: Falta registrar el evento del movimiento en la auditoría."

    def test_salida_insumos_proteccion_stock_negativo(self, api_client, test_jefe_bodega):
        """
        Test 14: Verifica que un movimiento de SALIDA reste del stock físico,
        y comprueba la validación crítica de que el stock no puede ser negativo.
        """
        from apps.inventory.models import SubCategoria, Producto, Bodega, StockBodega
        
        # 1. Preparar el terreno
        categoria = SubCategoria.objects.create(nombre="Insumos Varios")
        producto = Producto.objects.create(nombre="Sirope Vainilla", sub_categoria=categoria, costo_unitario="5.00", inventario_seguridad="2", punto_reorden="5")
        bodega = Bodega.objects.create(nombre="Bodega Suministros")
        
        # Truco para pruebas: Forzamos el stock inicial a 50 mediante ORM puro
        stock = StockBodega.objects.create(producto=producto, bodega=bodega, cantidad="50.00")
        
        # 2. Autenticar
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_jefe_bodega.email, 'password': 'JefePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_movements = '/api/v1/movements/'
        
        # 3. Intentar sacar más de lo que hay (200 unidades vs 50 en stock)
        payload_salida_excesiva = {
            "tipo_movimiento": "SALIDA",
            "producto": str(producto.id),
            "bodega_origen": str(bodega.id),
            "bodega_destino": None,
            "cantidad": "200.00",
            "observaciones": "Merma por vencimiento"
        }
        res_salida_fail = api_client.post(url_movements, payload_salida_excesiva, format='json')
        
        # Asegurarnos de que el servidor se niegue a dejar el stock negativo
        assert res_salida_fail.status_code == status.HTTP_400_BAD_REQUEST, "FAIL TDD: El sistema permitió una salida mayor al stock disponible (Stock Negativo)."
        
        # Confirmar que la BD sigue intacta tras el fallo
        stock.refresh_from_db()
        assert stock.cantidad == 50, "FAIL TDD: El stock fue alterado a pesar de que la petición falló."
        
        # 4. Intentar sacar una cantidad válida (30 unidades)
        payload_salida_valida = payload_salida_excesiva.copy()
        payload_salida_valida["cantidad"] = "30.00"
        
        res_salida_exito = api_client.post(url_movements, payload_salida_valida, format='json')
        assert res_salida_exito.status_code == status.HTTP_201_CREATED, "FAIL TDD: El sistema rechazó una salida válida."
        
        # 5. Validar la resta automática
        stock.refresh_from_db()
        assert stock.cantidad == 20, f"FAIL TDD: El stock final debería ser 20 (50-30), pero quedó en {stock.cantidad}."

    def test_transferencia_bodegas_transaccion_atomica(self, api_client, test_jefe_bodega):
        """
        Test 15: Verifica que un TRASLADO reste de la bodega origen
        y sume a la bodega destino correctamente (simulando éxito atómico).
        """
        from apps.inventory.models import SubCategoria, Producto, Bodega, StockBodega
        
        # 1. Preparar el terreno
        categoria = SubCategoria.objects.create(nombre="Insumos")
        producto = Producto.objects.create(nombre="Cacao", sub_categoria=categoria, costo_unitario="8.00")
        
        bodega_origen = Bodega.objects.create(nombre="Bodega Central")
        bodega_destino = Bodega.objects.create(nombre="Sucursal Norte")
        
        # Stocks iniciales
        stock_origen = StockBodega.objects.create(producto=producto, bodega=bodega_origen, cantidad="100.00")
        stock_destino = StockBodega.objects.create(producto=producto, bodega=bodega_destino, cantidad="0.00")
        
        # 2. Autenticar
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_jefe_bodega.email, 'password': 'JefePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_movements = '/api/v1/movements/'
        
        # 3. Ejecutar Traslado
        payload_traslado = {
            "tipo_movimiento": "TRASLADO",
            "producto": str(producto.id),
            "bodega_origen": str(bodega_origen.id),
            "bodega_destino": str(bodega_destino.id),
            "cantidad": "40.00",
            "observaciones": "Reabastecimiento de sucursal"
        }
        
        res_traslado = api_client.post(url_movements, payload_traslado, format='json')
        assert res_traslado.status_code == status.HTTP_201_CREATED, "FAIL TDD: Falló la creación del traslado en el endpoint."
        
        # 4. Validar sumas y restas atómicas
        stock_origen.refresh_from_db()
        stock_destino.refresh_from_db()
        
        assert stock_origen.cantidad == 60, f"FAIL TDD: El stock de origen debería tener 60 (100-40), pero tiene {stock_origen.cantidad}."
        assert stock_destino.cantidad == 40, f"FAIL TDD: El stock de destino debería tener 40 (0+40), pero tiene {stock_destino.cantidad}."
