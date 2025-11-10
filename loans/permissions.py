from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class BookLoanPermission(permissions.BasePermission):
    """
    Права доступа для BookLoan:

    - Анонимные пользователи: запрещены все действия.
    - Обычные пользователи (не staff):
      - GET: только свои выдачи (где user == request.user)
      - PATCH: только свои выдачи, можно менять notes/due_date
      - Остальные методы: запрещены
    - Staff (библиотекари):
      - Все действия разрешены
    """

    def has_permission(self, request, view):
        # Запрещаем анонимным пользователям
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff — полный доступ
        if request.user.is_staff:
            return True

        # Обычные пользователи — только GET и PATCH
        if request.method in ["GET", "PATCH"]:
            return True

        # Остальные методы (POST, PUT, DELETE) — запрещены
        return False

    def has_object_permission(self, request, view, obj):
        # Staff — всегда разрешено
        if request.user.is_staff:
            return True

        # Обычные пользователи:
        # - GET: если obj.user == request.user
        # - PATCH: если obj.user == request.user и меняются только разрешённые поля
        if request.method == "GET":
            return obj.user == request.user

        if request.method == "PATCH":
            # Проверяем, что пользователь меняет только разрешённые поля
            allowed_fields = {"notes", "due_date"}
            requested_fields = set(request.data.keys())
            if not requested_fields.issubset(allowed_fields):
                raise PermissionDenied("Вы можете изменять только поля: notes, due_date.")
            return obj.user == request.user

        # Все остальные методы (PUT, DELETE, POST) — запрещены для не-staff
        return False
