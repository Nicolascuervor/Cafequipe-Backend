from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('abc/', views.ABCAnalysisView.as_view(), name='abc-analysis'),
    path('kpis/inventory/', views.InventoryKPIView.as_view(), name='kpis-inventory'),
    path('kpis/production/', views.ProductionKPIView.as_view(), name='kpis-production'),
    path('export/excel/', views.ExportExcelView.as_view(), name='export-excel'),
    path('export/pdf/', views.ExportPDFView.as_view(), name='export-pdf'),
]