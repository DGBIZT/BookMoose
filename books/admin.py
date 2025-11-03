from django.contrib import admin
from .models import Book
from django.contrib.auth import get_user_model

User = get_user_model() # Возвращает CustomUser


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    # Основные настройки отображения
    list_display = (
        'title',
        'genre',
        'author',
        'created_by',
        'publication_year',
        'pages',
        'available_copies',
        'total_copies',
        'created_at',
        'updated_at'
    )
    list_display_links = ('title',)  # По клику — переход к редактированию
    ordering = ('title',)  # Сортировка по умолчанию

    # Фильтры в правой панели
    list_filter = (
        'publication_year',
        'language',
        'created_at',
        'updated_at',
        'created_by'
    )

    # Поле поиска
    search_fields = (
        'title',
        'isbn',
        'description',
        'language'
    )

    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основные данные', {
            'fields': (
                'title',
                'genre',
                'author',
                'created_by',
                'isbn',
                'publication_year',
                'pages',
                'language'
            )
        }),
        ('Доступность', {
            'fields': (
                'available_copies',
                'total_copies'
            )
        }),
        ('Дополнительно', {
            'fields': (
                'edition',
                'description',
                'cover_image'
            ),
            'classes': ('collapse',)  # Сворачиваемая группа
        }),
        ('Автоматические поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Эти поля обновляются автоматически.'
        })
    )

    # Поля, которые нельзя редактировать в админке
    readonly_fields = ('created_at', 'updated_at')

    # Визуальные улучшения
    save_on_top = True  # Кнопки сохранения вверху и внизу
    save_as = True  # Опция «Сохранить как новый»
    list_per_page = 25  # Количество объектов на странице

    # Кастомное действие: обнулить доступные копии
    actions = ['reset_available_copies']

    def reset_available_copies(self, request, queryset):
        updated = queryset.update(available_copies=0)
        self.message_user(
            request,
            f'Количество доступных копий обнулено для {updated} книг.'
        )

    reset_available_copies.short_description = (
        'Обнулить количество доступных копий'
    )

    # Оптимизация запросов (избегаем N+1)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('created_by')  # Подгружаем User сразу

    # Кастомизация формы (опционально)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Если понадобится фильтровать ForeignKey-поля
        if db_field.name == "created_by":
            # Например, показывать только активных пользователей
            kwargs["queryset"] = User.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
