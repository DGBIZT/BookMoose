from django.contrib import admin

from .models import Genre


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    # Поля, отображаемые в списке записей
    list_display = [
        "name",
        "parent",
        "order",
        "is_active",
        "created_by",
        "has_subgenres",
        "full_path",
    ]

    # Поля, по которым можно фильтровать в правой панели
    list_filter = [
        "is_active",
        "parent",
        "created_by",
    ]

    # Поле для поиска (по названию жанра)
    search_fields = ["name", "description"]

    # Поля, доступные для редактирования в списке (без открытия полной формы)
    list_editable = ["order", "is_active"]

    # Группировка полей в форме редактирования
    fieldsets = (
        (None, {"fields": ("name", "description", "parent")}),
        (
            "Сортировка и статус",
            {
                "fields": ("order", "is_active"),
                "classes": ("collapse",),  # Сворачиваемая группа
            },
        ),
        (
            "Метаданные",
            {
                "fields": ("created_by",),
                "classes": ("collapse", "readonly"),
            },
        ),
    )

    # Только для чтения (не редактируются в админке)
    readonly_fields = ["created_by"]

    # Порядок сортировки в списке
    ordering = ["order", "name"]

    # Количество элементов на странице пагинации
    list_per_page = 50

    # Показать «Сохранить/Удалить» вверху формы
    save_on_top = True

    # Автозаполнение поля parent (удобно при большом числе жанров)
    autocomplete_fields = ["parent"]

    def has_subgenres(self, obj):
        """Столбец «Есть поджанры?» в списке."""
        return obj.has_subgenres

    has_subgenres.boolean = True
    has_subgenres.short_description = "Есть поджанры"

    def full_path(self, obj):
        """Столбец с полным путём иерархии."""
        return obj.get_full_path()

    full_path.short_description = "Полный путь"

    def get_queryset(self, request):
        """Добавляем select_related для оптимизации запросов."""
        qs = super().get_queryset(request)
        return qs.select_related("parent", "created_by")

    def save_model(self, request, obj, form, change):
        """
        Автоматически устанавливаем created_by при создании.
        При редактировании поле не меняется.
        """
        if not change:  # Если это создание новой записи
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_changeform_initial_data(self, request):
        """
        Начальные значения при создании новой записи.
        Например, автоматически активируем жанр.
        """
        return {"is_active": True}
