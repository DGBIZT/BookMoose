from django.core.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .filters import BOOK_ORDERING_FIELDS, BOOK_SEARCH_FIELDS, BookFilter
from .models import Book, BookInstance
from .paginators import CustomPagination
from .permissions import IsOwnerOrAdmin
from .serializers import BookInstanceSerializer, BookSerializer


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
    ordering = ["title"]
    permission_classes = [IsOwnerOrAdmin]  # Единое разрешение для всех действий

    @action(detail=True, methods=["post"])
    def add_copies(self, request, pk=None):
        """
        Действие для добавления экземпляров книги (копий).
        Вызывается по POST-запросу к URL: /books/{pk}/add_copies/
        """

        book = self.get_object()

        # Извлекаем параметр 'count' из тела запроса (сколько копий нужно добавить)
        # Если 'count' не передан, используем значение по умолчанию = 1
        count = request.data.get("count", 1)

        if not isinstance(count, int) or count < 1:
            return Response({"error": "count должен быть целым числом ≥ 1"}, status=400)

        # Получаем все существующие copy_id для данной книги из БД
        # Это нужно, чтобы не создать дубликаты copy_id
        existing_ids = set(
            BookInstance.objects.filter(book=book).values_list(  # Фильтруем экземпляры по текущей книге
                "copy_id", flat=True
            )  # Получаем только значения copy_id
        )

        created_count = 0

        # Цикл для создания нужного количества копий (count)
        for i in range(count):
            # Генерируем уникальный copy_id
            attempts = 0  # Счетчик попыток подбора свободного copy_id
            while True:
                if book.isbn:
                    copy_id = f"{book.isbn}-{i + 1 + attempts}"
                else:
                    copy_id = f"COPY-{book.id}-{i + 1 + attempts}"

                if copy_id not in existing_ids:
                    break
                attempts += 1

            # Создаем новый экземпляр книги в БД
            BookInstance.objects.create(
                book=book,
                copy_id=copy_id,
                status="available",
            )
            # Добавляем созданный copy_id в набор существующих, чтобы избежать дубликатов в следующих итерациях
            existing_ids.add(copy_id)
            created_count += 1

        # Обновляем объект книги из БД (сбрасываем кэш, чтобы увидеть новые экземпляры)
        book.refresh_from_db()
        # Пересчитываем количество экземпляров (total_copies и available_copies) для книги
        book.update_copies_count()

        # Возвращаем ответ клиенту
        return Response(
            {
                "status": "copies added",
                "total": book.total_copies,
                "available": book.available_copies,
                "created": created_count,
            }
        )

    def get_queryset(self):
        """
        Возвращает все книги.
        Админы видят всё; обычные пользователи — тоже (по условию).
        Если нужно ограничить видимость — переопределите логику.
        """
        return Book.objects.select_related("genre", "created_by").prefetch_related("author")

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
            raise PermissionDenied("Нельзя удалить книгу, пока есть выданные или зарезервированные экземпляры.")
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
    filterset_fields = ["author", "genre", "publication_year", "language"]
    search_fields = ["title", "author__full_name", "genre__name", "description"]
    ordering_fields = ["title", "publication_year", "author__full_name"]
    ordering = ["title"]

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

    queryset = BookInstance.objects.select_related("book", "borrower")
    serializer_class = BookInstanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["book", "status", "borrower"]
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        # Дополнительно можно ограничить видимость (например, только свои выданные книги)
        return super().get_queryset()

    def perform_update(self, serializer):
        # Валидация: нельзя выдать книгу, если она уже выдана
        instance = serializer.instance
        new_status = serializer.validated_data.get("status")

        if instance.status == "loaned" and new_status != "loaned":
            # Если книга была выдана и статус меняется — разрешаем (возврат)
            pass
        elif instance.status != "loaned" and new_status == "loaned":
            # Если книга не выдана, но её пытаются выдать — проверяем наличие borrower
            if not serializer.validated_data.get("borrower"):
                raise ValidationError({"borrower": "Поле обязательно при выдаче книги."})

        serializer.save()
