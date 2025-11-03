from django.contrib import admin
from .models import BookLoan


@admin.register(BookLoan)
class BookLoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'loan_date', 'return_date', 'is_returned')
    list_filter = ('is_returned', 'loan_date', 'return_date')
    search_fields = ('book__title', 'user__username')
    readonly_fields = ('loan_date',)
