from rest_framework import permissions


class GenrePermission(permissions.BasePermission):
    """
    Права для модели Genre:
    - GET/HEAD/OPTIONS: доступно всем (даже неаутентифицированным)
    - CREATE: только аутентифицированные пользователи
    - UPDATE/DELETE: только автор записи ИЛИ админ
    """

    def has_permission(self, request, view):
        # GET, HEAD, OPTIONS — разрешаем всем
        if request.method in permissions.SAFE_METHODS:
            return True

        # CREATE — только аутентифицированные
        if request.method == "POST":
            return request.user and request.user.is_authenticated

        # UPDATE/DELETE — проверяем на уровне объекта (в has_object_permission)
        return True

    def has_object_permission(self, request, view, obj):
        # Для безопасных методов — разрешаем всем
        if request.method in permissions.SAFE_METHODS:
            return True

        # Для UPDATE/DELETE:
        # 1. Если пользователь — админ, разрешаем всё
        if request.user and request.user.is_staff:
            return True

        # 2. Иначе — только если пользователь является автором записи
        return obj.created_by == request.user
