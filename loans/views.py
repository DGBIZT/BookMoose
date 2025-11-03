# books/views.py
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import BookLoan
from .serializers import BookLoanSerializer
from .permissions import BookLoanPermission


class BookLoanViewSet(viewsets.ModelViewSet):
    """
    API для управления выдачами книг:
    - GET /loans/ — список выдач
    - GET /loans/{id}/ — деталь о выдаче
    - POST /loans/ — создать выдачу
    - PUT/PATCH /loans/{id}/ — обновить выдачу
    - DELETE /loans/{id}/ — удалить выдачу
    """
    queryset = BookLoan.objects.all()
    serializer_class = BookLoanSerializer
    permission_classes = [BookLoanPermission]  # опционально
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Точная фильтрация
    filterset_fields = ['is_returned', 'book__id', 'user__id']

    # Поиск по подстроке (в названии книги, примечаниях)
    search_fields = ['book__title', 'notes']

    # Сортировка
    ordering_fields = [
        'loan_date', 'return_date', 'due_date',
        'book__title', 'user__username', 'is_returned'
    ]
    ordering = ['-loan_date']  # дефолтная сортировка: новые сверху


    def perform_create(self, serializer):
        """Автоматически устанавливает created_by = текущий пользователь."""
        serializer.save(created_by=self.request.user)

