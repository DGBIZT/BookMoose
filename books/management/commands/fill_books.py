import os
from datetime import datetime

from django.core.management import BaseCommand
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from books.models import Book
from authors.models import Author
from genres.models import Genre
import openpyxl
import xlrd

User = get_user_model()


class Command(BaseCommand):
    help = 'Заполняет базу данных книгами из Excel-файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Путь к Excel-файлу (XLSX или XLS)'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='ID пользователя (created_by). Если не указан — берётся первый суперпользователь.'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        user_id = options['user_id']

        # Получаем пользователя
        try:
            if user_id:
                user = User.objects.get(id=user_id)
            else:
                user = User.objects.filter(is_staff=True).first()
                if not user:
                    self.stderr.write('Нет суперпользователей в БД. Создайте пользователя.')
                    return
        except User.DoesNotExist:
            self.stderr.write(f'Пользователь с ID {user_id} не найден.')
            return

        self.user = user  # Сохраняем для доступа в методах
        self.stdout.write(f'Начнём заполнение. Пользователь: {user.email}')

        created_count = 0
        updated_count = 0
        errors = []

        # Читаем Excel-файл
        data = self.read_excel(file_path)
        if not data:
            return

        for row in data:
            try:
                # Получаем авторов (с защитой от None)
                authors = self.get_authors(row.get('author'))
                if not authors:
                    self.stderr.write(f'Нет авторов для книги "{row.get("title", "без названия")}". Пропускаем.')
                    continue

                # Ищем книгу по title + isbn + авторы
                book = Book.objects.filter(
                    title=row['title'],
                    isbn=row.get('isbn'),
                    author__in=authors
                ).first()

                if not book:
                    # Создаём новую книгу
                    book = Book(
                        title=row['title'],
                        publication_year=row['publication_year'],
                        pages=row['pages'],
                        language=row.get('language', 'русский'),
                        description=row.get('description', ''),
                        edition=row.get('edition', ''),
                        total_copies=row.get('total_copies', 1),
                        available_copies=row.get('available_copies', row.get('total_copies', 1)),
                        created_by=user,
                        isbn=row.get('isbn', None)
                    )

                    # Устанавливаем жанр, если указан
                    if row.get('genre'):
                        genre = self.get_genre(row['genre'])
                        book.genre = genre

                    book.full_clean()
                    book.save()
                    book.author.set(authors)
                    created_count += 1
                else:
                    # Обновляем существующую книгу
                    book.publication_year = row['publication_year']
                    book.pages = row['pages']
                    book.language = row.get('language', 'русский')
                    book.description = row.get('description', '')
                    book.edition = row.get('edition', '')
                    book.total_copies = row.get('total_copies', book.total_copies)
                    book.available_copies = row.get('available_copies', book.available_copies)

                    if row.get('genre'):
                        genre = self.get_genre(row['genre'])
                        book.genre = genre

                    book.save()
                    updated_count += 1

            except ValidationError as e:
                errors.append(f'Ошибка валидации для {row.get("title", "без названия")}: {e}')
            except Exception as e:
                errors.append(f'Ошибка для {row.get("title", "без названия")}: {e}')

        # Вывод итогов
        self.stdout.write(self.style.SUCCESS(
            f'Готово! Создано: {created_count}, обновлено: {updated_count}'
        ))
        if errors:
            self.stderr.write('Ошибки:')
            for error in errors:
                self.stderr.write(error)

    def read_excel(self, file_path):
        """Читает Excel-файл и возвращает список строк с полностью заполненными полями."""
        try:
            if file_path.endswith('.xlsx'):
                workbook = openpyxl.load_workbook(file_path, read_only=True)
                sheet = workbook.active
                headers = [cell.value for cell in sheet[1]]
                data = []

                for row_idx in range(2, sheet.max_row + 1):
                    row_values = [sheet.cell(row=row_idx, column=col).value for col in range(1, len(headers) + 1)]

                    # Создаём словарь для текущей строки
                    row_dict = {headers[i]: row_values[i] for i in range(len(headers))}

                    # Проверяем, что строка не полностью пустая
                    if not any(v is not None and str(v).strip() != '' for v in row_values):
                        continue  # Пропускаем полностью пустые строки

                    # Проверяем заполнение всех обязательных полей
                    missing_fields = []
                    for field in ['title', 'author', 'isbn', 'publication_year', 'genre', 'pages']:
                        if field not in row_dict:
                            missing_fields.append(field)
                        else:
                            value = row_dict[field]
                            if value is None or str(value).strip() == '':
                                missing_fields.append(field)

                    if missing_fields:
                        self.stderr.write(
                            f'Строка {row_idx}: пропущена из-за незаполненных полей: {", ".join(missing_fields)}'
                        )
                        continue  # Пропускаем строку с неполными данными

                    data.append(row_dict)
                return data

            elif file_path.endswith('.xls'):
                workbook = xlrd.open_workbook(file_path)
                sheet = workbook.sheet_by_index(0)
                headers = sheet.row_values(0)
                data = []

                for row_idx in range(1, sheet.nrows):
                    row_values = sheet.row_values(row_idx)
                    row_dict = {headers[i]: row_values[i] for i in range(len(headers))}

                    # Проверяем, что строка не полностью пустая
                    if not any(v is not None and str(v).strip() != '' for v in row_values):
                        continue

                    # Проверяем заполнение обязательных полей
                    missing_fields = []
                    for field in ['title', 'author', 'isbn', 'publication_year', 'genre', 'pages']:
                        if field not in row_dict:
                            missing_fields.append(field)
                        else:
                            value = row_dict[field]
                            if value is None or str(value).strip() == '':
                                missing_fields.append(field)

                    if missing_fields:
                        self.stderr.write(
                            f'Строка {row_idx + 1}: пропущена из-за незаполненных полей: {", ".join(missing_fields)}'
                        )
                        continue

                    data.append(row_dict)
                return data
            else:
                raise ValueError("Поддерживаются только файлы XLSX и XLS")

        except Exception as e:
            self.stderr.write(f'Ошибка при чтении Excel-файла: {e}')
            return []

    def get_authors(self, author_str):
        """Разбирает строку с именами авторов и возвращает список экземпляров Author."""
        if author_str is None:
            self.stderr.write('Поле "author" равно None. Пропускаем.')
            return []

        author_str = str(author_str).strip()
        if not author_str:
            self.stderr.write('Поле "author" пустое после очистки. Пропускаем.')
            return []

        authors = []
        author_names = [name.strip() for name in author_str.split(',') if name.strip()]

        for name in author_names:
            parts = name.split()
            if len(parts) < 2:
                self.stderr.write(f'Некорректное имя автора: "{name}". Пропускаем.')
                continue

            last_name = parts[0]
            first_name = parts[1]
            middle_name = ' '.join(parts[2:]) if len(parts) > 2 else ''

            try:
                author, created = Author.objects.get_or_create(
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name or None,
                    created_by=self.user
                )
                authors.append(author)
            except Exception as e:
                self.stderr.write(f'Ошибка при создании автора "{name}": {e}')
                continue

            return authors

    def get_genre(self, genre_name):
        """Находит или создаёт жанр по названию и возвращает экземпляр Genre."""
        if not genre_name or not str(genre_name).strip():
            return None  # Если имя пустое или None — возвращаем None

        name = str(genre_name).strip().lower().capitalize()  # Нормализация регистра
        try:
            genre, _ = Genre.objects.get_or_create(name=name)
            return genre
        except Exception as e:
            self.stderr.write(f'Ошибка при создании жанра "{name}": {e}')
            return None
