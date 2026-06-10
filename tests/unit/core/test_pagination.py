import pytest
from unittest.mock import MagicMock
from apps.core.pagination import OptionalPagination

class TestOptionalPagination:

    def test_paginate_queryset_con_nopage_true(self):

        request_mock = MagicMock()
        request_mock.query_params = {'nopage': 'true'}
        
        paginator = OptionalPagination()

        resultado = paginator.paginate_queryset(queryset=[1, 2, 3], request=request_mock)

        assert resultado is None

    def test_paginate_queryset_sin_nopage(self):

        request_mock = MagicMock()

        request_mock.query_params = {}
        
        paginator = OptionalPagination()

        queryset_simulado = list(range(100)) 
        
        resultado = paginator.paginate_queryset(queryset=queryset_simulado, request=request_mock)

        assert resultado is not None
        assert len(resultado) == 25