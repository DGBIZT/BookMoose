from rest_framework import permissions
from .models import Author


class AuthorPermission(permissions.BasePermission):
    """
    Разрешения для модели Author:
    - Все авторизованные пользователи могут создавать авторов (POST).
    - Редактировать/удалять (PUT/PATCH/DELETE) можно только своих авторов (созданных текущим пользователем).
    - Админы (is_staff=True) могут делать всё.
    """

    def has_permission(self, request, view):
        # Все авторизованные пользователи могут создавать (POST)
        if request.method == 'POST' and request.user.is_authenticated:
            return True
        # Для остальных методов требуется аутентификация
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Админы могут делать что угодно
        if request.user.is_staff:
            return True

        # Обычные пользователи могут редактировать/удалять только своих авторов
        # Предполагаем, что у Author есть поле created_by (ForeignKey на User)
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user

        return False
