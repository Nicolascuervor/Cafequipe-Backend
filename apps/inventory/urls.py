# apps/inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Subcategorías
    path('subcategorias/',            views.SubCategoriaListCreateView.as_view(), name='subcategoria-list'),
    path('subcategorias/<uuid:pk>/',  views.SubCategoriaDetailView.as_view(),     name='subcategoria-detail'),

    # Productos
    path('productos/',             views.ProductoListCreateView.as_view(),  name='producto-list'),
    path('productos/<uuid:pk>/',   views.ProductoDetailView.as_view(),      name='producto-detail'),

    # Bodegas
    path('bodegas/',               views.BodegaListCreateView.as_view(),    name='bodega-list'),
    path('bodegas/<uuid:pk>/',     views.BodegaDetailView.as_view(),        name='bodega-detail'),

    # Stock por Bodega
    path('stock/',                 views.StockBodegaListCreateView.as_view(), name='stock-list'),
    path('stock/alertas/',         views.AlertasStockView.as_view(),          name='stock-alertas'),
    path('stock/<uuid:pk>/',       views.StockBodegaDetailView.as_view(),     name='stock-detail'),
]