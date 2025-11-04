from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Author
from .paginators import CustomPagination
from .serializers import AuthorSerializer
from .permissions import AuthorPermission


class AuthorViewSet(viewsets.ModelViewSet):
    """
    API для управления авторами:
    - GET /authors/ — список всех авторов
    - GET /authors/{id}/ — детальную информацию об авторе
    - POST /authors/ — создание нового автора
    - PUT/PATCH /authors/{id}/ — редактирование автора
    - DELETE /authors/{id}/ — удаление автора
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [AuthorPermission]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Поля для фильтрации (точная фильтрация)
    filterset_fields = ['last_name', 'first_name']

    # Поля для поиска (частичное совпадение, icontains)
    search_fields = ['last_name', 'first_name', 'biography']

    # Поля для сортировки
    ordering_fields = ['last_name', 'first_name', 'birth_date']
    ordering = ['last_name', 'first_name']  # дефолтная сортировка

    # Дополнительно: можно ограничить доступ (например, только для админов)
    # from rest_framework.permissions import IsAdminUser
    # permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
