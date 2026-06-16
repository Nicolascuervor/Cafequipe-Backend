import os
import django

# Configurar el entorno de Django para poder usar los modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import User

# Lista de usuarios a garantizar
users_data = [
    {"email": "vhoyos703@cue.edu.co", "first": "Valentina", "last": "Hoyos"},
    {"email": "iarias579@cue.edu.co", "first": "Isabella", "last": "Arias"},
    {"email": "mgiraldo3163@cue.edu.co", "first": "Victoria", "last": "Giraldo"},
    {"email": "ncuervo_175@cue.edu.co", "first": "Nicolas", "last": "Cuervo"},
]

print("Iniciando actualización de usuarios...")

for data in users_data:
    # Buscar el usuario por correo, si no existe lo crea
    user, created = User.objects.get_or_create(email=data["email"])
    
    # Actualizar datos
    user.first_name = data["first"]
    user.last_name = data["last"]
    user.rol = "GER" # Rol de Gerente
    
    # Restauramos la contraseña por defecto para asegurar que todas puedan entrar
    user.set_password("Cafequipe2026!")
    user.save()
    
    if created:
        print(f"[\u2713] Usuario CREADO: {user.first_name} {user.last_name} ({user.email})")
    else:
        print(f"[\u2713] Usuario ACTUALIZADO: {user.first_name} {user.last_name} ({user.email})")

print("\n\u00a1Todos los usuarios han sido configurados como Gerentes exitosamente!")
