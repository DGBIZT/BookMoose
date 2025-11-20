from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Genre

User = get_user_model()


class GenreModelTest(TestCase):
    """Тесты модели Genre."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="testuser@example.com",
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            password="adminpass123",
            email="admin@example.com",
        )

    def test_genre_creation(self):
        """Создание жанра."""
        genre = Genre.objects.create(
            name="Фантастика", description="Научно-фантастические миры", order=1, created_by=self.user
        )
        self.assertEqual(genre.name, "Фантастика")
        self.assertTrue(genre.is_active)
        self.assertEqual(genre.created_by, self.user)

    def test_genre_string_representation(self):
        """__str__ возвращает name."""
        genre = Genre(name="Детектив")
        self.assertEqual(str(genre), "Детектив")

    def test_get_full_path_root(self):
        """Полный путь для корневого жанра."""
        genre = Genre.objects.create(name="Фэнтези", created_by=self.user)
        self.assertEqual(genre.get_full_path(), "Фэнтези")

    def test_get_full_path_subgenre(self):
        """Полный путь для поджанра."""
        parent = Genre.objects.create(name="Фантастика", created_by=self.user)
        child = Genre.objects.create(name="Космоопера", parent=parent, created_by=self.user)
        self.assertEqual(child.get_full_path(), "Фантастика → Космоопера")

    def test_has_subgenres(self):
        """Проверка наличия поджанров."""
        parent = Genre.objects.create(name="Ужасы", created_by=self.user)
        Genre.objects.create(name="Сплэттер", parent=parent, created_by=self.user)
        self.assertTrue(parent.has_subgenres)


class GenreAPITest(TransactionTestCase):
    """Тесты API жанров."""

    def setUp(self):

        User.objects.filter(email="testuser@example.com").delete()
        User.objects.filter(email="admin@example.com").delete()
        Genre.objects.all().delete()  # очищает таблицу перед каждым тестом
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="author",
            password="pass123",
            email="testuser@example.com",
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            password="adminpass123",
            email="admin@example.com",
        )

        # Создаём жанры
        self.genre1 = Genre.objects.create(name="Научная фантастика", order=1, created_by=self.user)

        self.genre2 = Genre.objects.create(name="Фэнтези", order=2, created_by=self.user)
        self.subgenre = Genre.objects.create(name="Космоопера", parent=self.genre1, order=3, created_by=self.user)
        # Добавляем жанр "Детектив" с описанием для теста поиска
        self.detective_genre = Genre.objects.create(
            name="Детектив",
            description="Расследования и загадки",  # ← ключевое слово "загадки"
            created_by=self.user,
            order=4,
            is_active=True,
        )

        # URL
        self.list_url = reverse("genres:genre-list")
        self.detail_url = lambda pk: reverse("genres:genre-detail", kwargs={"pk": pk})

    def test_list_genres(self):
        """GET /genres/ — список жанров."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_retrieve_genre(self):
        """GET /genres/{id}/ — деталь жанра."""
        response = self.client.get(self.detail_url(self.genre1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Научная фантастика")
        self.assertEqual(response.data["full_path"], "Научная фантастика")

    def test_create_genre_authenticated(self):
        """POST /genres/ — создание жанра (аутентифицированный)."""
        self.client.force_authenticate(user=self.user)
        data = {"name": "Детектив XXI века", "description": "Расследования и загадки", "order": 4}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Genre.objects.count(), 5)
        self.assertEqual(response.data["created_by_username"], "author")

    def test_create_genre_unauthenticated(self):
        """POST /genres/ — запрещено без аутентификации."""
        data = {"name": "Триллер", "order": 5}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_genre_owner(self):
        """PUT /genres/{id}/ — обновление владельцем."""
        self.client.force_authenticate(user=self.user)
        data = {"name": "Новая фантастика", "order": 10}
        response = self.client.put(self.detail_url(self.genre1.pk), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Новая фантастика")

    def test_update_genre_other_user(self):
        """PUT /genres/{id}/ — запрещено для чужого жанра."""
        other_user = User.objects.create_user(username="other", password="pass")
        self.client.force_authenticate(user=other_user)
        data = {"name": "Взлом"}
        response = self.client.put(self.detail_url(self.genre1.pk), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_genre_admin(self):
        """PUT /genres/{id}/ — разрешено для админа."""
        self.client.force_authenticate(user=self.admin)
        data = {"name": "Админ-жанр"}
        response = self.client.put(self.detail_url(self.genre1.pk), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Админ-жанр")

    def test_delete_genre_owner(self):
        """DELETE /genres/{id}/ — удаление владельцем."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.detail_url(self.genre2.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Genre.objects.filter(pk=self.genre2.pk).exists())

    def test_delete_genre_other_user(self):
        """DELETE /genres/{id}/ — запрещено для чужого жанра."""
        other_user = User.objects.create_user(username="other", password="pass")
        self.client.force_authenticate(user=other_user)
        response = self.client.delete(self.detail_url(self.genre1.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_parent(self):
        """Фильтрация ?parent=... (только для существующего parent)"""

        # 1. Проверяем существование жанра в БД
        self.assertTrue(
            Genre.objects.filter(pk=self.genre1.pk).exists(), f"Жанр с pk={self.genre1.pk} не найден в БД!"
        )

        # 2. Выполняем запрос с фильтром по parent
        response = self.client.get(self.list_url, {"parent": int(self.genre1.pk)})

        # 3. Проверяем статус ответа
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Ожидался статус 200, получен {response.status_code}. Данные: {response.data}",
        )

        # 4. Проверяем наличие пагинации (поля 'results')
        self.assertIn("results", response.data, "Ответ должен содержать поле 'results' (пагинация)")

        results = response.data["results"]

        # 5. Проверяем количество результатов
        self.assertEqual(len(results), 1, f"Ожидался 1 результат, получено {len(results)}. Данные: {results}")

        # 6. Проверяем данные поджанра
        subgenre = results[0]
        self.assertEqual(subgenre["name"], "Космоопера", "Неверное имя поджанра")
        self.assertEqual(subgenre["parent"], self.genre1.pk, "Неверный parent PK")
        self.assertEqual(subgenre["full_path"], "Научная фантастика → Космоопера", "Неверный full_path")

    def test_filter_by_is_active(self):
        """Фильтрация ?is_active=..."""
        # Деактивируем один жанр
        self.genre2.is_active = False
        self.genre2.save()

        # Получаем только активные
        response = self.client.get(self.list_url, {"is_active": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что ответ пагинирован
        self.assertIn("results", response.data, "Ответ должен содержать поле 'results'")

        # Берём имена из results
        active_names = [item["name"] for item in response.data["results"]]
        self.assertIn("Научная фантастика", active_names)
        self.assertIn("Космоопера", active_names)
        self.assertNotIn("Фэнтези", active_names)  # деактивирован

        # Получаем только неактивные
        response = self.client.get(self.list_url, {"is_active": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("results", response.data, "Ответ должен содержать поле 'results'")
        inactive_names = [item["name"] for item in response.data["results"]]
        self.assertIn("Фэнтези", inactive_names)

    def test_search_in_name_description(self):
        """Поиск ?search=... по name и description."""
        # Ищем по части названия
        response = self.client.get(self.list_url, {"search": "науч"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Берем данные из 'results' пагинированного ответа
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Научная фантастика", names)

        # Ищем по описанию
        response = self.client.get(self.list_url, {"search": "загадки"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Детектив", names)

    def test_ordering(self):
        """Сортировка ?ordering=..."""
        # По имени (возрастание)
        response = self.client.get(self.list_url, {"ordering": "name"})
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, sorted(names))

        # По порядку (убывание)
        response = self.client.get(self.list_url, {"ordering": "-order"})
        orders = [item["order"] for item in response.data["results"]]
        self.assertEqual(orders, sorted(orders, reverse=True))

        # По username создателя
        response = self.client.get(self.list_url, {"ordering": "created_by__username"})
        usernames = [item["created_by_username"] for item in response.data["results"]]
        self.assertEqual(usernames, sorted(usernames))

    def test_pagination(self):
        """Пагинация: page и page_size."""
        # Создаём дополнительные жанры для пагинации
        for i in range(3, 25):
            Genre.objects.create(name=f"Жанр {i}", order=i, created_by=self.user)

        # Первая страница (20 на страницу по умолчанию)
        response = self.client.get(self.list_url, {"page": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])  # должна быть следующая страница

        # Вторая страница
        response = self.client.get(self.list_url, {"page": 2})
        self.assertEqual(len(response.data["results"]), 6)  # 24 жанра всего
        self.assertIsNone(response.data["next"])  # последней страницы нет next

        # Изменение размера страницы
        response = self.client.get(self.list_url, {"page_size": 5})
        self.assertEqual(len(response.data["results"]), 5)

    def test_read_only_fields(self):
        """Поля read_only не могут быть изменены при обновлении."""
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "Изменённый жанр",
            "created_by": 999,  # попытка изменить read_only поле
            "full_path": "фиктивный путь",  # ещё одно read_only
        }
        response = self.client.put(self.detail_url(self.genre1.pk), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверяем, что read_only поля остались прежними
        genre = Genre.objects.get(pk=self.genre1.pk)
        self.assertEqual(genre.created_by, self.user)  # не изменился
        # full_path вычисляется автоматически, не хранится в БД

    def test_serializer_full_path_has_subgenres(self):
        """Serializer добавляет full_path и has_subgenres."""
        response = self.client.get(self.detail_url(self.subgenre.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_path"], "Научная фантастика → Космоопера")
        self.assertFalse(response.data["has_subgenres"])  # у Космоперы нет поджанров

        # Добавляем поджанр к Космопере
        Genre.objects.create(name="Подкосмоопера", parent=self.subgenre, created_by=self.user)
        response = self.client.get(self.detail_url(self.subgenre.pk))
        self.assertTrue(response.data["has_subgenres"])

    def test_safe_methods_unauthenticated(self):
        """GET/HEAD/OPTIONS доступны без аутентификации."""
        # GET список
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # HEAD
        response = self.client.head(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # OPTIONS
        response = self.client.options(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
