from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GenreViewSet
from genres.apps import GenresConfig  # замените на имя вашего app

router = DefaultRouter()
router.register(r'genres', GenreViewSet, basename='genre')

urlpatterns = [
    path('', include(router.urls)),
]

app_name = GenresConfig.name
