import pytest
from unittest.mock import MagicMock
from apps.core.pagination import OptionalPagination

class TestOptionalPagination:

    def test_paginate_queryset_con_nopage_true(self):
        """
        Prueba que la paginación se desactive (retornando None) 
        cuando el frontend envía ?nopage=true en la petición HTTP.
        """
        # Simulamos un objeto Request de Django Rest Framework
        request_mock = MagicMock()
        request_mock.query_params = {'nopage': 'true'}
        
        paginator = OptionalPagination()
        # Le pasamos una lista simple (queryset) y nuestro request simulado
        resultado = paginator.paginate_queryset(queryset=[1, 2, 3], request=request_mock)
        
        # Al devolver None, DRF sabe que debe ignorar la paginación
        assert resultado is None

    def test_paginate_queryset_sin_nopage(self):
        """
        Prueba que la paginación aplique su funcionamiento normal
        (tamaño de página = 25) si no se solicita desactivarla.
        """
        request_mock = MagicMock()
        # Simulamos parámetros vacíos (sin 'nopage')
        request_mock.query_params = {}
        
        paginator = OptionalPagination()
        
        # Usamos una lista de 100 números para simular 100 registros en BD
        # Django Rest Framework soporta paginar listas nativas de Python
        queryset_simulado = list(range(100)) 
        
        resultado = paginator.paginate_queryset(queryset=queryset_simulado, request=request_mock)
        
        # Como no enviamos 'nopage', debería retornar solo la primera página
        # La clase OptionalPagination tiene definido page_size = 25
        assert resultado is not None
        assert len(resultado) == 25
