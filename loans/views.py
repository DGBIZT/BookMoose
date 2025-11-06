from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from .models import BookLoan, BookInstance
from .paginators import CustomPagination
from .serializers import BookLoanSerializer
from .permissions import BookLoanPermission



class BookLoanViewSet(viewsets.ModelViewSet):
    """
    API для управления выдачами книг.

    Endpoints:
    - GET /loans/ — список выдач (фильтры: is_returned, book_instance, user)
    - GET /loans/{id}/ — деталь о выдаче
    - POST /loans/ — создать выдачу (проверяет доступность экземпляра)
    - PUT/PATCH /loans/{id}/ — обновить выдачу (включая отметку о возврате)
    - DELETE /loans/{id}/ — отменить выдачу (возвращает экземпляр в фонд)

    Фильтры:
    - is_returned: true/false
    - book_instance: ID экземпляра
    - user: ID пользователя

    Поиск (search):
    - По title книги (через book_instance.book.title)
    - По notes

    Сортировка (ordering):
    - loan_date, return_date, due_date
    - book_instance__book__title, user__username
    """
    queryset = BookLoan.objects.all()
    serializer_class = BookLoanSerializer
    pagination_class = CustomPagination
    permission_classes = [BookLoanPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


    # Корректные поля для фильтрации
    filterset_fields = ['is_returned', 'book_instance', 'user']

    # Поиск
    search_fields = [
        'book_instance__book__title',  # через связь BookInstance → Book
        'notes'
    ]

    # Сортировка
    ordering_fields = [
        'loan_date', 'return_date', 'due_date',
        'book_instance__book__title', 'user__username', 'is_returned'
    ]
    ordering = ['-loan_date']

    def get_queryset(self):
        """Оптимизируем запросы: подгружаем связанные объекты."""
        return BookLoan.objects.select_related(
            'book_instance__book',
            'user',
            'created_by'
        ).prefetch_related('book_instance')

    def perform_create(self, serializer):
        """
        1. Проверяем доступность экземпляра.
        2. Устанавливаем created_by = текущий пользователь.
        3. Валидируем due_date.
        """
        book_instance = serializer.validated_data['book_instance']
        due_date = serializer.validated_data.get('due_date')

        # Проверка доступности
        if book_instance.status != 'available':
            raise ValidationError({
                'book_instance': 'Экземпляр уже выдан или недоступен.'
            })

        # Проверка срока возврата
        if due_date and due_date < timezone.now():
            raise ValidationError({
                'due_date': 'Срок возврата не может быть в прошлом.'
            })

        serializer.save(
            created_by=self.request.user,
            is_returned=False  # Явно задаём статус
        )

        # Обновляем статус экземпляра
        book_instance.status = 'loaned'
        book_instance.save()

    def perform_update(self, serializer):
        """
        При обновлении:
        - Если is_returned = True → устанавливаем return_date и освобождаем экземпляр.
        - Иначе → просто сохраняем.
        """
        instance = serializer.save()

        if instance.is_returned and not instance.return_date:
            instance.return_date = timezone.now()
            instance.save(update_fields=['return_date'])

        # Синхронизируем статус экземпляра
        if instance.is_returned:
            instance.book_instance.status = 'available'
        else:
            instance.book_instance.status = 'loaned'
        instance.book_instance.save()

    def perform_destroy(self, instance):
        """
        При удалении выдачи:
        1. Возвращаем экземпляр в фонд (status = 'available').
        2. Удаляем запись.
        """
        if not instance.is_returned:
            # Если книга не была возвращена, освобождаем экземпляр
            instance.book_instance.status = 'available'
            instance.book_instance.save()

        instance.delete()
