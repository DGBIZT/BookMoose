from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from users.models import CustomUser
from books.models import Book
from authors.models import Author
from .models import BookLoan
from .serializers import BookLoanSerializer
from django.utils import timezone
from datetime import timedelta


class BookLoanModelTest(TestCase):
    def setUp(self):
        # Создаём тестовых пользователей
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.staff_user = CustomUser.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        # Создаём автора
        self.author = Author.objects.create(
            last_name='AuthorLastName',
            first_name='AuthorFirstName',
            created_by=self.staff_user  # Обязательное поле
        )

        # Создаём книгу
        self.book = Book.objects.create(
            title='Test Book',
            publication_year=2020,
            pages=300,
            language='русский',
            created_by=self.staff_user,
            total_copies=5,
            available_copies=5
        )
        # Связываем книгу с автором через M2M
        self.book.author.add(self.author)

    def test_create_book_loan(self):
        # Дата возврата: через 30 дней от текущего момента
        due_date = timezone.now() + timedelta(days=30)
        loan = BookLoan.objects.create(
            book=self.book,
            user=self.user,
            due_date=due_date
        )
        self.assertEqual(loan.book.title, 'Test Book')
        self.assertEqual(loan.user.username, 'testuser')
        self.assertFalse(loan.is_returned)
        self.assertIsNone(loan.return_date)


    def test_str_method(self):
        loan = BookLoan.objects.create(
            book=self.book,
            user=self.user
        )
        expected_str = f"{self.book.title} → {self.user.username} ({loan.loan_date.date()})"
        self.assertEqual(str(loan), expected_str)



class BookLoanSerializerTest(TestCase):
    def setUp(self):
        # Создаём пользователя
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

        # Создаём автора (обязательно для M2M)
        self.author = Author.objects.create(
            last_name='AuthorLastName',
            first_name='AuthorFirstName',
            created_by=self.user  # created_by — обязательное поле
        )

        # Создаём книгу БЕЗ прямого указания author (пока не связываем)
        self.book = Book.objects.create(
            title='Test Book',
            publication_year=2020,
            pages=300,
            language='русский',
            created_by=self.user,
            total_copies=5,
            available_copies=5
        )

        # Связываем книгу с автором через M2M
        self.book.author.add(self.author)

    def test_serializer_valid_data(self):
        data = {
            'book': self.book.id,
            'user': self.user.id,
            'due_date': '2025-12-01T10:00:00Z',  # timezone-aware ISO-формат
            'notes': 'Test note'
        }

        serializer = BookLoanSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)  # Выводим ошибки, если есть

        # Проверяем, что validated_data содержит ожидаемые объекты
        self.assertEqual(serializer.validated_data['book'], self.book)
        self.assertEqual(serializer.validated_data['user'], self.user)

    def test_serializer_read_only_fields(self):
        loan = BookLoan.objects.create(book=self.book, user=self.user)
        serializer = BookLoanSerializer(loan)
        self.assertIn('loan_date', serializer.data)
        self.assertIn('created_by', serializer.data)
        # Проверяем, что read_only_fields не передаются в validated_data при обновлении
        update_data = {'loan_date': '2025-01-01T00:00:00Z'}
        serializer = BookLoanSerializer(loan, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())
        self.assertNotIn('loan_date', serializer.validated_data)



