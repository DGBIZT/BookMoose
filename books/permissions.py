from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает:
    - Чтение (list/retrieve) — всем.
    - Создание — всем пользователям (создают свои книги).
    - Обновление/удаление — только владельцу книги ИЛИ админу.
    """

    def has_permission(self, request, view):
        # Чтение разрешено всем
        if view.action in ['list', 'retrieve']:
            return True

        # Создание разрешено всем авторизованным пользователям
        if view.action == 'create':
            return request.user and request.user.is_authenticated

        # Для update/partial_update/destroy нужна дополнительная проверка в has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        # Админы могут всё
        if request.user.is_staff:
            return True

        # Обычные пользователи — только свои книги
        return obj.created_by == request.user   # Предполагаем, что у Book есть поле author=User

