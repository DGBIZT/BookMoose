from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django.http import QueryDict


from authors.models import Author
from genres.models import Genre
from .models import Book, BookInstance
from .serializers import BookSerializer, BookInstanceSerializer
from .views import BookViewSet


User = get_user_model()



# 1. Тесты моделей
class BookModelTest(TestCase):
    def setUp(self):
        # Создаём пользователя-автора книги
        self.user = User.objects.create_user(
            username='testuser',
            password='pass123'
        )

        # Создаём автора (с обязательными полями last_name и first_name)
        self.author = Author.objects.create(
            last_name='Тестов',
            first_name='Иван',
            created_by=self.user  # обязательное поле created_by
        )

    def test_book_creation(self):
        # Создаём книгу
        book = Book.objects.create(
            title='Тест-книга',
            created_by=self.user,
            publication_year=2020,
            pages=300,
            language='русский'
        )

        # Добавляем автора к книге (через ManyToMany)
        book.author.add(self.author)

        # Проверяем основные поля
        self.assertEqual(book.title, 'Тест-книга')
        self.assertEqual(book.publication_year, 2020)
        self.assertEqual(book.pages, 300)
        self.assertEqual(book.language, 'русский')

        # Проверяем связь с автором
        self.assertEqual(book.author.count(), 1)
        self.assertEqual(book.author.first().last_name, 'Тестов')
        self.assertEqual(book.author.first().first_name, 'Иван')

        # Проверяем __str__ у книги (должно быть: "Название (Авторы, Год)")
        self.assertEqual(
            str(book),
            'Тест-книга (Иван Тестов, 2020)'
        )

    def test_isbn_unique(self):
        Book.objects.create(
            title='Книга 1',
            created_by=self.user,
            isbn='123-456-789',
            publication_year=2020,
            pages=100
        )
        with self.assertRaises(ValidationError):
            book2 = Book(
                title='Книга 2',
                created_by=self.user,
                isbn='123-456-789',  # Дубликат
                publication_year=2021,
                pages=150
            )
            book2.full_clean()

    def test_publication_year_range(self):
        with self.assertRaises(ValidationError):
            book = Book(
                title='Старая книга',
                created_by=self.user,
                publication_year=1400,  # < 1450
                pages=100
            )
            book.full_clean()

        with self.assertRaises(ValidationError):
            book = Book(
                title='Будущая книга',
                created_by=self.user,
                publication_year=3000,  # > 2030
                pages=100
            )
            book.full_clean()



class BookInstanceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.book = Book.objects.create(
            title='Основная книга',
            created_by=self.user,
            publication_year=2020,
            pages=200
        )

    def test_instance_creation(self):
        instance = BookInstance.objects.create(
            book=self.book,
            copy_id='COPY-001',
            status='available'
        )
        self.assertEqual(instance.copy_id, 'COPY-001')
        self.assertEqual(instance.status, 'available')
        self.assertEqual(str(instance), 'COPY-001 (Основная книга) — available')

    def test_copy_id_uniqueness(self):
        BookInstance.objects.create(book=self.book, copy_id='COPY-001', status='available')
        with self.assertRaises(ValidationError):
            instance2 = BookInstance(book=self.book, copy_id='COPY-001', status='loaned')
            instance2.full_clean()


# 2. Тесты сериализаторов
class BookSerializerTest(APITestCase):
    def setUp(self):

        # Создаём пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        # Создаём автора с реальными полями модели Author
        self.author = Author.objects.create(
            last_name='Сериализатор',
            first_name='Автор',
            created_by=User.objects.create_user(
                username='serializer_test_user',
                password='testpass'
            )
        )

        # Создаём книгу
        self.book = Book.objects.create(
            title='Сериализуемая книга',
            publication_year=2021,
            pages=400,
            created_by=self.author.created_by  # связываем с тем же пользователем
        )

        # Добавляем автора к книге
        self.book.author.add(self.author)

    def test_serializer_data(self):
        serializer = BookSerializer(self.book)
        data = serializer.data

        # Проверяем основные поля книги
        self.assertEqual(data['title'], 'Сериализуемая книга')
        self.assertEqual(data['publication_year'], 2021)
        self.assertEqual(data['pages'], 400)

        # Проверяем поле author
        expected_author_str = f"{self.author.last_name} {self.author.first_name}"
        self.assertIn(expected_author_str, data['author'])

        # Проверяем cover_image_url: поле должно присутствовать, но может быть None
        self.assertIn('cover_image_url', data)
        self.assertIsInstance(data['cover_image_url'], (str, type(None)))

        # Дополнительно: если нужно проверить формат URL при наличии
        if data['cover_image_url'] is not None:
            self.assertTrue(data['cover_image_url'].startswith('/'))

    def test_serializer_valid_data(self):
        data = {
            'title': 'Новая книга',
            'author': [self.author.id],
            'publication_year': 2022,
            'pages': 250,
            'language': 'русский',
            'total_copies': 10,
        }
        serializer = BookSerializer(data=data)
        # Выводим ошибки, если валидация не прошла
        if not serializer.is_valid():
            print("Ошибки валидации:", serializer.errors)

        self.assertTrue(serializer.is_valid())

    def test_serializer_invalid_data(self):
        data = {
            'title': '',
            'publication_year': 1000,
            'pages': -1
        }
        serializer = BookSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn('publication_year', serializer.errors)
        self.assertIn('pages', serializer.errors)



