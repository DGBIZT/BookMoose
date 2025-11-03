from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from authors.models import Author
import random
from datetime import date

User = get_user_model()

class Command(BaseCommand):
    help = 'Создаёт тестовые записи авторов в базе данных'

    def handle(self, *args, **options):
        # Получаем первого пользователя для поля created_by
        try:
            user = User.objects.first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('Нет пользователей в базе. Создайте пользователя через админку.')
                )
                return
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Нет пользователей в базе. Создайте пользователя через админку.')
            )
            return

        # Список тестовых данных
        authors_data = [
            {
                'last_name': 'Стругацкий',
                'first_name': 'Аркадий',
                'middle_name': 'Натанович',
                'birth_date': date(1925, 8, 28),
                'death_date': date(1991, 10, 12),
                'biography': 'Русский советский писатель, сценарист, переводчик, создавший в соавторстве с братом Борисом Стругацким несколько десятков произведений, считающихся классикой современной научной и социальной фантастики.',
            },
            {
                'last_name': 'Стругацкий',
                'first_name': 'Борис',
                'middle_name': 'Натанович',
                'birth_date': date(1933, 4, 15),
                'death_date': date(2012, 11, 19),
                'biography': 'Русский советский писатель, сценарист, редактор и переводчик, создавший в соавторстве с братом Аркадием Стругацким несколько десятков произведений, ставших классикой современной научной и социальной фантастики.',
            },
            {
                'last_name': 'Ремарк',
                'first_name': 'Эрих Мария',
                'birth_date': date(1898, 6, 22),
                'death_date': date(1970, 9, 25),
                'biography': 'Немецкий писатель, представитель «потерянного поколения».',
            },
            {
                'last_name': 'Чехов',
                'first_name': 'Антон',
                'middle_name': 'Павлович',
                'birth_date': date(1860, 1, 29),
                'death_date': date(1904, 7, 15),
                'biography': 'Писатель, драматург, врач.',
            },
            {
                'last_name': 'Булгаков',
                'first_name': 'Михаил',
                'middle_name': 'Афанасьевич',
                'birth_date': date(1891, 5, 15),
                'death_date': date(1940, 3, 10),
                'biography': 'Писатель, драматург, театральный режиссёр.',
            },
            {
                'last_name': 'Хорган',
                'first_name': 'Джон',
                'birth_date': date(1974, 10, 19),
                'biography': 'Джон Дж. Хорган (род. в 1974 году) — заслуженный профессор психологии в Университете штата Джорджия в Атланте, штат Джорджия. Он изучает вовлечённость в терроризм и участие в нём, уделяя особое внимание выходу из террористических движений и дерадикализации.',
            },
        ]

        self.stdout.write('Начинаем заполнение авторов...')

        for data in authors_data:
            author, created = Author.objects.get_or_create(
                last_name=data['last_name'],
                first_name=data['first_name'],
                defaults={
                    'middle_name': data.get('middle_name'),
                    'birth_date': data.get('birth_date'),
                    'death_date': data.get('death_date'),
                    'biography': data.get('biography'),
                    'created_by': user,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Создан автор: {author.get_full_name()}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Автор уже существует: {author.get_full_name()}')
                )

        self.stdout.write(self.style.SUCCESS('Заполнение завершено!'))
