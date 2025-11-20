from django.core.management import BaseCommand

from users.models import CustomUser


class Command(BaseCommand):

    def handle(self, *args, **options):
        user = CustomUser.objects.create(email="admin@go.pro", username="admin")
        user.is_staff = True
        user.is_active = True
        user.is_superuser = True
        user.set_password("1234")
        user.save()
