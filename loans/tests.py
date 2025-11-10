import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authors.models import Author
from books.models import Book, BookInstance
from loans.models import BookLoan

from .serializers import BookLoanSerializer

User = get_user_model()


class BookLoanModelTest(TestCase):
    def setUp(self):
        # Создаём пользователя (не staff)
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        # Создаём staff-пользователя (понадобится для created_by)
        self.staff_user = User.objects.create_user(username="libstaff", password="staffpass123", is_staff=True)

        # Создаём автора (обязательно last_name и first_name)
        self.author = Author.objects.create(
            last_name="Иванов", first_name="Иван", created_by=self.staff_user  # обязательное поле!
        )

        # Создаём книгу
        self.book = Book.objects.create(
            title="Test Book",
            created_by=self.staff_user,  # ← обязательно!
            publication_year=2023,  # ← обязательно!
            pages=300,  # ← обязательно!
            language="русский",  # ← лучше указать явно
        )

        # Связываем книгу с автором (предполагается M2M связь authors в модели Book)
        self.book.author.add(self.author)

        # Создаём экземпляр книги
        self.book_instance = BookInstance.objects.create(book=self.book, copy_id="001", status="available")

    def test_create_book_loan(self):
        """Проверка создания записи о выдаче."""
        loan = BookLoan.objects.create(
            book_instance=self.book_instance, user=self.user, due_date=timezone.now() + timedelta(days=14)
        )

        self.assertEqual(loan.book_instance, self.book_instance)
        self.assertEqual(loan.user, self.user)
        self.assertFalse(loan.is_returned)
        self.assertIsNone(loan.return_date)

    def test_save_sets_return_date(self):
        """При установке is_returned=True автоматически ставится return_date."""
        loan = BookLoan.objects.create(
            book_instance=self.book_instance, user=self.user, due_date=timezone.now() + datetime.timedelta(days=14)
        )
        loan.is_returned = True
        loan.save()
        self.assertIsNotNone(loan.return_date)
        self.assertTrue(loan.is_returned)

    def test_save_updates_book_instance_status(self):
        """Статус экземпляра меняется при сохранении выдачи."""
        loan = BookLoan.objects.create(
            book_instance=self.book_instance, user=self.user, due_date=timezone.now() + datetime.timedelta(days=14)
        )
        self.assertEqual(self.book_instance.status, "loaned")

        loan.is_returned = True
        loan.save()
        self.book_instance.refresh_from_db()
        self.assertEqual(self.book_instance.status, "available")

    def test_unique_active_loan_constraint(self):
        """Нельзя выдать один экземпляр дважды (если не возвращён)."""
        BookLoan.objects.create(
            book_instance=self.book_instance, user=self.user, due_date=timezone.now() + datetime.timedelta(days=14)
        )
        with self.assertRaises(Exception):  # Ожидаем ошибку целостности БД
            BookLoan.objects.create(
                book_instance=self.book_instance, user=self.user, due_date=timezone.now() + datetime.timedelta(days=7)
            )