class BookLoanViewSetTest(APITestCase):

    def setUp(self):
        self.client = APIClient()

        # Создаём пользователей
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.staff_user = CustomUser.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        # Создаём автора (обязательно для M2M)
        self.author = Author.objects.create(
            last_name='AuthorLastName',
            first_name='AuthorFirstName',
            created_by=self.staff_user  # created_by — обязательное поле
        )

        # Создаём книгу БЕЗ прямого указания author
        self.book = Book.objects.create(
            title='Test Book',
            publication_year=2020,
            pages=300,
            language='русский',
            created_by=self.staff_user,
            total_copies=5,
            available_copies=5
        )

        # Связываем книгу с автором через M2M
        self.book.author.add(self.author)

        # URL для API
        self.list_url = reverse('loans:loan-list')
        self.detail_url = lambda pk: reverse('loans:loan-detail', kwargs={'pk': pk})

    def test_list_loans_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_loan_staff_only(self):
        # Неавторизованный пользователь
        data = {'book': self.book.id, 'user': self.user.id}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Авторизованный не-staff
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Staff-пользователь
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BookLoan.objects.count(), 1)
        loan = BookLoan.objects.first()
        self.assertEqual(loan.created_by, self.staff_user)

    def test_update_loan_permissions(self):
        loan = BookLoan.objects.create(book=self.book, user=self.user, created_by=self.staff_user)
        data = {'is_returned': True}

        # Не-staff пытается обновить
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.detail_url(loan.id), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Staff может обновить
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.patch(self.detail_url(loan.id), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertTrue(loan.is_returned)

    def test_filtering(self):
        BookLoan.objects.create(book=self.book, user=self.user, is_returned=False)
        BookLoan.objects.create(book=self.book, user=self.staff_user, is_returned=True)

        self.client.force_authenticate(user=self.staff_user)
        # Фильтрация по is_returned
        response = self.client.get(self.list_url, {'is_returned': 'true'})
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['is_returned'])

        # Фильтрация по book__id
        response = self.client.get(self.list_url, {'book__id': self.book.id})
        self.assertEqual(len(response.data['results']), 2)

    def test_search(self):
        BookLoan.objects.create(
            book=self.book,
            user=self.user,
            notes='Special note about this loan'
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {'search': 'Special'})
        self.assertEqual(len(response.data['results']), 1)

    def test_ordering(self):
        loan1 = BookLoan.objects.create(
            book=self.book,
            user=self.user,
            loan_date='2025-01-01T10:00:00Z',
            due_date='2025-01-15T10:00:00Z'
        )
        loan2 = BookLoan.objects.create(
            book=self.book,
            user=self.staff_user,
            loan_date='2025-02-01T10:00:00Z',
            due_date='2025-02-15T10:00:00Z'
        )

        self.client.force_authenticate(user=self.staff_user)

        # Сортировка по loan_date (по убыванию — дефолтная)
        response = self.client.get(self.list_url, {'ordering': '-loan_date'})
        self.assertEqual(response.data['results'][0]['id'], loan2.id)
        self.assertEqual(response.data['results'][1]['id'], loan1.id)

        # Сортировка по loan_date (по возрастанию)
        response = self.client.get(self.list_url, {'ordering': 'loan_date'})
        self.assertEqual(response.data['results'][0]['id'], loan1.id)
        self.assertEqual(response.data['results'][1]['id'], loan2.id)

        # Сортировка по book__title
        response = self.client.get(self.list_url, {'ordering': 'book__title'})
        # Так как у обеих записей одна и та же книга, порядок может быть любым,
        # но оба объекта должны присутствовать
        self.assertEqual(len(response.data['results']), 2)

        # Сортировка по user__username
        response = self.client.get(self.list_url, {'ordering': 'user__username'})
        usernames = [item['user_username'] for item in response.data['results']]
        self.assertListEqual(usernames, ['staffuser', 'testuser'])

    def test_pagination(self):
        # Создаём больше записей, чем размер страницы (20)
        for i in range(25):
            BookLoan.objects.create(
                book=self.book,
                user=self.user,
                loan_date=f'2025-01-{i + 1}T10:00:00Z'
            )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data['results']), 20)  # Размер страницы по умолчанию
        self.assertIn('next', response.data)
        self.assertIsNotNone(response.data['next'])

        # Проверяем страницу с указанным размером
        response = self.client.get(self.list_url, {'page_size': 10})
        self.assertEqual(len(response.data['results']), 10)

        # Проверяем максимальную страницу
        response = self.client.get(self.list_url, {'page_size': 150})
        self.assertLessEqual(len(response.data['results']), 100)  # max_page_size = 100

    def test_detail_view(self):
        loan = BookLoan.objects.create(book=self.book, user=self.user)
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], loan.id)
        self.assertEqual(response.data['book'], self.book.id)
        self.assertEqual(response.data['user'], self.user.id)

    def test_delete_loan_staff_only(self):
        loan = BookLoan.objects.create(book=self.book, user=self.user, created_by=self.staff_user)

        # Не-staff не может удалить
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Staff может удалить
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BookLoan.objects.filter(id=loan.id).exists())

    def test_created_by_auto_set(self):
        self.client.force_authenticate(user=self.staff_user)
        data = {'book': self.book.id, 'user': self.user.id}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        loan = BookLoan.objects.get(id=response.data['id'])
        self.assertEqual(loan.created_by, self.staff_user)
