from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Book
from authors.models import Author
from genres.models import Genre
from .serializers import BookSerializer

User = get_user_model()


class BookModelTest(TestCase):
    """Тесты модели Book."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='pass123',
            email='test@example.com'
        )
        # Создаём автора через корректные поля last_name и first_name
        self.author = Author.objects.create(
            last_name='Иванов',
            first_name='Иван',
            created_by=self.user
        )
        # Создаём жанр С УКАЗАНИЕМ created_by
        self.genre = Genre.objects.create(
            name='Фантастика',
            created_by=self.user  # Обязательно!
        )

    def test_book_creation(self):
        book = Book.objects.create(
            title='Тест-книга',
            publication_year=2020,
            pages=300,
            language='русский',
            created_by=self.user,
            genre=self.genre
        )
        book.author.add(self.author)

        self.assertEqual(book.title, 'Тест-книга')
        self.assertEqual(book.publication_year, 2020)
        self.assertEqual(book.pages, 300)
        self.assertEqual(book.language, 'русский')
        self.assertEqual(book.created_by, self.user)
        self.assertEqual(book.genre, self.genre)
        self.assertIn(self.author, book.author.all())

        # Проверяем строковое представление автора
        self.assertEqual(str(self.author), 'Иванов Иван')  # __str__ → last_name + first_name
        self.assertEqual(self.author.get_short_name(), 'Иван Иванов')

    def test_str_method(self):
        book = Book.objects.create(
            title='Книга 1',
            publication_year=2021,
            pages=300,  # Обязательно!
            language='русский',  # Рекомендуется также указать
            created_by=self.user,
            genre=self.genre  # Если поле genre обязательно
        )
        book.author.add(self.author)
        expected_str = f"Книга 1 (Иван Иванов, 2021)"
        self.assertEqual(str(book), expected_str)

    def test_available_copies_lte_total_copies(self):
        book = Book(
            title='Книга с копиями',
            publication_year=2022,
            pages=200,
            language='русский',
            created_by=self.user,
            total_copies=5,
            available_copies=6  # Нарушение: available > total
        )
        with self.assertRaises(Exception):
            book.save()


class BookSerializerTest(APITestCase):
    """Тесты сериализатора BookSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='author',
            password='pass123',
            email='author@example.com'
        )
        # Создаём автора через last_name и first_name
        self.author = Author.objects.create(
            last_name='Петров',  # Фамилия
            first_name='Алексей',  # Имя
            created_by=self.user  # Обязательное поле!
        )
        self.genre = Genre.objects.create(
            name='Детектив',
            created_by=self.user
        )

    def test_serializer_valid_data(self):
        valid_data = {
            'title': 'Новая книга',
            'publication_year': 2023,
            'pages': 400,
            'language': 'русский',
            'total_copies': 10,
            'genre': self.genre.id,
            'author': [self.author.id],
            'created_by': self.user.id  # Обязательно!
        }
        serializer = BookSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        book = serializer.save()
        self.assertEqual(book.title, 'Новая книга')
        self.assertEqual(book.total_copies, 10)
        self.assertEqual(book.available_copies, 0)

    def test_serializer_invalid_available_copies(self):
        data = {
            'title': 'Книга с ошибкой',
            'author': [self.author.id],
            'created_by': self.user.id,
            'publication_year': 2023,
            'pages': 300,
            'language': 'русский',
            'total_copies': 5,
            'available_copies': 10  # available > total
        }
        serializer = BookSerializer(data=data)

        # Проверяем, что данные невалидны
        self.assertFalse(serializer.is_valid(),
                         "Сериализатор должен отвергать данные с available_copies > total_copies")

        # Проверяем наличие ошибки для поля available_copies
        self.assertIn('available_copies', serializer.errors, "Ошибка должна быть в поле 'available_copies'")

        # Дополнительно проверяем текст ошибки (если важно)
        expected_error = 'Количество доступных копий не может превышать общее количество.'
        self.assertIn(
            expected_error,
            serializer.errors['available_copies'],
            f"Ожидалось сообщение: '{expected_error}', но получено: {serializer.errors['available_copies']}"
        )

    def test_serializer_to_representation(self):
        book = Book.objects.create(
            title='Представленная книга',
            publication_year=2024,
            pages=250,
            language='русский',
            created_by=self.user,
            total_copies=8,
            available_copies=3
        )
        book.author.add(self.author)
        serializer = BookSerializer(book)
        data = serializer.data
        self.assertEqual(data['title'], 'Представленная книга')
        self.assertIn('author', data)
        self.assertEqual(len(data['author']), 1)
        self.assertEqual(data['author'][0], str(self.author))




