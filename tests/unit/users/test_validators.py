import pytest
from unittest.mock import MagicMock
from django.core.exceptions import ValidationError
from apps.users.validators import validate_file_size

class TestFileValidators:

    def test_validate_file_size_valido(self):
        mock_file = MagicMock()
        mock_file.size = 2 * 1024 * 1024
        validate_file_size(mock_file)

    def test_validate_file_size_invalido(self):

        mock_file = MagicMock()
        mock_file.size = 6 * 1024 * 1024
        with pytest.raises(ValidationError, match="El tamaño máximo del archivo es de 5 MB"):
            validate_file_size(mock_file)

    def test_validate_file_size_limite_exacto(self):
        mock_file = MagicMock()
        mock_file.size = 5 * 1024 * 1024
        validate_file_size(mock_file)
