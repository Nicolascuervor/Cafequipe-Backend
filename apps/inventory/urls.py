# apps/inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Categorías
    path('categorias/',            views.CategoriaListCreateView.as_view(), name='categoria-list'),
    path('categorias/<uuid:pk>/',  views.CategoriaDetailView.as_view(),     name='categoria-detail'),

    # Productos
    path('productos/',             views.ProductoListCreateView.as_view(),  name='producto-list'),
    path('productos/<uuid:pk>/',   views.ProductoDetailView.as_view(),      name='producto-detail'),

    # Bodegas
    path('bodegas/',               views.BodegaListCreateView.as_view(),    name='bodega-list'),
    path('bodegas/<uuid:pk>/',     views.BodegaDetailView.as_view(),        name='bodega-detail'),

    # Stock por Bodega
    path('stock/',                 views.StockBodegaListCreateView.as_view(), name='stock-list'),
    path('stock/<uuid:pk>/',       views.StockBodegaDetailView.as_view(),    name='stock-detail'),
]