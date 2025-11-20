from django.contrib import admin

from .models import BookLoan


@admin.register(BookLoan)
class BookLoanAdmin(admin.ModelAdmin):
    list_display = [
        "book_instance",  # Было: 'book' → теперь корректно
        "user",
        "loan_date",
        "return_date",
        "is_returned",
        "due_date",
    ]
    list_filter = ["is_returned", "loan_date", "due_date", "user"]
    search_fields = ["book_instance__copy_id", "user__username", "notes"]
    readonly_fields = ["loan_date", "return_date"]
