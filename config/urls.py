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

    # ── API v1 ────────────────────────────────
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/inventory/', include('apps.inventory.urls')),
    path('api/v1/movements/', include('apps.movements.urls')),
    path('api/v1/production/', include('apps.production.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)