from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookLoanViewSet
from loans.apps import LoansConfig

router = DefaultRouter()
router.register(r'loans', BookLoanViewSet, basename='loans')

urlpatterns = [
    path('', include(router.urls)),
]

app_name = LoansConfig.name
