# apps/users/permissions/__init__.py
from .EsGerente import EsGerente
from .EsGerenteOJefeBodega import EsGerenteOJefeBodega
from .EsGerenteOSoloLectura import EsGerenteOSoloLectura
from .EsGerenteOJefeBodegaPeroSoloGerenteElimina import EsGerenteOJefeBodegaPeroSoloGerenteElimina

__all__ = [
    'EsGerente',
    'EsGerenteOJefeBodega',
    'EsGerenteOSoloLectura',
    'EsGerenteOJefeBodegaPeroSoloGerenteElimina',
]
