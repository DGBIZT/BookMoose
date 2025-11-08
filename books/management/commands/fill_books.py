import os
from datetime import datetime

from django.core.management import BaseCommand
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from books.models import Book, BookInstance
from authors.models import Author
from genres.models import Genre
import openpyxl
import xlrd

User = get_user_model()



class Command(BaseCommand):
    help = 'Заполняет базу данных книгами и их экземплярами из Excel-файла'


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
                    self.stderr.write(self.style.ERROR('Нет суперпользователей в БД. Создайте пользователя.'))
                    return
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Пользователь с ID {user_id} не найден.'))
            return

        self.user = user
        self.stdout.write(self.style.SUCCESS(f'Начнём заполнение. Пользователь: {user.email}'))

        created_books = 0
        updated_books = 0
        created_instances = 0
        errors = []

        # Читаем Excel-файл
        data = self.read_excel(file_path, errors)
        if not data:
            return

        for row in data:
            try:
                # Получаем авторов
                authors = self.get_authors(row.get('author'))
                if not authors:
                    self.stderr.write(self.style.WARNING(
                        f'Нет авторов для книги "{row.get("title", "без названия")}". Пропускаем.'
                    ))
                    continue

                # Ищем книгу по title + isbn
                book_query = Book.objects.filter(title=row['title'])
                if row.get('isbn'):
                    book_query = book_query.filter(isbn=row['isbn'])

                book = book_query.first()

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

                    if row.get('genre'):
                        genre = self.get_genre(row['genre'])
                        if genre:
                            book.genre = genre

                    try:
                        book.full_clean()
                        book.save()
                        book.author.set(authors)
                        created_books += 1
                        self.stdout.write(self.style.SUCCESS(f'Создана книга: {book.title}'))
                    except ValidationError as e:
                        errors.append(f'Ошибка валидации при создании книги "{row["title"]}": {e}')
                        continue
                    except Exception as e:
                        errors.append(f'Ошибка при сохранении книги "{row["title"]}": {e}')
                        continue
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
                        if genre:
                            book.genre = genre

                    try:
                        book.full_clean()
                        book.save()
                        book.author.set(authors)
                        updated_books += 1
                        self.stdout.write(self.style.SUCCESS(f'Обновлена книга: {book.title}'))
                    except ValidationError as e:
                        errors.append(f'Ошибка валидации при обновлении книги "{row["title"]}": {e}')
                        continue
                    except Exception as e:
                        errors.append(f'Ошибка при обновлении книги "{row["title"]}": {e}')
                        continue

                # Создаём экземпляры книги (BookInstance)
                if 'copy_id' in row and row['copy_id']:
                    copy_ids = [cid.strip() for cid in str(row['copy_id']).split(',') if cid.strip()]
                    for copy_id in copy_ids:
                        try:
                            # Проверяем, не существует ли уже такой экземпляр у этой книги
                            if BookInstance.objects.filter(book=book, copy_id=copy_id).exists():
                                self.stderr.write(self.style.WARNING(
                                    f'Экземпляр с copy_id="{copy_id}" для книги "{book.title}" уже существует. Пропускаем.'
                                ))
                                continue

                            instance = BookInstance(
                                    book=book,
                                    copy_id=copy_id,
                                    status=row.get('status', 'available'),
                                    acquisition_date=row.get('acquisition_date'),
                                    borrower=None  # По умолчанию — не выдан
                            )
                            instance.full_clean()  # Валидация
                            instance.save()
                            created_instances += 1
                            self.stdout.write(self.style.SUCCESS(
                                f'Создан экземпляр: {copy_id} (книга: {book.title})'
                            ))
                        except ValidationError as e:
                            errors.append(
                                f'Ошибка валидации экземпляра "{copy_id}" книги "{book.title}": {e}'
                            )
                        except Exception as e:
                            errors.append(
                                f'Ошибка при создании экземпляра "{copy_id}" книги "{book.title}": {e}'
                            )

            except Exception as e:
                errors.append(f'Неожиданная ошибка для {row.get("title", "без названия")}: {e}')

        # Вывод итогов
        self.stdout.write(self.style.SUCCESS(
            f'\nГотово!\n'
            f'Создано книг: {created_books}\n'
            f'Обновлено книг: {updated_books}\n'
            f'Создано экземпляров: {created_instances}'
        ))
        if errors:
            self.stderr.write(self.style.ERROR('Ошибки:'))
            for error in errors:
                self.stderr.write(self.style.ERROR(f'  • {error}'))

    def read_excel(self, file_path, errors):
        """Читает Excel-файл и возвращает список строк с полностью заполненными полями."""
        try:
            if file_path.endswith('.xlsx'):
                workbook = openpyxl.load_workbook(file_path, read_only=True)
                sheet = workbook.active
                headers = [cell.value for cell in sheet[1]]
                data = []

                for row_idx in range(2, sheet.max_row + 1):
                    row_values = [
                        sheet.cell(row=row_idx, column=col).value
                        for col in range(1, len(headers) + 1)
                    ]
                    row_dict = {headers[i]: row_values[i] for i in range(len(headers))}

                    # Пропускаем полностью пустые строки
                    if not any(v is not None and str(v).strip() != '' for v in row_values):
                        continue

                    # Проверяем обязательные поля
                    missing_fields = []
                    required_fields = ['title', 'author', 'publication_year', 'pages']
                    for field in required_fields:
                        if field not in row_dict or row_dict[field] is None or str(row_dict[field]).strip() == '':
                            missing_fields.append(field)

                    if missing_fields:
                        self.stderr.write(self.style.WARNING(
                            f'Строка {row_idx}: пропущена из‑за незаполненных полей: {", ".join(missing_fields)}'
                        ))
                        continue

                    # Нормализуем типы данных
                    if 'publication_year' in row_dict:
                        try:
                            row_dict['publication_year'] = int(row_dict['publication_year'])
                        except (ValueError, TypeError):
                            errors.append(f'Некорректный год издания в строке {row_idx}')
                            continue

                    if 'pages' in row_dict:
                        try:
                            row_dict['pages'] = int(row_dict['pages'])
                        except (ValueError, TypeError):
                            errors.append(f'Некорректное количество страниц в строке {row_idx}')
                            continue

                    if 'total_copies' in row_dict and row_dict['total_copies']:
                        try:
                            row_dict['total_copies'] = int(row_dict['total_copies'])
                        except (ValueError, TypeError):
                            row_dict['total_copies'] = 1

                    if 'available_copies' in row_dict and row_dict['available_copies']:
                        try:
                            row_dict['available_copies'] = int(row_dict['available_copies'])
                        except (ValueError, TypeError):
                            row_dict['available_copies'] = row_dict.get('total_copies', 1)

                    if 'acquisition_date' in row_dict and row_dict['acquisition_date']:
                        if isinstance(row_dict['acquisition_date'], str):
                            try:
                                row_dict['acquisition_date'] = datetime.strptime(
                                    row_dict['acquisition_date'], '%Y-%m-%d'
                                ).date()
                            except ValueError:
                                row_dict['acquisition_date'] = None
                        elif hasattr(row_dict['acquisition_date'], 'date'):
                            row_dict['acquisition_date'] = row_dict['acquisition_date'].date()

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

                    # Пропускаем полностью пустые строки
                    if not any(v is not None and str(v).strip() != '' for v in row_values):
                        continue

                    # Проверяем обязательные поля
                    missing_fields = []
                    required_fields = ['title', 'author', 'publication_year', 'pages']
                    for field in required_fields:
                        if field not in row_dict or row_dict[field] is None or str(row_dict[field]).strip() == '':
                            missing_fields.append(field)

                    if missing_fields:
                        self.stderr.write(self.style.WARNING(
                            f'Строка {row_idx + 1}: пропущена из‑за незаполненных полей: {", ".join(missing_fields)}'
                        ))
                        continue

                    # Нормализуем типы данных (аналогично XLSX)
                    if 'publication_year' in row_dict:
                        try:
                            row_dict['publication_year'] = int(row_dict['publication_year'])
                        except (ValueError, TypeError):
                            errors.append(f'Некорректный год издания в строке {row_idx + 1}')
                            continue

                    if 'pages' in row_dict:
                        try:
                            row_dict['pages'] = int(row_dict['pages'])
                        except (ValueError, TypeError):
                            errors.append(f'Некорректное количество страниц в строке {row_idx + 1}')
                            continue

                    if 'total_copies' in row_dict and row_dict['total_copies']:
                        try:
                            row_dict['total_copies'] = int(row_dict['total_copies'])
                        except (ValueError, TypeError):
                            row_dict['total_copies'] = 1

                    if 'available_copies' in row_dict and row_dict['available_copies']:
                        try:
                            row_dict['available_copies'] = int(row_dict['available_copies'])
                        except (ValueError, TypeError):
                            row_dict['available_copies'] = row_dict.get('total_copies', 1)

                    if 'acquisition_date' in row_dict and row_dict['acquisition_date']:
                        if isinstance(row_dict['acquisition_date'], str):
                            try:
                                row_dict['acquisition_date'] = datetime.strptime(
                                    row_dict['acquisition_date'], '%Y-%m-%d'
                                ).date()
                            except ValueError:
                                row_dict['acquisition_date'] = None

                    data.append(row_dict)
                return data
            else:
                raise ValueError("Поддерживаются только файлы XLSX и XLS")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ошибка при чтении Excel-файла: {e}'))
            return []

    def get_authors(self, author_str):
        """Разбирает строку с именами авторов и возвращает список экземпляров Author."""
        if not author_str or not str(author_str).strip():
            self.stderr.write(self.style.WARNING('Поле "author" пустое или отсутствует. Пропускаем.'))
            return []

        author_names = [name.strip() for name in str(author_str).split(',') if name.strip()]
        authors = []

        for name in author_names:
            parts = name.split()
            if len(parts) < 2:
                self.stderr.write(self.style.WARNING(f'Некорректное имя автора: "{name}". Пропускаем.'))
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
                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f'Создан автор: {author.get_full_name()}'
                    ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Ошибка при создании автора "{name}": {e}'))
                continue

            return authors

    def get_genre(self, genre_name):
        """Находит или создаёт жанр по названию и возвращает экземпляр Genre."""
        if not genre_name or not str(genre_name).strip():
            return None

        name = str(genre_name).strip().lower().capitalize()
        try:
            genre, created = Genre.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'Создан жанр: {name}'
                ))
            return genre
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Ошибка при создании жанра "{name}": {e}'
            ))
            return None
