# your_app/management/commands/import_genres.py
import csv
import sys
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from genres.models import Genre

User = get_user_model()


class Command(BaseCommand):
    help = 'Импортирует жанры из CSV‑файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Путь к CSV‑файлу с жанрами'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=1,
            help='ID пользователя, который создаст жанры (created_by)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        user_id = options['user_id']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stderr.write(f"Ошибка: Пользователь с ID={user_id} не найден.")
            sys.exit(1)

        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:  # -sig для обработки BOM
                reader = csv.DictReader(
                    f,
                    delimiter=';',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL
                )

                print("Поля CSV:", reader.fieldnames)

                for row_num, row in enumerate(reader, start=2):  # начинаем с 2 (1-я строка — заголовки)
                    try:
                        # Очищаем данные от лишних пробелов и спецсимволов
                        name = (row.get('name') or '').strip().replace('\xa0', ' ').strip()
                        description = (row.get('description') or '').strip().replace('\xa0', ' ').strip()
                        parent_name = (row.get('parent') or '').strip().replace('\xa0', ' ').strip()
                        order_str = (row.get('order') or '0').strip().replace('\xa0', ' ').strip()

                        if not name:
                            self.stderr.write(f"Пропущена строка {row_num}: отсутствует поле 'name'.")
                            continue

                        # Проверяем, что order — число
                        if not order_str.isdigit():
                            self.stderr.write(
                                f"Пропущена строка {row_num}: поле 'order' не является числом: {order_str}")
                            continue
                        order = int(order_str)

                        # Ищем родительский жанр по названию
                        parent = None
                        if parent_name:
                            try:
                                parent = Genre.objects.get(name=parent_name)
                            except Genre.DoesNotExist:
                                self.stderr.write(
                                    f"Предупреждение (строка {row_num}): Родительский жанр '{parent_name}' не найден. Будет создан без родителя.")

                        # Создаём или обновляем жанр
                        genre, created = Genre.objects.update_or_create(
                            name=name,
                            defaults={
                                'description': description,
                                'parent': parent,
                                'order': order,
                                'created_by': user,
                            }
                        )

                        if created:
                            self.stdout.write(self.style.SUCCESS(f"Создан жанр: {name}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"Обновлён жанр: {name}"))


                    except Exception as e:
                        self.stderr.write(f"Ошибка в строке {row_num}: {e}")
                        continue

        except FileNotFoundError:
            self.stderr.write(f"Ошибка: Файл '{csv_file}' не найден.")
            sys.exit(1)
        except Exception as e:
            self.stderr.write(f"Неожиданная ошибка: {e}")
            sys.exit(1)
