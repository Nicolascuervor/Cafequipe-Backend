import pytest
from rest_framework import status
from django.urls import reverse
from apps.audit.models import AuditLog

@pytest.mark.django_db
class TestProductionFlow:
    """Suite de pruebas para el módulo de Órdenes de Producción."""

    def test_creacion_orden_forzado_pendiente(self, api_client, test_user):
        """
        Test 16: Verifica que al crear una orden de producción, el sistema fuerce
        el estado a PENDIENTE, previniendo que se inyecte un estado avanzado.
        """
        from apps.inventory.models import SubCategoria, Producto
        from apps.production.models import OrdenProduccion
        
        # 1. Preparar datos
        cat = SubCategoria.objects.create(nombre="Recetas")
        producto_final = Producto.objects.create(nombre="Torta de Chocolate", sub_categoria=cat, costo_unitario="0.00")
        
        # 2. Login Operario
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_user.email, 'password': 'TestPassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_ordenes = '/api/v1/production/ordenes/' # Basado en el enrutador
        
        # 3. Intentar inyectar estado APROBADO en la creación
        payload = {
            "producto": str(producto_final.id),
            "cantidad_solicitada": "50.00",
            "estado": "APROBADO", # ¡Inyección!
            "observaciones": "Producción urgente"
        }
        
        res_crear = api_client.post(url_ordenes, payload, format='json')
        assert res_crear.status_code == status.HTTP_201_CREATED, "El operario debería poder registrar una orden de producción"
        
        # 4. Validar estado en la base de datos
        orden_id = res_crear.data['id']
        orden = OrdenProduccion.objects.get(id=orden_id)
        
        assert orden.estado == "PENDIENTE", "VULNERABILIDAD: El sistema permitió inyectar un estado distinto a PENDIENTE en la creación."
        
        # 5. Validar Auditoría
        logs = AuditLog.objects.filter(user=test_user)
        # Asumiendo una constante para la auditoría, verificamos que exista algún log relacionado
        assert logs.filter(action__icontains="ORDEN").exists(), "Falta auditar la creación de la orden en AuditLog."

    def test_aprobacion_orden_generacion_ticket_peps(self, api_client, test_gerente, test_user):
        """
        Test 17: Verifica que al aprobar una Orden (de PENDIENTE a APROBADO),
        el sistema genere automáticamente un TicketInsumo.
        """
        from apps.inventory.models import SubCategoria, Producto
        from apps.production.models import OrdenProduccion, TicketInsumo
        
        # 1. Preparar datos (Orden PENDIENTE)
        cat = SubCategoria.objects.create(nombre="Recetas")
        producto_final = Producto.objects.create(nombre="Galletas", sub_categoria=cat, costo_unitario="0.00")
        
        orden = OrdenProduccion.objects.create(
            producto=producto_final,
            cantidad_solicitada="100.00",
            estado="PENDIENTE",
            usuario_solicita=test_user
        )
        
        # 2. Autenticar Gerente
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_gerente.email, 'password': 'GerentePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_orden_detalle = f'/api/v1/production/ordenes/{orden.id}/'
        
        # 3. Aprobar orden vía PATCH
        res_patch = api_client.patch(url_orden_detalle, {"estado": "APROBADO"}, format='json')
        assert res_patch.status_code == status.HTTP_200_OK, "El gerente debería poder aprobar la orden."
        
        # 4. Validar generación automática de TicketInsumo
        # El requerimiento indica que el backend debe despachar insumos bajo PEPS
        # y crear un ticket.
        tickets = TicketInsumo.objects.filter(orden_produccion=orden)
        assert tickets.exists(), "FAIL TDD: El sistema no generó automáticamente el TicketInsumo tras aprobar la orden."
        
        # 5. Validar estado persistido
        orden.refresh_from_db()
        assert orden.estado == "APROBADO", "El estado de la orden no se actualizó en la BD."

    def test_transicion_estados_bloqueo_cambios_completado(self, api_client, test_gerente, test_user):
        """
        Test 18: Verifica que una orden en estado COMPLETADO sea inmutable.
        Nadie debe poder cambiar sus cantidades ni retroceder su estado.
        """
        from apps.inventory.models import SubCategoria, Producto
        from apps.production.models import OrdenProduccion
        
        cat = SubCategoria.objects.create(nombre="Recetas")
        producto_final = Producto.objects.create(nombre="Galletas", sub_categoria=cat, costo_unitario="0.00")
        
        # 1. Crear la orden ya cerrada (simulando que el proceso finalizó)
        orden_cerrada = OrdenProduccion.objects.create(
            producto=producto_final,
            cantidad_solicitada="200.00",
            estado="COMPLETADO",
            usuario_solicita=test_user
        )
        
        # 2. Autenticar Gerente
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_gerente.email, 'password': 'GerentePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_orden_detalle = f'/api/v1/production/ordenes/{orden_cerrada.id}/'
        
        # 3. Intentar vulnerar la inmutabilidad
        payload_trampa = {
            "estado": "PENDIENTE",
            "cantidad_solicitada": "500.00"
        }
        res_patch = api_client.patch(url_orden_detalle, payload_trampa, format='json')
        
        # Debe fallar por validación (400) o permisos del objeto (403)
        assert res_patch.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN], "FAIL TDD: El sistema permitió modificar una orden COMPLETADA."
        
        # 4. Validar persistencia en BD
        orden_cerrada.refresh_from_db()
        assert orden_cerrada.estado == "COMPLETADO", "VULNERABILIDAD CRÍTICA: Se logró retroceder el estado de una orden finalizada."
        assert orden_cerrada.cantidad_solicitada == 200.00, "VULNERABILIDAD CRÍTICA: Se lograron alterar las cantidades de una orden finalizada."
