from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError

from .models import Book, BookInstance
from .serializers import BookSerializer, BookInstanceSerializer
from .paginators import CustomPagination
from .permissions import IsOwnerOrAdmin
from .filters import BookFilter, BOOK_SEARCH_FIELDS, BOOK_ORDERING_FIELDS
from rest_framework.decorators import action
from rest_framework.response import Response




class BookViewSet(viewsets.ModelViewSet):
    """
    API для управления книгами:
    - Все пользователи могут просматривать список и детали.
    - Создание: доступно авторизованным пользователям (книга привязывается к автору).
    - Редактирование/удаление: только владелец книги ИЛИ админ.
    """
    serializer_class = BookSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookFilter
    search_fields = BOOK_SEARCH_FIELDS
    ordering_fields = BOOK_ORDERING_FIELDS
    ordering = ['title']
    permission_classes = [IsOwnerOrAdmin]  # Единое разрешение для всех действий

    @action(detail=True, methods=['post'])
    def add_copies(self, request, pk=None):
        book = self.get_object()
        count = request.data.get('count', 1)

        # Валидация
        if not isinstance(count, int) or count < 1:
            return Response(
                {"error": "count должен быть целым числом ≥ 1"},
                status=400
            )

        # Создаём экземпляры
        for i in range(count):
            BookInstance.objects.create(
                book=book,
                copy_id=f"{book.isbn}-{i + 1}" if book.isbn else f"COPY-{book.id}-{i + 1}",
                status="available"
            )

        # Перезагружаем book из БД, чтобы сбросить кэш related_manager
        book.refresh_from_db()

        # Обновляем счётчики (теперь book.instances «видит» новые экземпляры)
        book.update_copies_count()

        return Response({
            "status": "copies added",
            "total": book.total_copies,
            "available": book.available_copies
        })

    def get_queryset(self):
        """
        Возвращает все книги.
        Админы видят всё; обычные пользователи — тоже (по условию).
        Если нужно ограничить видимость — переопределите логику.
        """
        return Book.objects.select_related(
            'genre', 'created_by'
        ).prefetch_related('author')

    def perform_create(self, serializer):
        """
        При создании автоматически привязываем книгу к текущему пользователю.
        В модели Book есть поле `created_by` (ForeignKey на User).
        """
        try:
            serializer.save(created_by=self.request.user)
        except ValidationError as e:
            raise ValidationError(e.detail)

    def perform_update(self, serializer):
        """
        При обновлении:
        - Проверки уже выполнены в IsOwnerOrAdmin.
        - Автоматически пересчитываются счётчики экземпляров.
        """
        serializer.save()

    def perform_destroy(self, instance):
        """
        Перед удалением:
        1. Проверяем, есть ли выданные экземпляры.
        2. Проверки прав уже выполнены в IsOwnerOrAdmin.
        """
        if instance.available_copies != instance.total_copies:
            raise PermissionDenied(
                "Нельзя удалить книгу, пока есть выданные или зарезервированные экземпляры."
            )
        instance.delete()



class PublicBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Публичный API для просмотра книг (только list и retrieve).
    Без прав на изменение.
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['author', 'genre', 'publication_year', 'language']
    search_fields = ['title', 'author__full_name', 'genre__name', 'description']
    ordering_fields = ['title', 'publication_year', 'author__full_name']
    ordering = ['title']

    def retrieve(self, request, *args, **kwargs):
        """
        Можно добавить дополнительную логику при получении книги.
        Например, подсчёт просмотров.
        """
        # Пример: увеличить счётчик просмотров (если есть поле `views_count` в модели)
        # instance = self.get_object()
        # instance.views_count += 1
        # instance.save(update_fields=['views_count'])
        return super().retrieve(request, *args, **kwargs)


class BookInstanceViewSet(viewsets.ModelViewSet):
    """
    API для управления экземплярами книг:
    - Получение списка экземпляров (с фильтрацией по книге, статусу, заёмщику).
    - Выдача/возврат книги (изменение status и borrower).
    - Права: только авторизованные пользователи.
    """
    queryset = BookInstance.objects.select_related('book', 'borrower')
    serializer_class = BookInstanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['book', 'status', 'borrower']
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        # Дополнительно можно ограничить видимость (например, только свои выданные книги)
        return super().get_queryset()

    def perform_update(self, serializer):
        # Валидация: нельзя выдать книгу, если она уже выдана
        instance = serializer.instance
        new_status = serializer.validated_data.get('status')

        if instance.status == 'loaned' and new_status != 'loaned':
            # Если книга была выдана и статус меняется — разрешаем (возврат)
            pass
        elif instance.status != 'loaned' and new_status == 'loaned':
            # Если книга не выдана, но её пытаются выдать — проверяем наличие borrower
            if not serializer.validated_data.get('borrower'):
                raise ValidationError({"borrower": "Поле обязательно при выдаче книги."})

        serializer.save()