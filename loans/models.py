from django.db import models
from users.models import CustomUser
from books.models import Book
from django.utils import timezone


class BookLoan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="Книга")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Пользователь")

    loan_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата выдачи")
    return_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата возврата")
    is_returned = models.BooleanField(default=False, verbose_name="Возвращена")
    #  (опционально) — планируемая дата возврата
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Срок возврата")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loans_created',
        verbose_name="Создал"
    )

    class Meta:
        verbose_name = "Выдача книги"
        verbose_name_plural = "Выдачи книг"
        ordering = ['-loan_date']

    def __str__(self):
        return f"{self.book.title} → {self.user.username} ({self.loan_date.date()})"

    def save(self, *args, **kwargs):
        # Если книга отмечается как возвращённая и дата возврата не установлена
        if self.is_returned and not self.return_date:
            self.return_date = timezone.now()  # Текущее время сервера
        super().save(*args, **kwargs)
