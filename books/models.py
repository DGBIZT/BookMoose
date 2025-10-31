from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model() # Возвращает CustomUser


class Book(models.Model):
    # Основные поля
    # Название книги
    title = models.CharField(
        max_length=255,
        verbose_name='Название книги',
        help_text='До 255 символов'
    )
    # # Автор
    # author = models.ForeignKey(
    #     'Author',  # Название модели (можно строку)
    #     on_delete=models.CASCADE,  # Обязательный параметр
    #     verbose_name='Автор',
    #     help_text='ФИО автора'
    # )

    # Пользователь системы, который создал/управляет записью
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Создал запись',
        help_text='Пользователь системы, добавивший книгу'
    )

    # Международный стандартный номер книги
    isbn = models.CharField(
        max_length=17,
        unique=True,
        blank=True,
        null=True,
        verbose_name='ISBN',
        help_text='Международный стандартный номер книги'
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
        validators=[
            MinValueValidator(1450),
            MaxValueValidator(2030)
        ],
        verbose_name='Год издания',
        help_text='Год выпуска (1450–2030)'
    )
    # # Жанр
    # genre = models.ForeignKey(
    #     'Genre',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     verbose_name='Жанр',
    #     help_text='Жанр книги'
    # )
    # Количество страниц
    pages = models.PositiveIntegerField(
        verbose_name='Количество страниц',
        validators=[MinValueValidator(1)]
    )
    # Язык
    language = models.CharField(
        max_length=50,
        default='русский',
        verbose_name='Язык',
        help_text='Язык издания (до 50 символов)'
    )

    # Дополнительные поля
    # Аннотация
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Аннотация',
        help_text='Подробное описание книги'
    )
    # Издание
    edition = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Издание',
        help_text='Номер издания (например, "2‑е изд.")'
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
        default=0,
        verbose_name='Доступных экземпляров',
        help_text='Сколько копий сейчас в наличии'
    )
    # Общее количество копий в фонде
    total_copies = models.PositiveIntegerField(
        default=1,
        verbose_name='Всего экземпляров',
        help_text='Общее количество копий в фонде'
    )
    # URL изображения обложки
    cover_image = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка на обложку',
        help_text='URL изображения обложки'
    )

    # Автоматические поля
    # Создано
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    # Обновлено
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено'
    )

    class Meta:
        verbose_name = 'Книга'
        verbose_name_plural = 'Книги'
        ordering = ['title']
        # indexes = [  Как создам все приложения раскрыть коментарий
        #     models.Index(fields=['title']),
        #     models.Index(fields=['author']),
        #     models.Index(fields=['isbn']),
        # ]

    def __str__(self):
        return f"{self.title} ({self.author}, {self.publication_year})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
