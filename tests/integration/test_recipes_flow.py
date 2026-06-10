import pytest
from rest_framework import status
from apps.audit.models import AuditLog

@pytest.mark.django_db
class TestRecipesFlow:
    """Suite de pruebas para Despachos, Recetas y Calidad (Módulo 5)."""

    def test_despacho_ticket_insumo(self, api_client, test_user):
        """
        Test 19: Verifica que un Operario pueda cambiar el estado de un 
        TicketInsumo a DESPACHADO, simulando la entrega física en planta.
        """
        from apps.inventory.models import SubCategoria, Producto
        from apps.production.models import OrdenProduccion, TicketInsumo
        
        # 1. Preparar datos (Orden y Ticket en estado PENDIENTE)
        cat = SubCategoria.objects.create(nombre="Insumos")
        producto = Producto.objects.create(nombre="Harina", sub_categoria=cat, costo_unitario="1.00")
        
        orden = OrdenProduccion.objects.create(
            producto=producto,
            cantidad_solicitada="50.00",
            estado="APROBADO",
            usuario_solicita=test_user
        )
        
        ticket = TicketInsumo.objects.create(
            orden_produccion=orden,
            estado="PENDIENTE"
        )
        
        # 2. Autenticar Operario
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_user.email, 'password': 'TestPassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        # Basado en router.register(r'tickets', TicketInsumoViewSet) en apps/production/urls.py
        url_ticket = f'/api/v1/production/tickets/{ticket.id}/'
        
        # 3. Ejecutar Despacho
        payload = {"estado": "DESPACHADO"}
        res_patch = api_client.patch(url_ticket, payload, format='json')
        assert res_patch.status_code == status.HTTP_200_OK, "FAIL TDD: El Operario debería poder despachar el ticket (PATCH devolvió error)."
        
        # 4. Validar persistencia
        ticket.refresh_from_db()
        assert ticket.estado == "DESPACHADO", "FAIL TDD: El estado del ticket no se actualizó en la BD."
        
        # 5. Validar Auditoría
        logs = AuditLog.objects.filter(user=test_user)
        assert logs.filter(action__icontains="TICKET").exists() or logs.filter(action__icontains="DESPACHO").exists(), "FAIL TDD: Falta auditar el evento de despacho del ticket."

    def test_control_calidad_lote(self, api_client, test_user):
        """
        Test 20: Verifica que un inspector de calidad (o usuario) pueda
        registrar la evaluación de un lote de producción.
        """
        from apps.production.models import ParametroCalidad, ControlCalidadLote
        
        # 1. Preparar parámetro de calidad
        parametro = ParametroCalidad.objects.create(
            nombre="Humedad del Grano",
            descripcion="Porcentaje de humedad en café verde",
            valor_esperado="11.0 - 12.0%"
        )
        
        # 2. Autenticar
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_user.email, 'password': 'TestPassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_calidad = '/api/v1/production/control-calidad/'
        
        payload = {
            "lote": "LOTE-CAFE-001",
            "parametro": str(parametro.id),
            "valor_medido": "11.5%",
            "cumple": True,
            "observaciones": "Humedad óptima",
            "inspector": str(test_user.id)
        }
        
        # 3. Ejecutar Evaluación
        res_calidad = api_client.post(url_calidad, payload, format='json')
        assert res_calidad.status_code == status.HTTP_201_CREATED, "FAIL TDD: El endpoint de control de calidad falló o no existe."
        
        # 4. Validar persistencia
        evaluacion_id = res_calidad.data.get('id')
        if evaluacion_id:
            evaluacion = ControlCalidadLote.objects.get(id=evaluacion_id)
            assert evaluacion.cumple is True, "El dictamen no se guardó correctamente."
            assert evaluacion.lote == "LOTE-CAFE-001", "El número de lote no coincide."

    def test_validacion_receta_bloqueo_insumos_faltantes(self, api_client, test_gerente, test_user):
        """
        Test 21: Verifica que al intentar aprobar una orden, el sistema valide
        que exista suficiente stock de los ingredientes de la receta en bodega.
        Si falta stock, la orden no debe poder aprobarse.
        """
        from apps.inventory.models import SubCategoria, Producto, Bodega, StockBodega
        from apps.production.models import Receta, OrdenProduccion
        
        # 1. Preparar datos base
        cat_insumos = SubCategoria.objects.create(nombre="Insumos")
        cat_final = SubCategoria.objects.create(nombre="Finales")
        
        # Ingrediente y Producto Final
        harina = Producto.objects.create(nombre="Harina", sub_categoria=cat_insumos, costo_unitario="1.00")
        galletas = Producto.objects.create(nombre="Galletas", sub_categoria=cat_final, costo_unitario="5.00")
        
        bodega = Bodega.objects.create(nombre="Bodega Central")
        
        # FORZAMOS STOCK CERO para el ingrediente
        StockBodega.objects.create(producto=harina, bodega=bodega, cantidad="0.00")
        
        # 2. Configurar la Receta (Simulamos que existe una estructura de receta)
        # Asumiendo que Receta tiene un campo para ingredientes.
        # En TDD, si no existe el campo exacto, la prueba guiara la refactorización.
        try:
            receta = Receta.objects.create(producto=galletas, ingredientes=[{"producto_id": str(harina.id), "cantidad": "10.00"}])
        except TypeError:
            # Fallback si el modelo Receta aún no acepta el kwarg ingredientes en el create
            receta = Receta.objects.create(producto=galletas)
        
        # 3. Crear Orden PENDIENTE
        orden = OrdenProduccion.objects.create(
            producto=galletas,
            cantidad_solicitada="5.00", # Requerirá 50 de harina si existiera la relación real
            estado="PENDIENTE",
            usuario_solicita=test_user
        )
        
        # 4. Autenticar Gerente
        res_login = api_client.post('/api/v1/auth/login/', {'email': test_gerente.email, 'password': 'GerentePassword123!'}, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res_login.data['access']}")
        
        url_orden = f'/api/v1/production/ordenes/{orden.id}/'
        
        # 5. Intentar Aprobar Orden sin stock
        res_patch = api_client.patch(url_orden, {"estado": "APROBADO"}, format='json')
        
        # Asegurar que el sistema frene la operación
        assert res_patch.status_code == status.HTTP_400_BAD_REQUEST, "FAIL TDD: El sistema permitió aprobar una orden sin tener los insumos necesarios en stock."
        
        # 6. Validar que la orden sigue pendiente en la BD
        orden.refresh_from_db()
        assert orden.estado == "PENDIENTE", "FAIL TDD: La orden cambió de estado a pesar de que no hay insumos."
