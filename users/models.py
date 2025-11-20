from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True, verbose_name="email address")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Номер телефона")
    city = models.CharField(max_length=100, blank=True, verbose_name="Город")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="Аватар")
    is_confirmed = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
