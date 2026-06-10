import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestReportsFlow:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.gerente = User.objects.create_user(
            email='gerente3@cafequipe.com', password='Password123!',
            rol=User.Rol.GERENTE, first_name='Carlos', last_name='G'
        )
        self.kpi_inv_url = reverse('reports:kpis-inventory')
        self.kpi_prod_url = reverse('reports:kpis-production')
        # URLs ficticias que deberían existir según el plan
        self.reporte_excel_url = '/api/v1/reports/export/excel/'
        self.reporte_pdf_url = '/api/v1/reports/export/pdf/'

    def test_cp058_dashboard_indicadores(self, api_client):
        """CP-058: Dashboard con indicadores básicos de inventario."""
        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(self.kpi_inv_url)
        assert response.status_code == status.HTTP_200_OK
        assert 'kpi_perdida_vencidos' in response.json()

    def test_cp059_dashboard_alertas_activas(self, api_client):
        """CP-059: Dashboard muestra alertas activas diferenciadas."""
        api_client.force_authenticate(user=self.gerente)
        # Esto invoca la vista de alertas
        alertas_url = reverse('inventory:stock-alertas')
        response = api_client.get(alertas_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'stock_critico' in data
        assert 'stock_bajo' in data
        assert 'por_vencer' in data

    def test_cp060_generacion_reporte_actual(self, api_client):
        """CP-060: Generación de reporte de inventario actual."""
        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(reverse('inventory:stock-list'))
        assert response.status_code == status.HTTP_200_OK

    def test_cp063_reporte_vacio_sin_resultados(self, api_client):
        """CP-063: Reporte vacío con filtros sin resultados."""
        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(reverse('inventory:stock-list') + '?producto__nombre=Inexistente2026')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json().get('results', response.json())) == 0

    def test_cp061_exportacion_excel(self, api_client):
        """CP-061: Exportación de reporte a Excel (.xlsx)."""
        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(self.reporte_excel_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_cp062_exportacion_pdf(self, api_client):
        """CP-062: Exportación de reporte a PDF."""
        api_client.force_authenticate(user=self.gerente)
        response = api_client.get(self.reporte_pdf_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers['Content-Type'] == 'application/pdf'
