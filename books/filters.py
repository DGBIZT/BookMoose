from django_filters import CharFilter, FilterSet
from django_filters import rest_framework as filters

from authors.models import Author

from .models import Book


class BookFilter(FilterSet):
    # M2M-поля
    author = filters.ModelMultipleChoiceFilter(
        field_name="author", queryset=Author.objects.all(), lookup_expr="exact", to_field_name="id", label="Автор"
    )
    genre = CharFilter(field_name="genre__id", lookup_expr="exact", label="Жанр")
    # publisher = CharFilter(field_name='publisher__id', lookup_expr='exact', label='Издательство')
    # series = CharFilter(field_name='series__id', lookup_expr='exact', label='Серия')

    # Числовые диапазоны
    publication_year = filters.RangeFilter(label="Год издания (диапазон)")
    available_copies = filters.NumberFilter(lookup_expr="gte", label="Доступно ≥")
    total_copies = filters.NumberFilter(lookup_expr="lte", label="Всего ≤")

    # Поиск по подстроке
    title = CharFilter(lookup_expr="icontains", label="Название")
    isbn = CharFilter(lookup_expr="icontains", label="ISBN")
    description = CharFilter(lookup_expr="icontains", label="Описание")

    class Meta:
        model = Book
        fields = [
            "author",
            "genre",
            # 'publisher',
            # 'series',
            "publication_year",
            "available_copies",
            "total_copies",
            "title",
            "isbn",
            "description",
        ]


# Константы для search/ordering
BOOK_SEARCH_FIELDS = [
    "title",
    "author__last_name",
    "author__first_name",
    "author__middle_name",
    "genre__name",
    # 'publisher__name',
    # 'series__name',
    "isbn",
    "description",
]

BOOK_ORDERING_FIELDS = [
    "title",
    "publication_year",
    "author__last_name",
    "author__first_name",
    "author__middle_name",
    "genre__name",
    "available_copies",
    "created_at",
    "updated_at",
]
