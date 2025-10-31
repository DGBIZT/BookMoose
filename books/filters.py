from django_filters import rest_framework as filters
from .models import Book


class BookFilter(filters.FilterSet):
    # Точные совпадения
    author = filters.CharFilter(field_name='author__id', lookup_expr='exact')
    genre = filters.CharFilter(field_name='genre__id', lookup_expr='exact')
    publisher = filters.CharFilter(field_name='publisher__id', lookup_expr='exact')
    series = filters.CharFilter(field_name='series__id', lookup_expr='exact')

    # Числовые диапазоны
    publication_year = filters.RangeFilter()
    available_copies = filters.NumberFilter()
    total_copies = filters.NumberFilter()

    # Поиск по подстроке
    title = filters.CharFilter(lookup_expr='icontains')
    isbn = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Book
        fields = []


# search_fields и ordering_fields можно оставить в виде констант
BOOK_SEARCH_FIELDS = [
    'title',
    'author__full_name',
    'genre__name',
    'publisher__name',
    'series__name',
    'isbn',
    'description',
]

BOOK_ORDERING_FIELDS = [
    'title',
    'publication_year',
    'author__full_name',
    'genre__name',
    'available_copies',
    'created_at',
    'updated_at',
]
