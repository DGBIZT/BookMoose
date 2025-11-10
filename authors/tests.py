import uuid
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Author
from .serializers import AuthorSerializer

User = get_user_model()


class AuthorModelTest(TestCase):
    """Тесты модели Author"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        self.author = Author.objects.create(
            last_name="Мартин",
            first_name="Джордж",
            middle_name="Рэймонд Ричард",
            birth_date=date(1948, 9, 20),
            biography="Американский писатель-фантаст.",
            created_by=self.user,
        )

    def test_author_str(self):
        """Проверка строкового представления"""
        self.assertEqual(str(self.author), "Мартин Джордж Рэймонд Ричард")

    def test_get_full_name(self):
        """Проверка метода get_full_name"""
        self.assertEqual(self.author.get_full_name(), "Мартин Джордж Рэймонд Ричард")

    def test_get_short_name(self):
        """Проверка метода get_short_name"""
        self.assertEqual(self.author.get_short_name(), "Джордж Мартин")

    def test_required_fields(self):
        """Проверка обязательных полей"""
        author = Author(first_name="Иван", created_by=self.user)

        with self.assertRaises(Exception) as cm:
            author.full_clean()  # Явная валидация

        # Дополнительно можно проверить тип исключения
        self.assertIsInstance(cm.exception, ValidationError)

    def test_min_length_validator(self):
        """Проверка валидатора MinLengthValidator"""
        author = Author(last_name="А", first_name="Б", created_by=self.user)
        with self.assertRaises(Exception):
            author.full_clean()


class AuthorSerializerTest(TestCase):
    """Тесты сериализатора AuthorSerializer"""

    def setUp(self):
        # Генерируем уникальное имя, чтобы избежать конфликтов
        unique_username = f"serializer_user_{uuid.uuid4().hex[:8]}"
        self.user = User.objects.create_user(username=unique_username, password="pass123")
        self.data = {
            "last_name": "Толкин",
            "first_name": "Джон",
            "middle_name": "Рональд Руэл",
            "birth_date": "1892-01-03",
            "biography": "Английский писатель, филолог.",
        }

    def test_serializer_valid(self):
        serializer = AuthorSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_missing_required(self):
        """Сериализатор отклоняет отсутствие last_name/first_name"""
        data = self.data.copy()
        data.pop("last_name")
        serializer = AuthorSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("last_name", serializer.errors)

    def test_serializer_save(self):
        """Сериализатор сохраняет объект"""
        serializer = AuthorSerializer(data=self.data)
        if serializer.is_valid():
            author = serializer.save(created_by=self.user)
            self.assertEqual(author.last_name, "Толкин")
            self.assertEqual(author.created_by, self.user)


class AuthorAPITest(APITestCase):
    """Тесты API (ViewSet) для Author"""

    def setUp(self):
        # Создаём пользователей
        self.admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="adminpass")
        self.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="userpass")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="userpass")

        # Логинимся как user1
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

        # URL API
        self.list_url = reverse("authors:author-list")  # Добавляем namespace
        self.detail_url = lambda pk: reverse("authors:author-detail", kwargs={"pk": pk})

        # Пример данных для создания
        self.author_data = {
            "last_name": "Стругацкий",
            "first_name": "Аркадий",
            "middle_name": "Натанович",
            "birth_date": "1925-08-28",
            "biography": "Советский писатель-фантаст.",
        }

    def test_create_author(self):
        """Создание автора (POST)"""
        response = self.client.post(self.list_url, self.author_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Author.objects.count(), 1)
        self.assertEqual(Author.objects.first().created_by, self.user1)

    def test_retrieve_author(self):
        """Получение автора (GET detail)"""
        # Сначала создаём
        response = self.client.post(self.list_url, self.author_data, format="json")
        pk = response.data["id"]

        response = self.client.get(self.detail_url(pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_name"], "Стругацкий")

    def test_update_author(self):
        """Обновление автора (PUT/PATCH)"""
        # Создаём
        response = self.client.post(self.list_url, self.author_data, format="json")
        pk = response.data["id"]

        # PATCH (частичное обновление)
        patch_data = {"middle_name": "Н."}
        response = self.client.patch(self.detail_url(pk), patch_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["middle_name"], "Н.")

        # PUT (полное обновление)
        put_data = self.author_data.copy()
        put_data["first_name"] = "Борис"
        response = self.client.put(self.detail_url(pk), put_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Борис")

    def test_delete_author(self):
        """Удаление автора (DELETE)"""
        # Создаём
        response = self.client.post(self.list_url, self.author_data, format="json")
        pk = response.data["id"]

        response = self.client.delete(self.detail_url(pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Author.objects.count(), 0)

    def test_filtering(self):
        """Фильтрация по last_name/first_name"""
        Author.objects.create(last_name="Пушкин", first_name="Александр", created_by=self.user1)
        Author.objects.create(last_name="Лермонтов", first_name="Михаил", created_by=self.user1)

        # Фильтрация по фамилии
        response = self.client.get(self.list_url, {"last_name": "Пушкин"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["last_name"], "Пушкин")

        # Фильтрация по имени
        response = self.client.get(self.list_url, {"first_name": "Михаил"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["first_name"], "Михаил")

        # Комбинированная фильтрация (если поддерживается)
        response = self.client.get(self.list_url, {"last_name": "Пушкин", "first_name": "Александр"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["last_name"], "Пушкин")
        self.assertEqual(result["first_name"], "Александр")

    def test_search(self):
        """Поиск по полям (search_fields)"""
        Author.objects.create(
            last_name="Достоевский", first_name="Фёдор", biography="Великий русский писатель.", created_by=self.user1
        )

        # Поиск по фамилии
        response = self.client.get(self.list_url, {"search": "Достоевский"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)
        self.assertIn("Достоевский", [a["last_name"] for a in response.data["results"]])

        # Поиск по имени
        response = self.client.get(self.list_url, {"search": "Фёдор"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)
        self.assertIn("Фёдор", [a["first_name"] for a in response.data["results"]])

        # Поиск по биографии
        response = self.client.get(self.list_url, {"search": "русский писатель"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

    def test_ordering(self):
        """Сортировка по полям (ordering_fields)"""
        Author.objects.create(last_name="Толстой", first_name="Лев", created_by=self.user1)
        Author.objects.create(last_name="Чехов", first_name="Антон", created_by=self.user1)

        # Сортировка по фамилии (asc)
        response = self.client.get(self.list_url, {"ordering": "last_name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        last_names = [a["last_name"] for a in response.data["results"]]
        self.assertEqual(last_names, ["Толстой", "Чехов"])  # Лев → Антон

        # Сортировка по фамилии (desc)
        response = self.client.get(self.list_url, {"ordering": "-last_name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        last_names = [a["last_name"] for a in response.data["results"]]
        self.assertEqual(last_names, ["Чехов", "Толстой"])

        # Сортировка по имени
        response = self.client.get(self.list_url, {"ordering": "first_name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_names = [a["first_name"] for a in response.data["results"]]
        self.assertEqual(first_names, ["Антон", "Лев"])

    def test_permission_deny_other_user_update(self):
        """Пользователь не может редактировать/удалять авторов другого пользователя"""
        # Создаём автора от user2
        author = Author.objects.create(last_name="Другой", first_name="Автор", created_by=self.user2)

        url = self.detail_url(author.id)

        # Пытаемся обновить как user1 (должно быть запрещено)
        patch_data = {"middle_name": "Обновлённое"}
        response = self.client.patch(url, patch_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Пытаемся удалить как user1
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_manage_all_authors(self):
        """Админ может редактировать/удалять любых авторов"""
        self.client.force_authenticate(user=self.admin)

        author = Author.objects.create(
            last_name="Секретный", first_name="Автор", created_by=self.user2  # Создан другим пользователем
        )

        url = self.detail_url(author.id)

        # Админ обновляет
        patch_data = {"middle_name": "Админское"}
        response = self.client.patch(url, patch_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["middle_name"], "Админское")

        # Админ удаляет
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_access(self):
        """Неавторизованный пользователь не может создавать/редактировать/удалять"""
        self.client.force_authenticate(user=None)  # Снимаем аутентификацию

        # POST (создание)
        response = self.client.post(self.list_url, self.author_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # PUT (обновление)
        author = Author.objects.create(**self.author_data, created_by=self.user1)
        url = self.detail_url(author.id)
        response = self.client.put(url, self.author_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # DELETE (удаление)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
