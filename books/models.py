from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()


class Book(models.Model):
    # Основные поля
    # Название книги
    title = models.CharField(max_length=255, verbose_name="Название книги", help_text="До 255 символов")
    # Автор
    author = models.ManyToManyField(
        "authors.Author",
        verbose_name="Авторы",
        help_text="ФИО автора или список авторов книги",
        related_name="books",  # Позволяет: author.books.all()
    )

    # Пользователь системы, который создал/управляет записью
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Создал запись",
        help_text="Пользователь системы, добавивший книгу",
    )

    # Международный стандартный номер книги
    isbn = models.CharField(
        max_length=17,
        unique=True,  # Гарантирует отсутствие дублей
        blank=True,
        null=True,
        verbose_name="ISBN",
        help_text="Международный стандартный номер книги",
    )
    # # Издательство книги
    # publisher = models.ForeignKey(
    #     'Publisher',
    #     on_delete=models.SET_NULL,  # Если издательство удалено — ставим NULL
    #     blank=True,
    #     null=True,
    #     verbose_name='Издательство',
    #     help_text='Издательство книги'
    # )
    # Год издания
    publication_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1450), MaxValueValidator(2030)],
        verbose_name="Год издания",
        help_text="Год выпуска (1450–2030)",
    )
    # Жанр
    genre = models.ForeignKey(
        "genres.Genre", on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Жанр", help_text="Жанр книги"
    )

    # Количество страниц
    pages = models.PositiveIntegerField(verbose_name="Количество страниц", validators=[MinValueValidator(1)])
    # Язык
    language = models.CharField(
        max_length=50, default="русский", verbose_name="Язык", help_text="Язык издания (до 50 символов)"
    )

    # Дополнительные поля
    # Аннотация
    description = models.TextField(
        blank=True, null=True, verbose_name="Аннотация", help_text="Подробное описание книги"
    )
    # Издание
    edition = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Издание", help_text='Номер издания (например, "2‑е изд.")'
    )
    # # Серия
    # series = models.ForeignKey(
    #     'Series',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     verbose_name='Серия',
    #     help_text='Серия, к которой относится книга'
    # )
    # Сколько копий сейчас в наличии
    available_copies = models.PositiveIntegerField(
        default=0, verbose_name="Доступных экземпляров", help_text="Сколько копий сейчас в наличии"
    )
    # Общее количество копий в фонде
    total_copies = models.PositiveIntegerField(
        default=1, verbose_name="Всего экземпляров", help_text="Общее количество копий в фонде"
    )
    # URL изображения обложки
    cover_image = models.ImageField(
        blank=True,
        null=True,
        verbose_name="Обложка",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "gif"])],
    )

    # Автоматические поля
    # Создано
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    # Обновлено
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ["title"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["isbn"]),
        ]

    def __str__(self):
        author_names = ", ".join([author.get_short_name() for author in self.author.all()])
        if not author_names:
            author_names = "Нет авторов"
        return f"{self.title} ({author_names}, {self.publication_year})"

    def clean(self):
        super().clean()

    def update_copies_count(self):
        """Обновляет счётчики экземпляров."""
        self.total_copies = self.instances.count()
        self.available_copies = self.instances.filter(status="available").count()
        self.save(update_fields=["total_copies", "available_copies"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # После сохранения обновляем счётчики (если это новое создание)
        if not kwargs.get("update_fields"):
            self.update_copies_count()


class BookInstance(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        verbose_name="Книга",
        help_text="Ссылка на основную запись книги",
        related_name="instances",
    )
    copy_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="ID экземпляра",
        help_text='Уникальный идентификатор экземпляра (например, "GP-001")',
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("available", "Доступно"),
            ("loaned", "Выдано"),
            ("reserved", "Зарезервировано"),
            ("damaged", "Повреждено"),
            ("lost", "Утеряно"),
        ],
        default="available",
        verbose_name="Статус",
        help_text="Текущий статус экземпляра",
    )
    acquisition_date = models.DateField(
        null=True, blank=True, verbose_name="Дата поступления", help_text="Когда экземпляр поступил в фонд"
    )

    borrower = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="borrowed_books", verbose_name="Заёмщик"
    )

    class Meta:
        verbose_name = "Экземпляр книги"
        verbose_name_plural = "Экземпляры книг"
        indexes = [
            models.Index(fields=["copy_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.copy_id} ({self.book.title}) — {self.status}"

    def clean(self):
        super().clean()
        if BookInstance.objects.filter(book=self.book, copy_id=self.copy_id).exclude(pk=self.pk).exists():
            raise ValidationError({"copy_id": "ID экземпляра должен быть уникальным для данной книги."})

    def save(self, *args, **kwargs):
        self.full_clean()  # Вызываем валидацию
        super().save(*args, **kwargs)  # ОБЯЗАТЕЛЬНО: сохраняем объект в БД
        if self.book:
            self.book.update_copies_count()  # Обновляем счётчики книги

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.book:
            self.book.update_copies_count()

    def set_status(self, new_status):
        valid_statuses = [choice[0] for choice in self._meta.get_field("status").choices]
        if new_status not in valid_statuses:
            raise ValidationError(f"Недопустимый статус: {new_status}")

        self.status = new_status
        try:
            self.save()
        except ValidationError as e:
            # Перехватываем ошибки валидации при сохранении
            raise ValidationError(e.error_dict)
