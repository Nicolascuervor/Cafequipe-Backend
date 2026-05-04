# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Admin de Django
    path('admin/', admin.site.urls),

    # Documentación API — Swagger y Redoc
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth — JWT tokens
    path('api/auth/', include('apps.users.urls')),

    # Módulos de negocio
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/movements/', include('apps.movements.urls')),
    path('api/production/', include('apps.production.urls')),
    path('api/reports/', include('apps.reports.urls')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)