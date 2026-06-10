import pytest
from apps.notifications.models import SystemEmailConfiguration

@pytest.mark.django_db
class TestSystemEmailConfigurationSingleton:

    def test_load_creates_initial_config(self):

        assert SystemEmailConfiguration.objects.count() == 0

        config = SystemEmailConfiguration.load()

        assert config is not None
        assert SystemEmailConfiguration.objects.count() == 1
        assert config.notify_alerts is True

    def test_singleton_behavior(self):

        config_original = SystemEmailConfiguration.load()
        config_original.admin_email = 'admin1@cafequipe.com'
        config_original.save()

        config_nueva = SystemEmailConfiguration(admin_email='admin2@cafequipe.com')
        config_nueva.save()

        assert SystemEmailConfiguration.objects.count() == 1

        config_actual = SystemEmailConfiguration.load()
        assert config_actual.admin_email == 'admin2@cafequipe.com'

    def test_delete_disabled(self):

        config = SystemEmailConfiguration.load()
        assert SystemEmailConfiguration.objects.count() == 1

        config.delete()

        assert SystemEmailConfiguration.objects.count() == 1