# CafeQuipe Backend

Backend en Django Rest Framework (DRF) para el sistema de gestión de inventario y producción de CafeQuipe.

## 🚀 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado en tu sistema:
- [Python 3.10+](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/)

---

## 🛠️ Instalación y Configuración Local

Sigue estos pasos para levantar el proyecto en tu máquina local.

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd cafequipe
```

### 2. Entorno Virtual
Es obligatorio usar un entorno virtual para no ensuciar tu sistema con dependencias globales.

```powershell
# Crear el entorno virtual (solo la primera vez)
python -m venv venv

# Activar el entorno virtual (Windows)
.\venv\Scripts\activate

# (Si estás en Mac/Linux, usa: source venv/bin/activate)
```
> Sabrás que está activado porque verás `(venv)` al inicio de tu línea de comandos.

### 3. Instalar Dependencias
Con el entorno virtual activado, instala las librerías:
```powershell
pip install -r requirements.txt
```

### 4. Configurar la Base de Datos (PostgreSQL)
Abre **pgAdmin** o la consola de PostgreSQL (psql) y crea una base de datos y un usuario para desarrollo:

```sql
CREATE DATABASE cafequipe_db;
CREATE USER cafequipe_user WITH PASSWORD 'CQ_dev_2026!';
ALTER ROLE cafequipe_user SET client_encoding TO 'utf8';
ALTER ROLE cafequipe_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE cafequipe_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE cafequipe_db TO cafequipe_user;
-- Si usas PostgreSQL 15+, también debes ejecutar:
GRANT ALL ON SCHEMA public TO cafequipe_user;
```

### 5. Variables de Entorno
Crea un archivo llamado `.env` en la raíz del proyecto (al mismo nivel que `manage.py`). **Nunca subas este archivo a Git**.

Copia el siguiente contenido en tu `.env`:

```env
DEBUG=True
SECRET_KEY=django-insecure-tu-clave-secreta-local-muy-larga-12345

# URL de conexión a la BD: postgres://<usuario>:<password>@localhost:5432/<nombre_db>
DATABASE_URL=postgres://cafequipe_user:CQ_dev_2026!@localhost:5432/cafequipe_db

# CORS (Frontend local)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8081

# JWT Config (opcional, estos son los valores por defecto)
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

### 6. Migraciones
Aplica las migraciones para crear las tablas en la base de datos:
```powershell
python manage.py migrate
```

### 7. Crear el Superusuario (Admin)
Crea una cuenta para acceder al panel de administración y probar los endpoints protegidos:
```powershell
python manage.py createsuperuser
```
> **Nota:** El sistema usa el **email** para autenticarse, aunque la consola pregunte por `username`, debes escribir tu correo (ej. `admin@cafequipe.com`).

---

## 🏃‍♂️ Ejecutar el Servidor

Para levantar el servidor de desarrollo en `http://localhost:8000`:
```powershell
python manage.py runserver
```

### Acceso a la Documentación (Swagger)
Con el servidor corriendo, puedes ver y probar todos los endpoints del API desde tu navegador:

- **Swagger UI (Recomendado para pruebas):** [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **Redoc (Solo lectura, buena vista general):** [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)

### Acceso al Panel de Django
- **Admin Panel:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## 🏗️ Estructura del Proyecto

```text
cafequipe/
├── apps/               # Módulos del negocio
│   ├── users/          # Gestión de usuarios, roles y autenticación JWT
│   ├── inventory/      # Gestión de inventario
│   ├── movements/      # Entradas, salidas y traslados
│   ├── production/     # Lotes y mermas
│   └── reports/        # Consultas de reportes
├── config/             # Configuración general de Django (settings, urls)
├── .env                # Variables de entorno (NO subido a Git)
├── manage.py           # Script principal de Django
└── requirements.txt    # Dependencias del proyecto
```

## 🤝 Buenas Prácticas para el Equipo
1. **Siempre trabajar con el entorno virtual activado (`venv`).**
2. Si instalas una nueva librería (`pip install paquete`), recuerda actualizar el archivo de dependencias: `pip freeze > requirements.txt`.
3. Cualquier cambio en la estructura de la base de datos (models.py) requiere ejecutar `python manage.py makemigrations` y luego compartir los archivos generados en el repo para que el resto haga `migrate`.
