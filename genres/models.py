from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Genre(models.Model):
    """
    Модель жанра литературы.
    Используется для категоризации книг по жанрам.
    """

    # Название жанра (обязательно, уникальное)
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название жанра",
        help_text='Краткое название жанра, например: "Фантастика", "Детектив"',
    )

    # Описание жанра (необязательно)
    description = models.TextField(
        blank=True, null=True, verbose_name="Описание", help_text="Подробное описание особенностей жанра"
    )

    # Родительский жанр (для иерархической структуры, например: "Научная фантастика" → "Фантастика")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subgenres",
        verbose_name="Родительский жанр",
        help_text="Основной жанр, к которому относится данный поджанр",
    )

    # Порядок сортировки (для отображения в списках)
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки",
        help_text="Число для сортировки жанров в списках (меньше число — выше в списке)",
    )

    # Активен ли жанр (для временного скрытия без удаления)
    is_active = models.BooleanField(
        default=True, verbose_name="Активен", help_text="Если снято, жанр не будет отображаться в интерфейсе"
    )

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Создал запись", help_text="Пользователь, создавший автора"
    )

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"
        ordering = ["order", "name"]  # Сначала по порядку, затем по названию
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["is_active"]),
        ]
        # Ограничение на уникальность имени
        constraints = [models.UniqueConstraint(fields=["name"], name="unique_genre_name")]

    def __str__(self):
        """Строковое представление жанра."""
        return self.name

    def save(self, *args, **kwargs):
        """
        Дополнительная логика перед сохранением.
        Например, очистка пробелов в названии.
        """
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    @property
    def has_subgenres(self):
        """Возвращает True, если у жанра есть поджанры."""
        return self.subgenres.exists()

    def get_ancestors(self):
        """
        Возвращает список родительских жанров (иерархия вверх).
        Пример: ['Фантастика', 'Научная фантастика']
        """
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current.name)
            current = current.parent
        return ancestors

    def get_full_path(self):
        """
        Возвращает полный путь жанра в иерархии.
        Пример: "Фантастика → Научная фантастика → Космоопера"
        """
        path = self.get_ancestors()
        path.reverse()
        path.append(self.name)
        return " → ".join(path)
