from django.db import models
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

User = get_user_model() # Возвращает CustomUser


class Author(models.Model):
    # Фамилия (обязательно)
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия',
        help_text='Фамилия автора',
        validators=[MinLengthValidator(2)]
    )

    # Имя (обязательно)
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя',
        help_text='Имя автора',
        validators=[MinLengthValidator(2)]
    )

    # Отчество (необязательно)
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Отчество',
        help_text='Отчество автора (если есть)'
    )

    # Дата рождения (необязательно)
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Дата рождения',
        help_text='Дата рождения автора'
    )

    # Дата смерти (необязательно, для умерших авторов)
    death_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Дата смерти',
        help_text='Дата смерти автора (если применимо)'
    )

    # Биография (необязательно)
    biography = models.TextField(
        blank=True,
        null=True,
        verbose_name='Биография',
        help_text='Краткая биография автора'
    )

    # URL фото автора (необязательно)
    photo_url = models.ImageField(
        blank=True,
        null=True,
        verbose_name='Фото автора',
        validators = [FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])]
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Создал запись',
        help_text='Пользователь, создавший автора'
    )

    class Meta:
        verbose_name = 'Автор'
        verbose_name_plural = 'Авторы'
        ordering = ['last_name', 'first_name']  # Сортировка по фамилии и имени
        indexes = [
            models.Index(fields=['last_name']),
            models.Index(fields=['first_name']),
        ]

    def __str__(self):
        # Формируем полное имя: Фамилия Имя Отчество
        if self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        return f"{self.last_name} {self.first_name}"

    def get_full_name(self):
        """Возвращает полное имя автора"""
        return self.__str__()

    def get_short_name(self):
        """Возвращает имя и фамилию (без отчества)"""
        return f"{self.first_name} {self.last_name}"
