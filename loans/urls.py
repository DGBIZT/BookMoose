from django.urls import include, path
from rest_framework.routers import DefaultRouter

from loans.apps import LoansConfig

from .views import BookLoanViewSet

router = DefaultRouter()
router.register(r"loans", BookLoanViewSet, basename="loans")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = LoansConfig.name
