from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.serializers import UserSerializer
from users.models import CustomUser
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied


class UserCreateAPIView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    serializer_class = UserSerializer
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserRetrieveAPIView(generics.RetrieveAPIView):
    """Получение информации о пользователе из БД"""
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    queryset = CustomUser.objects.all()

    def get_object(self):
        # Проверяем, какой URL используется
        if self.request.path.endswith('/me/'):
            # Если это /me/, возвращаем текущего пользователя
            return self.request.user
        else:
            # Иначе возвращаем пользователя по ID
            return super().get_object()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Проверяем права доступа
        if not request.path.endswith('/me/') and not request.user.is_superuser:
            if instance != request.user:
                raise PermissionDenied("Доступ запрещен")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserUpdateAPIView(generics.UpdateAPIView):
    """Обновление пользователя"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        obj = super().get_object()
        # Проверка прав доступа
        if not self.request.user.is_superuser and obj != self.request.user:
            raise PermissionDenied("Доступ запрещен")
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Дополнительная проверка прав перед обновлением
        if not request.user.is_superuser and instance != request.user:
            return Response({'detail': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        self.perform_update(serializer)
        return Response(serializer.data)


class UserDestroyAPIView(generics.DestroyAPIView):
    """ Удаление учетной записи пользователя из системы """
    queryset = CustomUser.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        # Получаем ID пользователя из URL
        pk = self.kwargs.get('pk')

        # Если это суперпользователь, он может удалять любого пользователя
        if self.request.user.is_superuser:
            return CustomUser.objects.get(pk=pk)

        # Обычный пользователь может удалять только себя
        if str(self.request.user.pk) == str(pk):
            return self.request.user

        raise PermissionDenied("У вас нет прав на удаление этого пользователя")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
