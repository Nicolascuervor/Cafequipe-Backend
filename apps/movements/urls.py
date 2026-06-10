from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecepcionViewSet, SolicitudInternaViewSet, MovimientoViewSet

router = DefaultRouter()
router.register(r'recepciones', RecepcionViewSet, basename='recepcion')
router.register(r'solicitudes', SolicitudInternaViewSet, basename='solicitud')
router.register(r'historial', MovimientoViewSet, basename='movimiento')

app_name = 'movements'

urlpatterns = [
    path('', include(router.urls)),
]