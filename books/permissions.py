from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает:
    - Чтение (list/retrieve) — всем пользователям.
    - Создание (create) — авторизованным пользователям (книга привязывается к создателю).
    - Обновление (update/partial_update) и удаление (destroy) —
      только владельцу книги (поле `created_by`) ИЛИ администратору (is_staff).
    """

    def has_permission(self, request, view):
        # Чтение разрешено всем (включая неавторизованных)
        if view.action in ["list", "retrieve"]:
            return True

        # Создание разрешено только авторизованным пользователям
        if view.action == "create":
            return request.user.is_authenticated

        # Для update/partial_update/destroy проверка переносится в has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        # Админы имеют полный доступ к любым объектам
        if request.user.is_staff:
            return True

        # Для обычных пользователей: доступ только к своим объектам (created_by == user)
        if hasattr(obj, "created_by") and obj.created_by == request.user:
            return True

        # В остальных случаях — запрет
        return False
