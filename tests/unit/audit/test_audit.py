import pytest
from apps.users.models import User
from apps.audit.models import AuditLog

@pytest.mark.django_db
class TestAuditLogModel:

    @pytest.fixture
    def usuario(self):
        return User.objects.create_user(email='auditor@cafequipe.com', password='123')

    def test_inmutabilidad_edicion(self, usuario):
        """
        Prueba que el sistema lance un PermissionError si alguien (incluso por código)
        intenta invocar save() sobre un log que ya existía en la base de datos.
        """
        log = AuditLog.objects.create(
            user=usuario,
            user_email=usuario.email,
            action=AuditLog.Action.LOGIN,
            module=AuditLog.Module.AUTH,
            description='Login exitoso'
        )

        # Intentamos manipular la descripción y guardarlo
        log.description = 'Login manipulado por hacker'
        
        with pytest.raises(PermissionError, match='No se permite la modificación'):
            log.save()

    def test_inmutabilidad_eliminacion(self, usuario):
        """
        Prueba que el sistema lance un PermissionError al intentar borrar 
        un log de auditoría (invocando delete()).
        """
        log = AuditLog.objects.create(
            user=usuario,
            user_email=usuario.email,
            action=AuditLog.Action.USER_CREATED,
            module=AuditLog.Module.USERS,
            description='Creación de usuario'
        )

        # Intentamos eliminar el registro
        with pytest.raises(PermissionError, match='No se permite la eliminación'):
            log.delete()

    def test_str_auditlog(self, usuario):
        """Prueba el formato de la representación en texto del log."""
        log = AuditLog.objects.create(
            user=usuario,
            user_email='prueba@cafequipe.com',
            action=AuditLog.Action.LOGOUT,
            module=AuditLog.Module.AUTH,
            description='Logout'
        )
        
        formato_esperado = f"[{log.timestamp:%Y-%m-%d %H:%M}] {log.action} — prueba@cafequipe.com"
        assert str(log) == formato_esperado