class BookInstanceSerializerTest(APITestCase):
    def setUp(self):
        # Создаём пользователя (если ещё не создан)
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        # Создаём автора (если нужен для теста)
        self.author = Author.objects.create(
            last_name='Тестов',
            first_name='Иван',
            created_by=self.user
        )

        # Создаём книгу — теперь с created_by
        self.book = Book.objects.create(
            title='Книга для экземпляра',
            publication_year=2020,
            pages=100,
            created_by=self.user  # ← добавляем обязательное поле
        )

        # Если нужно связать автора с книгой
        self.book.author.add(self.author)

    def test_instance_serializer(self):
        instance = BookInstance.objects.create(book=self.book, copy_id='TEST-001', status='reserved')
        serializer = BookInstanceSerializer(instance)
        data = serializer.data
        self.assertEqual(data['copy_id'], 'TEST-001')
        self.assertEqual(data['status'], 'reserved')



# 3. Тесты viewsets
class BookViewSetTest(APITestCase):
    def setUp(self):
        # Создаём суперпользователя (с email, как мы исправили ранее)
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass',
            email='admin@example.com'
        )

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='testuser@example.com'
        )

        # Создаём автора — используем реальные поля модели Author
        self.author = Author.objects.create(
            first_name='Тест',  # ← имя
            last_name='Автор',  # ← фамилия
            created_by=self.admin,  # ← если есть поле created_by (обязательно!)

        )

        # Если нужно создать книгу (для теста)
        self.book = Book.objects.create(
            title='Тестовая книга',
            publication_year=2023,
            pages=300,
            created_by=self.user,
            language='русский',

        )
        self.book.author.add(self.author)

    def test_list_books(self):
        response = self.client.get(reverse('books:book-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_create_book_as_author(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Новая книга',
            'author': [self.author.id],
            'publication_year': 2023,
            'pages': 300,
            'language': 'русский',
            'total_copies': 10,
        }
        response = self.client.post(reverse('books:book-list'), data, format='json')

        # Выводим ошибки, если статус не 201
        if response.status_code != status.HTTP_201_CREATED:
            print("Статус:", response.status_code)
            print("Ошибки:", response.data)  # Вот здесь ключ к проблеме!

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Новая книга')

    def test_update_book_by_owner(self):
        self.client.force_authenticate(user=self.user)
        data = {'title': 'Обновлённая книга'}
        response = self.client.patch(reverse('books:book-detail', kwargs={'pk': self.book.pk}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Обновлённая книга')

    def test_update_book_by_non_owner(self):
        non_owner = User.objects.create_user(username='nonowner', password='pass123')
        self.client.force_authenticate(user=non_owner)
        data = {'title': 'Попытка изменения'}
        response = self.client.patch(
            reverse('books:book-detail', kwargs={'pk': self.book.pk}),
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_book_by_admin(self):
        self.client.force_authenticate(user=self.admin)
        data = {'title': 'Изменено админом'}
        response = self.client.patch(
            reverse('books:book-detail', kwargs={'pk': self.book.pk}),
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Изменено админом')

    def test_delete_book_by_owner(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('books:book-detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_book_with_loaned_copies(self):
        # Создаём экземпляр в статусе "выдано"
        BookInstance.objects.create(
            book=self.book,
            copy_id='LOANED-001',
            status='loaned'
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('books:book-detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('нельзя удалить книгу', response.data['detail'].lower())

    def test_add_copies_action(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('books:book-add-copies', kwargs={'pk': self.book.pk})
        data = {'count': 3}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Перезагружаем книгу из БД, чтобы получить актуальные значения
        self.book.refresh_from_db()

        self.assertEqual(response.data['total'], self.book.total_copies)
        self.assertEqual(response.data['available'], self.book.available_copies)
        self.assertEqual(
            BookInstance.objects.filter(book=self.book).count(),
            3
        )

    def test_add_copies_invalid_count(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('books:book-add-copies', kwargs={'pk': self.book.pk})
        data = {'count': 0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('count должен быть целым числом ≥ 1', response.data['error'])

    def test_retrieve_book(self):
        # Аутентифицируем клиента
        self.client.force_authenticate(user=self.user)

        # Выполняем GET-запрос
        response = self.client.get(
            reverse('books:book-detail', kwargs={'pk': self.book.pk})
        )

        # Проверяем статус
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем данные
        self.assertEqual(response.data['title'], self.book.title)

    def test_filter_books_by_author(self):
        query_dict = QueryDict(mutable=True)
        query_dict.setlist('author', [str(self.author.id)])  # ← список строк
        response = self.client.get(
            reverse('books:book-list'),
            query_dict
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item['title'] for item in response.data['results']]
        self.assertIn(self.book.title, titles)

    def test_search_books_by_title(self):
        response = self.client.get(
            reverse('books:book-list'),
            {'search': 'Тестовая'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn('results', response.data)
        titles = [item['title'] for item in response.data['results']]
        self.assertIn(self.book.title, titles)


# 4. Тесты PublicBookViewSet (только чтение)
class PublicBookViewSetTest(APITestCase):
    def setUp(self):
        # Создаём тестового пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='12345',
            email='testuser@example.com'
        )

        # Создаём книгу, указывая created_by
        self.book = Book.objects.create(
            title='Публичная книга',
            publication_year=2021,
            pages=150,
            created_by=self.user  # Обязательное поле!
        )

    def test_public_list(self):
        response = self.client.get(reverse('books:public-book-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что книга есть в результатах
        titles = [item['title'] for item in response.data['results']]
        self.assertIn('Публичная книга', titles)

    def test_public_retrieve(self):
        response = self.client.get(reverse('books:public-book-detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Публичная книга')

    def test_public_create_forbidden(self):
        data = {'title': 'Новая публичная книга', 'publication_year': 2022, 'pages': 100}
        response = self.client.post(reverse('books:public-book-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

# 5. Тесты BookInstanceViewSet
class BookInstanceViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='borrower', password='pass123', email='borrower@example.com', is_staff=True)
        self.book = Book.objects.create(
            title='Книга для экземпляра',
            publication_year=2020,
            pages=100,
            created_by=self.user
        )
        self.instance = BookInstance.objects.create(
            book=self.book,
            copy_id='INSTANCE-001',
            status='available'
        )

    def test_list_instances(self):
        response = self.client.get(reverse('books:instance-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        copy_ids = [item['copy_id'] for item in response.data]
        self.assertIn('INSTANCE-001', copy_ids)

    def test_update_instance_status(self):
        self.client.force_authenticate(user=self.user)
        data = {'status': 'loaned', 'borrower': self.user.id}
        response = self.client.patch(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk}),
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'loaned')

    def test_update_instance_without_borrower(self):
        self.client.force_authenticate(user=self.user)
        data = {'status': 'loaned'}  # Нет borrower
        response = self.client.patch(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk}),
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('borrower', response.data)

    def test_retrieve_instance(self):
        # Аутентифицируем клиента
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['copy_id'], 'INSTANCE-001')

    def test_filter_instances_by_book(self):
        response = self.client.get(
            reverse('books:instance-list'),
            {'book': self.book.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        copy_ids = [item['copy_id'] for item in response.data]
        self.assertIn('INSTANCE-001', copy_ids)

    def test_filter_instances_by_status(self):
        response = self.client.get(
            reverse('books:instance-list'),
            {'status': 'available'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = [item['status'] for item in response.data]
        self.assertTrue(all(status == 'available' for status in statuses))

    def test_filter_instances_by_borrower(self):
        # Сначала выдаём экземпляр пользователю
        self.instance.borrower = self.user
        self.instance.status = 'loaned'
        self.instance.save()

        response = self.client.get(
            reverse('books:instance-list'),
            {'borrower': self.user.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['copy_id'], 'INSTANCE-001')

    def test_create_instance_as_staff_success(self):
        """
        Тест: админ может создать экземпляр книги.
        Ожидаем: статус 201, корректный copy_id и связь с книгой.
        """
        self.client.force_authenticate(user=self.user)  # user.is_staff == True

        data = {
            'book': self.book.pk,
            'copy_id': 'NEW-001',
            'status': 'available'
        }

        response = self.client.post(
            reverse('books:instance-list'),
            data,
            format='json'
        )

        # Проверяем статус
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем данные в ответе
        self.assertEqual(response.data['copy_id'], 'NEW-001')
        self.assertEqual(response.data['status'], 'available')
        self.assertEqual(response.data['book'], self.book.pk)

        # Проверяем, что объект действительно создан в БД
        instance = BookInstance.objects.get(copy_id='NEW-001')
        self.assertEqual(instance.book, self.book)
        self.assertEqual(instance.status, 'available')

    def test_invalid_status_transition(self):
        self.client.force_authenticate(user=self.user)
        data = {'status': 'invalid_status'}
        response = self.client.patch(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk}),
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверяем, что ошибка относится к полю status
        self.assertIn('status', response.data)
        # Проверяем код ошибки
        self.assertIn('invalid_choice', str(response.data['status']))

    def test_update_instance_retains_copy_id(self):
        self.client.force_authenticate(user=self.user)
        data = {'status': 'reserved'}
        response = self.client.patch(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk}),
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['copy_id'], 'INSTANCE-001')  # copy_id не должен меняться

    def test_acquisition_date_can_be_null(self):
        # Аутентифицируем клиента
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk})
        )

        # Проверяем статус
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Должен возвращаться 200 OK для авторизованного пользователя"
        )

        # Проверяем, что acquisition_date == null
        self.assertIsNone(
            response.data['acquisition_date'],
            "acquisition_date должен быть null по умолчанию"
        )

    def test_partial_update_without_status(self):
        self.client.force_authenticate(user=self.user)
        data = {'borrower': self.user.pk}  # Только borrower, без статуса
        response = self.client.patch(
            reverse('books:instance-detail', kwargs={'pk': self.instance.pk}),
            data,
            format='json'
        )
        # Должно пройти, если статус уже корректный
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        # Если статус 'available', то назначение borrower без смены статуса — ошибка
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertIn('borrower', response.data)

# 6. Вспомогательные тесты (опционально)
class UtilityTests(TestCase):
    def test_book_str_method(self):
        user = User.objects.create_user(username='test', password='pass')
        book = Book.objects.create(
            title='Название',
            created_by=user,
            publication_year=2000,
            pages=100
        )
        self.assertEqual(str(book), 'Название (Нет авторов, 2000)')

    def test_bookinstance_str_method(self):
        # Создаём пользователя (как в test_book_str_method)
        user = User.objects.create_user(username='testuser', password='pass123')

        # Создаём книгу с указанием created_by
        book = Book.objects.create(
            title='Книга',
            publication_year=2020,
            pages=50,
            created_by=user  # ← Обязательно!
        )

        # Создаём экземпляр книги
        instance = BookInstance.objects.create(
            book=book,
            copy_id='ID-123',
            status='damaged'
        )

        # Проверяем __str__
        self.assertEqual(str(instance), 'ID-123 (Книга) — damaged')

    def test_book_update_copies_count(self):
        user = User.objects.create_user(username='owner', password='pass')
        book = Book.objects.create(
            title='Счётчик',
            created_by=user,
            publication_year=2021,
            pages=200
        )
        # Создаём 2 экземпляра
        BookInstance.objects.create(book=book, copy_id='C1', status='available')
        BookInstance.objects.create(book=book, copy_id='C2', status='loaned')

        book.update_copies_count()
        self.assertEqual(book.total_copies, 2)
        self.assertEqual(book.available_copies, 1)  # Только 'available' считается доступным

    def test_bookinstance_set_status(self):
        # Создаём пользователя
        user = User.objects.create_user(username='testuser', password='pass123')

        # Создаём книгу с указанием created_by
        book = Book.objects.create(
            title='Тест',
            publication_year=2022,
            pages=100,
            created_by=user  # ← Обязательно!
        )

        # Создаём экземпляр книги
        instance = BookInstance.objects.create(
            book=book,
            copy_id='TEST-01',
            status='available'
        )

        # Тестируем метод set_status
        instance.set_status('reserved')
        self.assertEqual(instance.status, 'reserved')

        # Проверяем обработку недопустимого статуса
        with self.assertRaises(ValidationError):
            instance.set_status('invalid_status')