class BookLoanSerializerTest(TestCase):
    """Тесты для сериализатора BookLoanSerializer."""

    def setUp(self):
        # Создаём пользователя (не staff)
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        # Создаём staff-пользователя (понадобится для created_by)
        self.staff_user = User.objects.create_user(username="libstaff", password="staffpass123", is_staff=True)

        # Создаём автора (обязательно last_name и first_name)
        self.author = Author.objects.create(
            last_name="Иванов", first_name="Иван", created_by=self.staff_user  # обязательное поле!
        )

        # Создаём книгу
        self.book = Book.objects.create(
            title="Test Book",
            created_by=self.staff_user,  # ← обязательно!
            publication_year=2023,  # ← обязательно!
            pages=300,  # ← обязательно!
            language="русский",  # ← лучше указать явно
        )

        # Связываем книгу с автором (предполагается M2M связь authors в модели Book)
        self.book.author.add(self.author)

        # Создаём экземпляр книги
        self.book_instance = BookInstance.objects.create(book=self.book, copy_id="001", status="available")

    def test_serializer_valid_data(self):
        """Сериализатор принимает корректные данные."""
        data = {
            "book_instance": self.book_instance.id,
            "user": self.user.id,
            "due_date": timezone.now() + datetime.timedelta(days=14),
            "notes": "Please return on time.",
        }
        serializer = BookLoanSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["book_instance"], self.book_instance)

    def test_serializer_invalid_due_date(self):
        """Ошибка, если due_date раньше loan_date."""
        data = {
            "book_instance": self.book_instance.id,
            "user": self.user.id,
            "due_date": timezone.now() - datetime.timedelta(days=1),
        }
        serializer = BookLoanSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("due_date", serializer.errors)

    def test_serializer_read_only_fields(self):
        """Нельзя изменять loan_date и created_by."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        data = {"loan_date": timezone.now(), "created_by": self.user.id}
        serializer = BookLoanSerializer(instance=loan, data=data, partial=True)

        # 1. Проверяем, что is_valid() возвращает True (DRF игнорирует read_only-поля)
        self.assertTrue(serializer.is_valid())

        # 2. Проверяем, что поля НЕ попали в validated_data
        self.assertNotIn("loan_date", serializer.validated_data)
        self.assertNotIn("created_by", serializer.validated_data)

        # 3. Дополнительно: проверяем, что поля остались неизменными в экземпляре
        serializer.save()
        self.assertEqual(loan.loan_date, serializer.instance.loan_date)  # не изменился
        self.assertEqual(loan.created_by, serializer.instance.created_by)  # не изменился

    def test_to_representation_hides_copy_id_and_title(self):
        """Если book_instance нет, copy_id и book_title скрываются."""
        loan = BookLoan.objects.create(user=self.user)  # без book_instance
        serializer = BookLoanSerializer(instance=loan)
        data = serializer.data
        self.assertIsNone(data["copy_id"])
        self.assertIsNone(data["book_title"])


class BookLoanViewSetTest(APITestCase):
    """Тесты для BookLoanViewSet (API)."""

    def setUp(self):
        self.client = APIClient()
        # Создаём пользователя (не staff)
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        # Создаём staff-пользователя (понадобится для created_by)
        self.staff_user = User.objects.create_user(username="libstaff", password="staffpass123", is_staff=True)

        # Создаём автора (обязательно last_name и first_name)
        self.author = Author.objects.create(
            last_name="Иванов", first_name="Иван", created_by=self.staff_user  # обязательное поле!
        )

        # Создаём книгу
        self.book = Book.objects.create(
            title="Test Book",
            created_by=self.staff_user,  # ← обязательно!
            publication_year=2023,  # ← обязательно!
            pages=300,  # ← обязательно!
            language="русский",  # ← лучше указать явно
        )

        # Связываем книгу с автором (предполагается M2M связь authors в модели Book)
        self.book.author.add(self.author)

        # Создаём экземпляр книги
        self.book_instance = BookInstance.objects.create(book=self.book, copy_id="001", status="available")
        # URL
        super().setUp()
        self.list_url = reverse("loans:loans-list")
        self.detail_url = lambda pk: reverse("loans:loans-detail", kwargs={"pk": pk})

    def test_unauthenticated_access_denied(self):
        """Анонимным доступ запрещён."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_own_loans(self):
        """Пользователь видит только свои выдачи."""
        # Создаём и сразу возвращаем первую выдачу
        BookLoan.objects.create(
            book_instance=self.book_instance,
            user=self.user,
            is_returned=True,  # ← отмечаем как возвращённую
            return_date=timezone.now(),
        )

        # Теперь можно создать вторую активную выдачу
        other_user = User.objects.create_user(username="other", password="otherpass", email="other@example.com")
        BookLoan.objects.create(book_instance=self.book_instance, user=other_user)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)  # ← у self.user нет активных выдач

    def test_staff_can_list_all_loans(self):
        """Staff видит все выдачи."""
        other_user = User.objects.create_user(username="other", password="otherpass", email="other@example.com")

        # Создаём два разных экземпляра книги с обязательным copy_id
        book_instance_1 = BookInstance.objects.create(book=self.book, status="available", copy_id="COPY001")
        book_instance_2 = BookInstance.objects.create(book=self.book, status="available", copy_id="COPY002")

        # Создаём выдачи для разных экземпляров
        BookLoan.objects.create(book_instance=book_instance_1, user=self.user)
        BookLoan.objects.create(book_instance=book_instance_2, user=other_user)

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_user_cannot_create_loan(self):
        """Обычный пользователь не может создать выдачу."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.list_url,
            {
                "book_instance": self.book_instance.id,
                "due_date": (timezone.now() + timedelta(days=14)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(BookLoan.objects.count(), 0)  # Выдача не создана

    def test_staff_can_create_loan(self):
        """Staff-пользователь может создать выдачу."""
        self.client.force_authenticate(user=self.staff_user)  # staff_user из setUp
        response = self.client.post(
            self.list_url,
            {
                "book_instance": self.book_instance.id,
                "user": self.user.id,  # выдаём книгу обычному пользователю
                "due_date": (timezone.now() + timedelta(days=14)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BookLoan.objects.count(), 1)
        loan = BookLoan.objects.first()
        self.assertEqual(loan.book_instance, self.book_instance)
        self.assertEqual(loan.user, self.user)  # получатель — self.user
        self.assertFalse(loan.is_returned)
        self.book_instance.refresh_from_db()
        self.assertEqual(self.book_instance.status, "loaned")

    def test_create_loan_unavailable_instance(self):
        """Нельзя создать выдачу для недоступного экземпляра."""
        # Сначала выдаём экземпляр
        BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        data = {
            "book_instance": self.book_instance.id,
            "user": self.user.id,
            "due_date": (timezone.now() + datetime.timedelta(days=14)).isoformat(),
        }
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book_instance", response.data)

    def test_user_can_update_own_loan_notes_and_due_date(self):
        """Пользователь может обновить notes и due_date своей выдачи."""
        loan = BookLoan.objects.create(
            book_instance=self.book_instance, user=self.user, due_date=timezone.now() + datetime.timedelta(days=7)
        )
        data = {"notes": "Updated notes", "due_date": (timezone.now() + datetime.timedelta(days=21)).isoformat()}
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.detail_url(loan.id), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.notes, "Updated notes")
        self.assertEqual(loan.due_date.date(), (timezone.now() + datetime.timedelta(days=21)).date())

    def test_user_cannot_update_forbidden_fields(self):
        """Пользователь не может обновить запрещённые поля."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        data = {"user": self.staff_user.id}  # Попытка сменить пользователя
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.detail_url(loan.id), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_update_any_field(self):
        # Создаём объект
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user, notes="Initial note")
        self.assertTrue(BookLoan.objects.filter(id=loan.id).exists())
        # Выполняем запрос
        data = {"notes": "Staff updated notes"}
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.patch(self.detail_url(loan.id), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.notes, "Staff updated notes")

    def test_user_cannot_mark_as_returned(self):
        """Пользователь НЕ может самостоятельно отметить выдачу как возвращённую."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        data = {"is_returned": True}
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.detail_url(loan.id), data, format="json")

        # Ожидаем 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверяем, что поле НЕ изменилось
        loan.refresh_from_db()
        self.assertFalse(loan.is_returned)
        self.assertIsNone(loan.return_date)

        # Статус экземпляра тоже не изменился
        self.book_instance.refresh_from_db()
        self.assertEqual(self.book_instance.status, "loaned")  # или исходное значение

    def test_staff_can_delete_loan(self):
        """Staff может удалить выдачу."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BookLoan.objects.filter(id=loan.id).exists())
        self.book_instance.refresh_from_db()
        self.assertEqual(self.book_instance.status, "available")

    def test_user_cannot_delete_loan(self):
        """Пользователь не может удалить выдачу."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filtering_by_is_returned(self):
        """Фильтрация по is_returned."""
        BookLoan.objects.create(book_instance=self.book_instance, user=self.user, is_returned=True)
        BookLoan.objects.create(book_instance=self.book_instance, user=self.user, is_returned=False)

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {"is_returned": "true"})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(response.data["results"][0]["is_returned"])

    def test_search_by_book_title(self):
        """Поиск по названию книги."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {"search": "Test Book"})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], loan.id)

    def test_search_by_notes(self):
        """Поиск по примечаниям (notes)."""
        loan = BookLoan.objects.create(
            book_instance=self.book_instance, user=self.user, notes="Особые условия возврата"
        )
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {"search": "Особые условия"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], loan.id)

    def test_ordering_by_loan_date(self):
        """Сортировка по дате выдачи (loan_date)."""
        # Создаём два разных экземпляра книги с заполненным copy_id
        book_instance1 = BookInstance.objects.create(book=self.book, copy_id="COPY001")
        book_instance2 = BookInstance.objects.create(book=self.book, copy_id="COPY002")

        loan1 = BookLoan.objects.create(
            book_instance=book_instance1, user=self.user, loan_date=timezone.now() - datetime.timedelta(days=7)
        )
        loan2 = BookLoan.objects.create(book_instance=book_instance2, user=self.user, loan_date=timezone.now())
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {"ordering": "loan_date"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], loan1.id)
        self.assertEqual(response.data["results"][1]["id"], loan2.id)

    def test_ordering_by_due_date_desc(self):
        """Сортировка по сроку возврата (due_date) по убыванию."""
        # Создаём два разных экземпляра книги
        book_instance1 = BookInstance.objects.create(book=self.book, copy_id="COPY001")
        book_instance2 = BookInstance.objects.create(book=self.book, copy_id="COPY002")

        loan1 = BookLoan.objects.create(
            book_instance=book_instance1, user=self.user, due_date=timezone.now() + datetime.timedelta(days=14)
        )
        loan2 = BookLoan.objects.create(
            book_instance=book_instance2, user=self.user, due_date=timezone.now() + datetime.timedelta(days=7)
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {"ordering": "-due_date"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], loan1.id)
        self.assertEqual(response.data["results"][1]["id"], loan2.id)

    def test_pagination(self):
        """Проверка пагинации (20 записей на страницу)."""
        # Создаём 25 разных экземпляров книги
        book_instances = []
        for i in range(25):
            book_instance = BookInstance.objects.create(book=self.book, copy_id=f"COPY{i:03d}")  # Уникальное значение
            book_instances.append(book_instance)

        # Создаём 25 выдач — каждая для своего экземпляра
        loans = []
        for book_instance in book_instances:
            loan = BookLoan.objects.create(book_instance=book_instance, user=self.user)
            loans.append(loan)

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 20)  # Первая страница — 20 записей
        self.assertIsNotNone(response.data["next"])  # Есть следующая страница
        self.assertIsNone(response.data["previous"])  # Нет предыдущей страницы

    def test_custom_page_size(self):
        """Изменение размера страницы через параметр page_size."""
        # Создаём 10 разных экземпляров книги
        book_instances = []
        for i in range(10):
            book_instance = BookInstance.objects.create(book=self.book, copy_id=f"COPY{i:03d}")  # Уникальное значение
            book_instances.append(book_instance)

        # Создаём 10 выдач — каждая для своего экземпляра
        for book_instance in book_instances:
            BookLoan.objects.create(book_instance=book_instance, user=self.user)

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url, {"page_size": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)

    def test_get_detail_for_own_loan(self):
        """Пользователь может получить детальную информацию о своей выдаче."""
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=self.user)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], loan.id)

    def test_get_detail_for_other_loan_denied(self):
        """Пользователь не может получить детальную информацию о чужой выдаче."""
        other_user = User.objects.create_user(username="other", password="otherpass", email="other@example.com")
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=other_user)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_get_any_detail(self):
        """Staff может получить детальную информацию о любой выдаче."""
        other_user = User.objects.create_user(username="other", password="otherpass", email="other@example.com")
        loan = BookLoan.objects.create(book_instance=self.book_instance, user=other_user)
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.detail_url(loan.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], loan.id)
