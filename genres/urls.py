from django.urls import include, path
from rest_framework.routers import DefaultRouter

from genres.apps import GenresConfig  # замените на имя вашего app

from .views import GenreViewSet

router = DefaultRouter()
router.register(r"genres", GenreViewSet, basename="genre")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = GenresConfig.name
