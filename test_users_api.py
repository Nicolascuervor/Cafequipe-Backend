"""Script de prueba para los endpoints de Users — CafeQuipe"""
import requests
import json
import sys

BASE = 'http://localhost:8000/api/auth'

# ─────────────────────────────────────────
# TEST 1: LOGIN
# ─────────────────────────────────────────
print('=' * 50)
print('TEST 1: LOGIN (POST /api/auth/login/)')
print('=' * 50)

r = requests.post(f'{BASE}/login/', json={
    'username': 'admin',
    'password': 'CafeQuipe2026!'
})
print(f'Status: {r.status_code}')

if r.status_code != 200:
    print(f'Error: {r.text}')
    print('\n>>> No se pudo hacer login. Verifica la password del superusuario.')
    print('>>> Si no la recuerdas, corre: python manage.py changepassword nicocu1127@gmail.com')
    sys.exit(1)

data = r.json()
token = data['access']
user_info = data.get('user', {})
print(f'Token obtenido: {token[:40]}...')
print(f'Usuario: {json.dumps(user_info, indent=2, ensure_ascii=False)}')

headers = {'Authorization': f'Bearer {token}'}

# ─────────────────────────────────────────
# TEST 2: MI PERFIL
# ─────────────────────────────────────────
print('\n' + '=' * 50)
print('TEST 2: MI PERFIL (GET /api/auth/me/)')
print('=' * 50)

r = requests.get(f'{BASE}/me/', headers=headers)
print(f'Status: {r.status_code}')
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─────────────────────────────────────────
# TEST 3: REGISTRAR USUARIO (solo Gerente)
# ─────────────────────────────────────────
print('\n' + '=' * 50)
print('TEST 3: REGISTRAR USUARIO (POST /api/auth/register/)')
print('=' * 50)

r = requests.post(f'{BASE}/register/', headers=headers, json={
    'email': 'operario.test@cafequipe.com',
    'first_name': 'Juan',
    'last_name': 'Prueba',
    'rol': 'OPR',
    'telefono': '3001234567',
    'password': 'CafeQuipe2026!',
    'password_confirm': 'CafeQuipe2026!'
})
print(f'Status: {r.status_code}')
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─────────────────────────────────────────
# TEST 4: LISTAR USUARIOS
# ─────────────────────────────────────────
print('\n' + '=' * 50)
print('TEST 4: LISTAR USUARIOS (GET /api/auth/users/)')
print('=' * 50)

r = requests.get(f'{BASE}/users/', headers=headers)
print(f'Status: {r.status_code}')
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─────────────────────────────────────────
# TEST 5: LOGIN CON USUARIO NUEVO (debe fallar permisos de registro)
# ─────────────────────────────────────────
print('\n' + '=' * 50)
print('TEST 5: LOGIN CON OPERARIO + INTENTO DE REGISTRO (debe dar 403)')
print('=' * 50)

r = requests.post(f'{BASE}/login/', json={
    'username': 'operario.test@cafequipe.com',
    'password': 'CafeQuipe2026!'
})
if r.status_code == 200:
    op_token = r.json()['access']
    op_headers = {'Authorization': f'Bearer {op_token}'}
    print(f'Login operario OK: {r.json().get("user", {})}')

    # Intentar registrar usuario como Operario (debe fallar)
    r2 = requests.post(f'{BASE}/register/', headers=op_headers, json={
        'email': 'hacker@evil.com',
        'first_name': 'Hacker',
        'last_name': 'Evil',
        'password': 'Password123!',
        'password_confirm': 'Password123!'
    })
    print(f'Intento registro como Operario -> Status: {r2.status_code}')
    print(f'Respuesta: {r2.json()}')
else:
    print(f'Login operario fallo: {r.status_code}')

print('\n' + '=' * 50)
print('TODOS LOS TESTS COMPLETADOS')
print('=' * 50)
