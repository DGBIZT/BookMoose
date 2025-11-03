from django.contrib import admin
from .models import Author



@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    # Поля, отображаемые в списке записей
    list_display = (
        'last_name',
        'first_name',
        'middle_name',
        'get_short_name',
        'birth_date',
        'death_date',
        'created_by',
    )

    # Поля, по которым можно искать
    search_fields = (
        'last_name',
        'first_name',
        'middle_name',
    )

    # Фильтры в правой панели
    list_filter = (
        'birth_date',
        'death_date',
        'created_by',
    )

    # Поля, доступные для редактирования в списке (опционально)
    list_editable = ()

    # Группы полей в форме редактирования
    fieldsets = (
        ('Основные данные', {
            'fields': ('last_name', 'first_name', 'middle_name')
        }),
        ('Даты жизни', {
            'fields': ('birth_date', 'death_date'),
            'classes': ('collapse',),  # Сворачиваемая группа
        }),
        ('Биография', {
            'fields': ('biography',),
            'classes': ('collapse',),
        }),
        ('Фото', {
            'fields': ('photo_url',),
            'classes': ('collapse',),
        }),
        ('Метаданные', {
            'fields': ('created_by',),
            'classes': ('collapse',),
        }),
    )


    # Порядок сортировки в списке
    ordering = ('last_name', 'first_name')

    # Количество записей на странице
    list_per_page = 20

    def get_queryset(self, request):
        """Оптимизируем запросы к БД"""
        qs = super().get_queryset(request)
        return qs.select_related('created_by')  # Избегаем N+1 для created_by

    def has_delete_permission(self, request, obj=None):
        """Можно настроить права на удаление"""
        return True  # По умолчанию разрешено

    def has_change_permission(self, request, obj=None):
        """Можно настроить права на изменение"""
        return True  # По умолчанию разрешено

