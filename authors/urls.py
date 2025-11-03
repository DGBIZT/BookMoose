from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthorViewSet
from authors.apps import AuthorsConfig

router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')

urlpatterns = [
    path('', include(router.urls)),
]

app_name = AuthorsConfig.name