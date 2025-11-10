from django.urls import include, path
from rest_framework.routers import DefaultRouter

from authors.apps import AuthorsConfig

from .views import AuthorViewSet

router = DefaultRouter()
router.register(r"authors", AuthorViewSet, basename="author")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = AuthorsConfig.name
