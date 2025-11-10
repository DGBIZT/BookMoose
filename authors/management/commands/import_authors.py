import sys
from datetime import date, datetime

import openpyxl
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from authors.models import Author

User = get_user_model()


class Command(BaseCommand):
    help = "Импортирует авторов из Excel‑файла (.xlsx)"

    def add_arguments(self, parser):
        parser.add_argument("excel_file", type=str, help="Путь к Excel‑файлу (.xlsx) с авторами")
        parser.add_argument(
            "--user-id", type=int, default=1, help="ID пользователя, который создаст записи (created_by)"
        )

    def handle(self, *args, **options):
        excel_file = options["excel_file"]
        user_id = options["user_id"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Ошибка: Пользователь с ID={user_id} не найден."))
            sys.exit(1)

        try:
            workbook = openpyxl.load_workbook(excel_file, read_only=True)
            sheet = workbook.active

            if sheet.max_row < 2:
                self.stderr.write(self.style.ERROR("Ошибка: Файл пуст или нет данных."))
                sys.exit(1)

            # Читаем заголовки (первая строка)
            headers = []
            for cell in sheet[1]:
                headers.append((cell.value or "").strip())

            # Определяем индексы нужных колонок
            required_fields = ["last_name", "first_name"]
            optional_fields = ["middle_name", "birth_date", "death_date", "biography"]

            col_indices = {}
            missing_required = []

            for field in required_fields + optional_fields:
                try:
                    col_indices[field] = headers.index(field)
                except ValueError:
                    if field in required_fields:
                        missing_required.append(field)

            if missing_required:
                self.stderr.write(
                    self.style.ERROR(f"Ошибка: Не найдены обязательные поля: {', '.join(missing_required)}")
                )
                sys.exit(1)

            created_count = 0
            updated_count = 0
            error_count = 0

            # Обрабатываем строки (начиная со 2-й)
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
                # Пропускаем полностью пустые строки
                if self.is_row_empty(row):
                    continue

                try:
                    # Извлекаем и приводим к строке, фильтруем 'unset'/'null'
                    last_name = self.clean_string(row[col_indices["last_name"]].value)
                    first_name = self.clean_string(row[col_indices["first_name"]].value)

                    middle_name = (
                        self.clean_string(row[col_indices.get("middle_name")].value)
                        if "middle_name" in col_indices
                        else None
                    )
                    biography = (
                        self.clean_string(row[col_indices.get("biography")].value)
                        if "biography" in col_indices
                        else None
                    )

                    # Обработка дат
                    birth_date = None
                    death_date = None

                    if "birth_date" in col_indices and row[col_indices["birth_date"]].value:
                        try:
                            birth_date = self.parse_date(row[col_indices["birth_date"]].value)
                        except ValueError:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Строка {row_idx}: некорректная дата рождения "
                                    f"'{row[col_indices['birth_date']].value}'. Пропущено."
                                )
                            )
                            continue

                    if "death_date" in col_indices and row[col_indices["death_date"]].value:
                        try:
                            death_date = self.parse_date(row[col_indices["death_date"]].value)
                        except ValueError:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Строка {row_idx}: некорректная дата смерти "
                                    f"'{row[col_indices['death_date']].value}'. Пропущено."
                                )
                            )
                            continue

                    # Валидация обязательных полей
                    if not last_name:
                        self.stderr.write(
                            self.style.WARNING(f"Строка {row_idx}: пропущена — отсутствует фамилия (last_name).")
                        )
                        error_count += 1
                        continue

                    if not first_name:
                        self.stderr.write(
                            self.style.WARNING(f"Строка {row_idx}: пропущена — отсутствует имя (first_name).")
                        )
                        error_count += 1
                        continue

                    # Создание/обновление автора
                    author, created = Author.objects.update_or_create(
                        last_name=last_name,
                        first_name=first_name,
                        defaults={
                            "middle_name": middle_name,
                            "birth_date": birth_date,
                            "death_date": death_date,
                            "biography": biography,
                            "created_by": user,
                        },
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Создан: {author.get_full_name()}"))
                        created_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"Обновлён: {author.get_full_name()}"))
                        updated_count += 1

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Ошибка в строке {row_idx}: {e}"))
                    error_count += 1
                    continue

            # Итоговый отчёт
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nИмпорт завершён:\n"
                    f"  Создано: {created_count}\n"
                    f"  Обновлено: {updated_count}\n"
                    f"  Ошибок: {error_count}"
                )
            )

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Ошибка: Файл '{excel_file}' не найден."))
            sys.exit(1)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Неожиданная ошибка: {e}"))
            sys.exit(1)

    def parse_date(self, value):
        """
        Преобразует значение в дату. Поддерживает:
        - datetime.date
        - datetime.datetime
        - строку в формате YYYY-MM-DD или DD.MM.YYYY
        - игнорирует 'unset', 'null', пустые значения
        """
        if not value or str(value).strip().lower() in ("unset", "null", ""):
            return None

        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            value = value.strip()
            # Формат YYYY-MM-DD
            if "-" in value:
                return datetime.strptime(value, "%Y-%m-%d").date()
            # Формат DD.MM.YYYY
            elif "." in value:
                return datetime.strptime(value, "%d.%m.%Y").date()

        raise ValueError(f"Не удаётся распознать дату: {value}")

    def clean_string(self, value):
        """Очищает строку от 'unset', 'null' и приводит к None, если пусто."""
        if not value or str(value).strip().lower() in ("unset", "null", ""):
            return None
        return str(value).strip()

    def is_row_empty(self, row):
        """
        Проверяет, является ли строка полностью пустой (все ячейки None/пустые строки/'unset'/'null').
        row — объект openpyxl Row (кортеж ячеек).
        """
        for cell in row:
            value = cell.value
            if value is not None:
                value_str = str(value).strip().lower()
                if value_str not in ("", "unset", "null"):
                    return False  # Найдена непустая ячейка
        return True  # Все ячейки пустые/null/unset
