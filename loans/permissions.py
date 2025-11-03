from rest_framework import permissions

class BookLoanPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # GET — всем, POST/PUT/DELETE — только staff
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return request.user and request.user.is_staff
        return True

    def has_object_permission(self, request, view, obj):
        # Для detail-действий: staff или владелец записи
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return (
                request.user and request.user.is_staff or
                obj.created_by == request.user
            )
        return True
