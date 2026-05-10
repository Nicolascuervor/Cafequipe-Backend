# apps/users/permissions/__init__.py
from .EsGerente import EsGerente
from .EsGerenteOJefeBodega import EsGerenteOJefeBodega
from .EsGerenteOSoloLectura import EsGerenteOSoloLectura

__all__ = [
    'EsGerente',
    'EsGerenteOJefeBodega',
    'EsGerenteOSoloLectura',
]
