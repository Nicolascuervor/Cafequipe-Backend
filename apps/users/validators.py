from django.core.exceptions import ValidationError

def validate_file_size(value):
    """
    Valida que el archivo no supere los 5 MB.
    """
    limit_mb = 5
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"El tamaño máximo del archivo es de {limit_mb} MB.")
