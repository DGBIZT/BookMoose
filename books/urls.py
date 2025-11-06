from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, PublicBookViewSet, BookInstanceViewSet
from books.apps import BooksConfig

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
router.register(r'public-books', PublicBookViewSet, basename='public-book')
router.register(r'instances', BookInstanceViewSet, basename='instance')

urlpatterns = [
    path('', include(router.urls)),
]
app_name = BooksConfig.name