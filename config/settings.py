# config/settings.py
from pathlib import Path
from datetime import timedelta
import environ

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# VARIABLES DE ENTORNO
# django-environ lee el archivo .env automáticamente
# ─────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(BASE_DIR / '.env')

# ─────────────────────────────────────────────
# SEGURIDAD CORE
# ─────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ─────────────────────────────────────────────
# APLICACIONES
# ─────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.users',
    'apps.inventory',
    'apps.movements',
    'apps.production',
    'apps.reports',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─────────────────────────────────────────────
# MIDDLEWARE
# corsheaders DEBE ir primero en la lista
# ─────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',       # ← PRIMERO
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─────────────────────────────────────────────
# BASE DE DATOS — PostgreSQL
# django-environ parsea la URL completa
# ─────────────────────────────────────────────
DATABASES = {
    'default': env.db('DATABASE_URL')
}
DATABASES['default']['ATOMIC_REQUESTS'] = True
# ATOMIC_REQUESTS: cada request HTTP se envuelve en una transacción
# Si algo falla, se hace rollback completo — protege la integridad del inventario

# ─────────────────────────────────────────────
# MODELO DE USUARIO PERSONALIZADO
# Siempre definirlo ANTES de la primera migración
# ─────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'

# ─────────────────────────────────────────────
# VALIDACIÓN DE CONTRASEÑAS
# ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─────────────────────────────────────────────
# DJANGO REST FRAMEWORK
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ─────────────────────────────────────────────
# JWT — Simple JWT
# ─────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)
    ),
    'ROTATE_REFRESH_TOKENS': True,       # Rota el refresh token en cada uso
    'BLACKLIST_AFTER_ROTATION': True,    # Invalida el token anterior
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_OBTAIN_SERIALIZER': 'apps.users.serializers.CustomTokenObtainPairSerializer',
}

# ─────────────────────────────────────────────
# CORS — Cross-Origin Resource Sharing
# Necesario para que React (puerto 5173) pueda
# hablar con Django (puerto 8000)
# ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://localhost:3000', 'http://localhost:8081', 'http://localhost:8000']
)
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL', default=DEBUG)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'origin',
    'x-requested-with',
]

# ─────────────────────────────────────────────
# SWAGGER / OPENAPI — drf-spectacular
# ─────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'CafeQuipe Inventory API',
    'DESCRIPTION': (
        'API REST para el sistema de gestión de inventario de CafeQuipe. '
        'Módulos: Productos, Insumos, Stock, Movimientos, Producción y Reportes.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Auth', 'description': 'Autenticación JWT'},
        {'name': 'Usuarios', 'description': 'Gestión de usuarios y roles'},
        {'name': 'Inventario', 'description': 'Productos e insumos'},
        {'name': 'Stock', 'description': 'Control de stock por bodega'},
        {'name': 'Movimientos', 'description': 'Entradas, salidas y traslados'},
        {'name': 'Producción', 'description': 'Lotes y proceso productivo'},
        {'name': 'Reportes', 'description': 'Análisis y exportaciones'},
    ],
}

# ─────────────────────────────────────────────
# INTERNACIONALIZACIÓN
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────
# ARCHIVOS ESTÁTICOS Y MEDIA
# ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'