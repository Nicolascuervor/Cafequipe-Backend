import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():

    return APIClient()

@pytest.fixture
def test_user(db):

    user = User.objects.create_user(
        email="test_user@cafequipe.com",
        password="TestPassword123!",
        first_name="Test",
        last_name="User",
        rol="OPR"
    )
    return user

@pytest.fixture
def test_gerente(db):

    user = User.objects.create_superuser(
        email="gerente@cafequipe.com",
        password="GerentePassword123!",
        first_name="Admin",
        last_name="Gerente"
    )
    return user

@pytest.fixture
def test_jefe_bodega(db):

    user = User.objects.create_user(
        email="jefe.bodega@cafequipe.com",
        password="JefePassword123!",
        first_name="Jefe",
        last_name="Bodega",
        rol="JBD"
    )
    return user