class BookViewSetTest(APITestCase):
    """Тесты API BookViewSet (полный CRUD)."""

    def setUp(self):
        self.client = APIClient()
        # Создаём пользователей
        self.user = User.objects.create_user(
            username='regular',
            password='pass123',
            email='regular@example.com'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@example.com'
        )
        # Создаём данные
        self.author = Author.objects.create(
            last_name='Смирнова',
            first_name='Анна',
            created_by=self.user  # Обязательно укажите created_by (поле NOT NULL)
        )

        self.genre = Genre.objects.create(
            name='Романтика',
            created_by=self.user
        )
        # Авторизуемся как обычный пользователь
        self.client.force_authenticate(user=self.user)

    def test_list_books(self):
        url = reverse('books:book-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_book(self):
        url = reverse('books:book-list')
        data = {
            'title': 'Созданная книга',
            'author': [self.author.id],
            'publication_year': 2025,
            'genre': self.genre.id,
            'pages': 350,
            'language': 'русский',
            'total_copies': 7,
            'available_copies': 7,
            'created_by': self.user.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 1)
        book = Book.objects.first()
        self.assertEqual(book.created_by, self.user)

    def test_update_book(self):
        # Сначала создаём книгу
        book = Book.objects.create(
            title='Старая книга',
            publication_year=2020,
            pages=200,
            language='русский',
            created_by=self.user,
            total_copies=5,
            available_copies=5
        )
        book.author.add(self.author)
        url = reverse('books:book-detail', kwargs={'pk': book.id})
        data = {
            'title': 'Обновлённая книга',
            'author': [self.author.id],
            'publication_year': 2026,
            'pages': 250,
            'language': 'английский',
            'total_copies': 6,
            'available_copies': 6,
            'created_by': self.user.id
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.title, 'Обновлённая книга')
        self.assertEqual(book.language, 'английский')

    def test_delete_book_by_owner(self):
        # Создаём книгу, принадлежащую текущему пользователю
        book = Book.objects.create(
            title='Удаляемая книга',
            publication_year=2020,
            pages=200,
            language='русский',
            created_by=self.user,
            total_copies=3,
            available_copies=3
        )
        book.author.add(self.author)
        url = reverse('books:book-detail', kwargs={'pk': book.id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_delete_book_by_non_owner_fails(self):
        # Создаём книгу, принадлежащую другому пользователю
        other_user = User.objects.create_user(
            username='other',
            password='pass123',
            email='other@example.com'
        )
        book = Book.objects.create(
            title='Книга другого пользователя',
            publication_year=2021,
            pages=250,
            language='русский',
            created_by=other_user,
            total_copies=4,
            available_copies=4
        )
        book.author.add(self.author)
        url = reverse('books:book-detail', kwargs={'pk': book.id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_book_with_issued_copies_fails(self):
        # Создаём книгу с выданными экземплярами (available < total)
        book = Book.objects.create(
            title='Книга с выданными копиями',
            publication_year=2022,
            pages=300,
            language='русский',
            created_by=self.user,
            total_copies=5,
            available_copies=2  # 3 копии выданы
        )
        book.author.add(self.author)
        url = reverse('books:book-detail', kwargs={'pk': book.id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('нельзя удалить книгу, пока есть выданные экземпляры',
                      str(response.data).lower())

    def test_admin_can_delete_any_book(self):
        # Авторизуемся как админ
        self.client.force_authenticate(user=self.admin)

        # Создаём книгу, принадлежащую другому пользователю
        other_user = User.objects.create_user(
            username='owner',
            password='pass123',
            email='owner@example.com'
        )
        book = Book.objects.create(
            title='Книга для удаления админом',
            publication_year=2023,
            pages=400,
            language='русский',
            created_by=other_user,
            total_copies=6,
            available_copies=6
        )
        book.author.add(self.author)
        url = reverse('books:book-detail', kwargs={'pk': book.id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())

class PublicBookViewSetTest(APITestCase):
    """Тесты API PublicBookViewSet (только чтение)."""

    @classmethod
    def setUpTestData(cls):
        # Создаём клиента для API-запросов
        cls.client = APIClient()

        # Создаём пользователя
        cls.user = User.objects.create_user(
            username='regular',
            password='pass123',
            email='regular@example.com'
        )

        # Создаём автора
        cls.author = Author.objects.create(
            first_name='Сергей',
            last_name='Орлов',
            created_by=cls.user
        )

        # Создаём жанр
        cls.genre = Genre.objects.create(
            name='Триллер',
            created_by=cls.user
        )

        # Создаём первую книгу
        cls.book1 = Book.objects.create(
            title='Публичная книга 1',
            publication_year=2024,
            pages=320,
            language='русский',
            created_by=cls.user,
            total_copies=10,
            available_copies=8
        )
        cls.book1.author.add(cls.author)

        # Создаём вторую книгу
        cls.book2 = Book.objects.create(
            title='Публичная книга 2',
            publication_year=2025,
            pages=280,
            language='английский',
            created_by=cls.user,
            total_copies=5,
            available_copies=5
        )
        cls.book2.author.add(cls.author)

    def test_public_list_books(self):
        url = reverse('books:public-book-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_public_retrieve_book(self):
        url = reverse('books:public-book-detail', kwargs={'pk': self.book1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Публичная книга 1')

    def test_public_filter_by_genre(self):
        url = reverse('books:public-book-list') + f'?genre={self.genre.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В данном случае ни одна книга не привязана к жанру, поэтому ожидаем пустой результат
        self.assertEqual(len(response.data['results']), 0)

    def test_public_ordering_by_title(self):
        url = reverse('books:public-book-list') + '?ordering=title'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item['title'] for item in response.data['results']]
        self.assertEqual(titles, sorted(titles))  # Должны быть отсортированы по алфавиту

    def test_public_create_not_allowed(self):
        url = reverse('books:public-book-list')
        data = {
            'title': 'Попытка создания',
            'author': [self.author.id],
            'publication_year': 2026,
            'pages': 300,
            'language': 'русский',
            'total_copies': 4,
            'available_copies': 4
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_public_update_not_allowed(self):
        url = reverse('books:public-book-detail', kwargs={'pk': self.book1.id})
        data = {'title': 'Попытка обновления'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_public_delete_not_allowed(self):
        url = reverse('books:public-book-detail', kwargs={'pk': self.book1.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
