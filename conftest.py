import pytest
from unittest.mock import patch
from apps.notifications.services import EmailThread

@pytest.fixture(autouse=True)
def run_email_threads_synchronously():
    """
    Obliga a que el envío de emails (que normalmente usa un hilo en background)
    se ejecute en el hilo principal durante los tests.
    Esto previene el warning de pytest-django sobre acceso a base de datos
    no permitido en hilos secundarios (PytestUnhandledThreadExceptionWarning).
    """
    with patch.object(EmailThread, 'start', new=EmailThread.run):
        yield
