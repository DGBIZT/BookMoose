from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Genre
from .serializers import GenreSerializer
from .permissions import GenrePermission

class GenreViewSet(viewsets.ModelViewSet):
    """
    API для управления жанрами:
    - GET /genres/ — список жанров
    - GET /genres/{id}/ — деталь о жанре
    - POST /genres/ — создать жанр
    - PUT/PATCH /genres/{id}/ — обновить жанр
    - DELETE /genres/{id}/ — удалить жанр
    """
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [GenrePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


    # Точная фильтрация (например, ?parent=1&is_active=true)
    filterset_fields = ['parent', 'is_active']

    # Поиск по подстроке в name/description (?search=фантастика)
    search_fields = ['name', 'description']

    # Сортировка (?ordering=name,-order)
    ordering_fields = ['name', 'order', 'created_by__username']
    ordering = ['order', 'name']  # дефолтная сортировка

    def perform_create(self, serializer):
        """Автоматически устанавливает created_by = текущий пользователь."""
        serializer.save(created_by=self.request.user)
