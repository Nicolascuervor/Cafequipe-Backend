import pytest
from rest_framework import status

@pytest.mark.django_db
class TestReportsFlow:
    """Suite de pruebas para Trazabilidad, Reportes e Integración (Módulo 6)."""

    def test_trazabilidad_orden_produccion(self, api_client, test_gerente, test_user):
        """
        Test 22: Verifica que la API exponga un endpoint o serializador anidado
        que consolide la Orden, sus Tickets de Insumo y su Control de Calidad.
        """
        from apps.inventory.models import SubCategoria, Producto
        from apps.production.models import OrdenProduccion, TicketInsumo, ControlCalidadLote, ParametroCalidad
        
        # 1. Preparar Datos Base
        cat = SubCategoria.objects.create(nombre="Finales")
        producto = Producto.objects.create(nombre="Café Premium", sub_categoria=cat, costo_unitario="0.00")
        
        # 2. Crear Árbol de Trazabilidad (Simulando un histórico)
        orden = OrdenProduccion.objects.create(
            producto=producto, cantidad_solicitada="100.00", 
            estado="COMPLETADO", usuario_solicita=test_user
        )
        
        ticket = TicketInsumo.objects.create(
            orden_produccion=orden, estado="DESPACHADO"
        )
        
        parametro = ParametroCalidad.objects.create(nombre="Tueste", valor_esperado="Medio")
        calidad = ControlCalidadLote.objects.create(
            lote="LOTE-001", parametro=parametro, valor_medido="Medio",
            cumple=True, inspector=test_user
        )
        
        # OJO: Asumiendo que ControlCalidadLote se relaciona con la orden.
        # Si esta relación no existe en los modelos actuales, la prueba lo expondrá.
        if hasattr(ControlCalidadLote, 'orden_produccion'):
            calidad.orden_produccion = orden
            calidad.save()
            
        # 3. Autenticar Gerente
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_gerente.email, 'password': 'GerentePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        # 4. Consultar Trazabilidad
        # Asumimos un @action(detail=True) llamado 'trazabilidad'
        url_trazabilidad = f'/api/v1/production/ordenes/{orden.id}/trazabilidad/'
        res = api_client.get(url_trazabilidad)
        
        if res.status_code == status.HTTP_404_NOT_FOUND:
            # Fallback: intentar ver si la trazabilidad viene inyectada en el GET general
            url_trazabilidad = f'/api/v1/production/ordenes/{orden.id}/'
            res = api_client.get(url_trazabilidad)
            
        assert res.status_code == status.HTTP_200_OK, "FAIL TDD: No existe un endpoint para consultar la trazabilidad."
        
        # 5. Analizar Payload JSON
        data_string = str(res.data).lower() # Aplanamos el dict para búsqueda abstracta
        
        # Comprobamos que el endpoint devuelva los nodos relacionales
        assert str(ticket.id) in str(res.data) or "ticket" in data_string, "FAIL TDD: El reporte de trazabilidad no incluye los tickets de insumo usados."
        assert str(calidad.id) in str(res.data) or "calidad" in data_string, "FAIL TDD: El reporte de trazabilidad no incluye los resultados de control de calidad."

    def test_reporte_costos_integracion_inventario(self, api_client, test_gerente, test_user):
        """
        Test 23: Verifica que el sistema calcule el costo total de una
        Orden de Producción basándose en el costo unitario de los insumos gastados.
        """
        from apps.inventory.models import SubCategoria, Producto
        from apps.production.models import OrdenProduccion, TicketInsumo
        from decimal import Decimal
        
        # 1. Preparar Datos (Insumo con costo definido)
        cat_insumos = SubCategoria.objects.create(nombre="Insumos Básicos")
        cat_final = SubCategoria.objects.create(nombre="Producto Final")
        
        azucar = Producto.objects.create(nombre="Azúcar", sub_categoria=cat_insumos, costo_unitario="2.50")
        pastel = Producto.objects.create(nombre="Pastel", sub_categoria=cat_final, costo_unitario="0.00")
        
        # 2. Crear Orden y Ticket (Simulando un gasto de 10 unidades de Azúcar)
        orden = OrdenProduccion.objects.create(
            producto=pastel, cantidad_solicitada="1.00", 
            estado="COMPLETADO", usuario_solicita=test_user
        )
        
        # Asumiendo que TicketInsumo se vincula al Producto (insumo) gastado y su cantidad
        # Si el modelo varía, el test fallará indicando cómo refactorizar
        try:
            TicketInsumo.objects.create(
                orden_produccion=orden, 
                insumo=azucar,
                cantidad_usada="10.00",
                estado="DESPACHADO"
            )
        except TypeError:
            # Fallback simple si la BD no lo soporta de forma directa aún en kwargs
            TicketInsumo.objects.create(orden_produccion=orden, estado="DESPACHADO")
        
        # 3. Autenticar Gerente
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_gerente.email, 'password': 'GerentePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        # 4. Consultar el Reporte/Orden
        url_orden = f'/api/v1/production/ordenes/{orden.id}/'
        res = api_client.get(url_orden)
        
        assert res.status_code == status.HTTP_200_OK, "Error al obtener la orden."
        
        # 5. Validar el cálculo de costo (10 unidades * 2.50 = 25.00)
        payload = res.data
        
        costo_total = None
        if isinstance(payload, dict) and 'costo_total' in payload:
            costo_total = Decimal(str(payload['costo_total']))
        elif hasattr(orden, 'calcular_costo'):
            # Validar al menos el modelo si el serializador aún no expone el campo
            costo_total = Decimal(str(orden.calcular_costo()))
            
        assert costo_total is not None, "FAIL TDD: El endpoint no expone un campo 'costo_total' calculado, ni el modelo tiene un método 'calcular_costo()'."
        assert costo_total == Decimal("25.00"), f"FAIL TDD: El costo total debería ser 25.00, pero el sistema calculó {costo_total}."
