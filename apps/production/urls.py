from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RecetaViewSet, OrdenProduccionViewSet,
    ParametroCalidadViewSet, ControlCalidadLoteViewSet,
    TicketInsumoViewSet
)

router = DefaultRouter()
router.register(r'recetas', RecetaViewSet, basename='recetas')
router.register(r'ordenes', OrdenProduccionViewSet, basename='ordenes')
router.register(r'parametros-calidad', ParametroCalidadViewSet, basename='parametros_calidad')
router.register(r'control-calidad', ControlCalidadLoteViewSet, basename='control_calidad')
router.register(r'tickets', TicketInsumoViewSet, basename='tickets')

urlpatterns = [
    path('', include(router.urls)),
]