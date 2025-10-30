from django.urls import path
from users.views import (
    UserCreateAPIView,
    UserRetrieveAPIView,
    UserUpdateAPIView,
    UserDestroyAPIView,
)
from users.apps import UsersConfig
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = UsersConfig.name

urlpatterns = [
    path("register/", UserCreateAPIView.as_view(), name="register"),
    path('login/', TokenObtainPairView.as_view(permission_classes=(AllowAny,)), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(permission_classes=(AllowAny,)), name='token_refresh'),
    path('user/me/', UserRetrieveAPIView.as_view(), name='user-me'),
    path('user/<int:pk>/', UserRetrieveAPIView.as_view(), name='user-detail'),  # Получение информации о себе
    path('user/update/<int:pk>/', UserUpdateAPIView.as_view(), name='user-update'),  # Обновление информации
    path('user/delete/<int:pk>/', UserDestroyAPIView.as_view(), name='user-delete'),  # Удаление аккаунта
]