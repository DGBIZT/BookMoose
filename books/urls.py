from django.urls import include, path
from rest_framework.routers import DefaultRouter

from books.apps import BooksConfig

from .views import BookInstanceViewSet, BookViewSet, PublicBookViewSet

router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")
router.register(r"public-books", PublicBookViewSet, basename="public-book")
router.register(r"instances", BookInstanceViewSet, basename="instance")

urlpatterns = [
    path("", include(router.urls)),
]
app_name = BooksConfig.name
