import pytest
from apps.users.models import User
from apps.audit.models import AuditLog

@pytest.mark.django_db
class TestAuditLogModel:

    @pytest.fixture
    def usuario(self):
        return User.objects.create_user(email='auditor@cafequipe.com', password='123')

    def test_inmutabilidad_edicion(self, usuario):
        log = AuditLog.objects.create(
            user=usuario,
            user_email=usuario.email,
            action=AuditLog.Action.LOGIN,
            module=AuditLog.Module.AUTH,
            description='Login exitoso'
        )

        log.description = 'Login manipulado por hacker'
        
        with pytest.raises(PermissionError, match='No se permite la modificación'):
            log.save()

    def test_inmutabilidad_eliminacion(self, usuario):
        log = AuditLog.objects.create(
            user=usuario,
            user_email=usuario.email,
            action=AuditLog.Action.USER_CREATED,
            module=AuditLog.Module.USERS,
            description='Creación de usuario'
        )

        with pytest.raises(PermissionError, match='No se permite la eliminación'):
            log.delete()

    def test_str_auditlog(self, usuario):
        log = AuditLog.objects.create(
            user=usuario,
            user_email='prueba@cafequipe.com',
            action=AuditLog.Action.LOGOUT,
            module=AuditLog.Module.AUTH,
            description='Logout'
        )
        
        formato_esperado = f"[{log.timestamp:%Y-%m-%d %H:%M}] {log.action} — prueba@cafequipe.com"
        assert str(log) == formato_esperado
