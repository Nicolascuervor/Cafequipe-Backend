import pytest
from apps.notifications.models import SystemEmailConfiguration

@pytest.mark.django_db
class TestSystemEmailConfigurationSingleton:

    def test_load_creates_initial_config(self):
        """
        Prueba que el método estático load() instancie y guarde la 
        configuración inicial de la base de datos si esta aún no existía.
        """
        # Verificamos que partimos de cero
        assert SystemEmailConfiguration.objects.count() == 0
        
        # Invocamos el método de la clase
        config = SystemEmailConfiguration.load()
        
        # Verificamos que se creó un único registro con sus defaults
        assert config is not None
        assert SystemEmailConfiguration.objects.count() == 1
        assert config.notify_alerts is True

    def test_singleton_behavior(self):
        """
        Prueba la regla de oro del Singleton: Si se intenta crear otra configuración,
        simplemente sobrescribe la existente (ya que el método save() fuerza pk=1).
        """
        config_original = SystemEmailConfiguration.load()
        config_original.admin_email = 'admin1@cafequipe.com'
        config_original.save()
        
        # Intentamos instanciar una nueva en memoria y guardarla
        config_nueva = SystemEmailConfiguration(admin_email='admin2@cafequipe.com')
        config_nueva.save()
        
        # Verificamos que siga existiendo exactamente 1 fila en la DB (no se multiplicaron)
        assert SystemEmailConfiguration.objects.count() == 1
        
        # Verificamos que la nueva reemplazó a la vieja
        config_actual = SystemEmailConfiguration.load()
        assert config_actual.admin_email == 'admin2@cafequipe.com'

    def test_delete_disabled(self):
        """
        Prueba que el método delete() esté anulado para evitar que 
        un administrador o un error de código borre la configuración global.
        """
        config = SystemEmailConfiguration.load()
        assert SystemEmailConfiguration.objects.count() == 1
        
        # Invocamos delete() de Django (sobreescrito en este modelo con un 'pass')
        config.delete()
        
        # El registro debe seguir intacto
        assert SystemEmailConfiguration.objects.count() == 1
