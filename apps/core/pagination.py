from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class OptionalPagination(PageNumberPagination):
    """
    Paginación por defecto que permite al frontend desactivarla enviando ?nopage=true
    Útil para cargar dropdowns completos sin romper la paginación de las tablas.
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get('nopage') == 'true':
            return None # Disable pagination
        return super().paginate_queryset(queryset, request, view)
