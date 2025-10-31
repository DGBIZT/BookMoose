from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Book
from .serializers import BookSerializer
from .paginators import CustomPagination
from .permissions import IsOwnerOrAdmin
from .filters import BookFilter, BOOK_SEARCH_FIELDS, BOOK_ORDERING_FIELDS



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

    def get_queryset(self):
        """
        Возвращает все книги.
        Админы видят всё; обычные пользователи — тоже (по условию).
        Если нужно ограничить видимость — переопределите логику.
        """
        return Book.objects.all()

    def perform_create(self, serializer):
        """
        При создании автоматически привязываем книгу к текущему пользователю.
        Предполагаем, что в модели Book есть поле `author` (ForeignKey на User).
        """
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """
        При обновлении:
        - Проверки уже выполнены в IsOwnerOrAdmin.
        - Можно добавить логирование.
        """
        serializer.save()

    def perform_destroy(self, instance):
        """
        Перед удалением:
        1. Проверяем, есть ли выданные экземпляры.
        2. Проверки прав уже выполнены в IsOwnerOrAdmin.
        """
        if instance.available_copies < instance.total_copies:
            raise PermissionDenied(
                "Нельзя удалить книгу, пока есть выданные экземпляры."
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
