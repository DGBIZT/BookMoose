from django.contrib import admin

from .models import CustomUser


@admin.register(CustomUser)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("username", "first_name", "last_name", "email", "phone_number")
    list_filter = ("username", "first_name", "last_name", "email", "phone_number")
    search_fields = ("email", "phone_number")
