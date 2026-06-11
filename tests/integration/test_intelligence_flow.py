import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.inventory.models import CategoriaPrincipal, UnidadMedida, SubCategoria, Producto, Bodega, StockBodega
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestIntelligenceFlow:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):

        self.gerente = User.objects.create_user(
            email='gerente2@cafequipe.com', password='Password123!',
            rol=User.Rol.GERENTE, first_name='Carlos', last_name='Gerente'
        )

        self.subcategoria = SubCategoria.objects.create(nombre='SubCat Inteligencia')
        self.p1 = Producto.objects.create(nombre='Prod1', categoria_principal=CategoriaPrincipal.PRODUCTO, sub_categoria=self.subcategoria, costo_unitario='100.00', inventario_seguridad='10', punto_reorden='20')
        self.p2 = Producto.objects.create(nombre='Prod2', categoria_principal=CategoriaPrincipal.INSUMO, sub_categoria=self.subcategoria, costo_unitario='50.00', inventario_seguridad='5', punto_reorden='10')

        self.bodega = Bodega.objects.create(nombre='Bodega Inteligencia', ubicacion='Z', administrador=self.gerente)
        self.bodega.catalogo_admitido = [CategoriaPrincipal.PRODUCTO, CategoriaPrincipal.INSUMO]
        self.bodega.save()

        hoy = timezone.now().date()
        self.stock_p1 = StockBodega.objects.create(bodega=self.bodega, producto=self.p1, stock_disponible=Decimal('5.00'), fecha_vencimiento=hoy + timedelta(days=10)) # Crítico (<6)
        self.stock_p2 = StockBodega.objects.create(bodega=self.bodega, producto=self.p2, stock_disponible=Decimal('15.00'), fecha_vencimiento=hoy - timedelta(days=2)) # Vencido

        self.stock_url = reverse('inventory:stock-list')
        self.alertas_url = reverse('inventory:stock-alertas')
        self.abc_url = reverse('reports:abc-analysis')

    def test_cp048_inventario_consolidado(self, api_client):

        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(self.stock_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json().get('results', response.json())) == 2

    def test_cp049_filtrado_inventario(self, api_client):

        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(f"{self.stock_url}?producto__categoria_principal=PR")
        assert response.status_code == status.HTTP_200_OK
        data = response.json().get('results', response.json())
        assert len(data) == 1
        assert data[0]['producto_nombre'] == 'Prod1'

    def test_cp050_inventario_vacio(self, api_client):

        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(f"{self.stock_url}?search=NoExiste")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json().get('results', response.json())) == 0

    def test_cp051_cp052_analisis_abc(self, api_client):

        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(self.abc_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_inventory_value' in data
        assert 'A' in data['clasificacion']

        assert len(data['clasificacion']['A']) > 0

    def test_cp053_cp054_alerta_reorden_y_desaparicion(self, api_client):

        api_client.force_authenticate(user=self.gerente)

        response = api_client.get(self.alertas_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data['stock_critico']) >= 1
        assert data['stock_critico'][0]['producto_nombre'] == 'Prod1'

        self.stock_p1.stock_disponible = Decimal('25.00')
        self.stock_p1.save()
        
        response2 = api_client.get(self.alertas_url)
        data2 = response2.json()
        nombres_criticos = [x['producto_nombre'] for x in data2['stock_critico']]
        assert 'Prod1' not in nombres_criticos

    def test_cp055_cp056_cp057_alertas_vencimiento(self, api_client):

        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(self.alertas_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        vencimientos = [x['producto_nombre'] for x in data['por_vencer']]

        assert 'Prod1' in vencimientos
        assert 'Prod2' in vencimientos