from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from books.models import BookInstance

User = get_user_model()


class BookLoan(models.Model):
    book_instance = models.ForeignKey(
        BookInstance,
        on_delete=models.CASCADE,
        verbose_name="Экземпляр книги",
        help_text="Какой именно экземпляр выдан",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Читатель", help_text="Кто взял книгу")
    loan_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата выдачи")
    return_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата возврата")
    is_returned = models.BooleanField(default=False, verbose_name="Возвращена", help_text="Отметка о возврате")
    due_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Срок возврата", help_text="Планируемая дата возврата"
    )
    notes = models.TextField(
        blank=True, verbose_name="Примечания", help_text="Дополнительные комментарии (например, повреждения)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans_created",
        verbose_name="Создал запись",
        help_text="Кто оформил выдачу",
    )

    class Meta:
        verbose_name = "Выдача экземпляра"
        verbose_name_plural = "Выдачи экземпляров"
        ordering = ["-loan_date"]
        # Гарантия: один экземпляр не может быть выдан дважды
        constraints = [
            models.UniqueConstraint(
                fields=["book_instance"], name="unique_active_loan", condition=models.Q(is_returned=False)
            )
        ]

    def __str__(self):
        return f"{self.book_instance.copy_id} → {self.user.username} " f"({self.loan_date.strftime('%d.%m.%Y')})"

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем дату возврата при отметке "возвращена"
        if self.is_returned and not self.return_date:
            self.return_date = timezone.now()

        super().save(*args, **kwargs)

        # Синхронизируем статус экземпляра, только если он задан
        if self.book_instance is not None:
            if self.is_returned:
                self.book_instance.status = "available"
            else:
                self.book_instance.status = "loaned"
            self.book_instance.save(update_fields=["status"])
