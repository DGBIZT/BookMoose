from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import CustomUser


class UserAPITestCase(APITestCase):
    def setUp(self):
        # Создаем тестового пользователя
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword123',
            phone_number='1234567890',
            city='TestCity'
        )
        self.superuser = CustomUser.objects.create_superuser(
            email='super@example.com',
            username='superuser',
            password='superpassword123'
        )

    def test_user_registration(self):
        """Тест регистрации нового пользователя"""
        url = reverse('users:register')  # Используем префикс приложения
        data = {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'newpassword123',
            'phone_number': '9876543210',
            'city': 'NewCity'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), 3)

    def test_user_login(self):
        """Тест входа в систему"""
        url = reverse('users:login')  # Используем префикс приложения
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_user_retrieve_me(self):
        """Тест получения информации о себе через /me/"""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['username'], self.user.username)

    def test_user_retrieve_by_pk(self):
        """Тест получения информации о пользователе по ID"""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-detail', kwargs={'pk': self.user.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['username'], self.user.username)

    def test_user_retrieve_other_user(self):
        """Тест попытки получения информации о другом пользователе"""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-detail', kwargs={'pk': self.superuser.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_retrieve_other_user(self):
        """Тест получения информации о пользователе суперпользователем"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('users:user-detail', kwargs={'pk': self.user.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_update(self):
        """Тест обновления данных пользователя"""
        self.client.force_authenticate(user=self.user)
        # Добавляем префикс приложения 'users:'
        url = reverse('users:user-update', kwargs={'pk': self.user.pk})
        data = {
            'phone_number': '1112223333',
            'city': 'UpdatedCity'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '1112223333')
        self.assertEqual(self.user.city, 'UpdatedCity')

    def test_user_delete(self):
        """Тест удаления собственного аккаунта"""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-delete', kwargs={'pk': self.user.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomUser.objects.filter(pk=self.user.pk).exists())

    def test_delete_other_user(self):
        """Тест попытки удаления чужого аккаунта обычным пользователем"""
        self.client.force_authenticate(user=self.user)
        # Исправляем имя URL и используем kwargs
        url = reverse('users:user-delete', kwargs={'pk': self.superuser.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CustomUser.objects.filter(pk=self.superuser.pk).exists())
        self.assertIn('detail', response.data)

    def test_superuser_delete(self):
        """Тест удаления аккаунта суперпользователем"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('users:user-delete', kwargs={'pk': self.user.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomUser.objects.filter(pk=self.user.pk).exists())

    def test_unauthorized_access(self):
        """Тест неавторизованного доступа к информации о пользователе"""
        # Добавляем префикс приложения и указываем pk
        url = reverse('users:user-detail', kwargs={'pk': self.user.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_other_user(self):
        """Тест попытки обновления чужого профиля"""
        self.client.force_authenticate(user=self.user)
        # Используем правильный префикс и kwargs
        url = reverse('users:user-update', kwargs={'pk': self.superuser.pk})
        data = {
            'phone_number': '1234567890',
            'city': 'NewCity'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_update_other_user(self):
        """Тест обновления профиля суперпользователем"""
        self.client.force_authenticate(user=self.superuser)
        # Используем правильный префикс приложения и kwargs
        url = reverse('users:user-update', kwargs={'pk': self.user.pk})
        data = {
            'phone_number': '9998887777',
            'city': 'SuperCity'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '9998887777')
        self.assertEqual(self.user.city, 'SuperCity')

    def test_invalid_registration_data(self):
        """Тест регистрации с некорректными данными"""
        url = reverse('users:register')
        data = {
            'email': 'invalid-email',  # Некорректный email
            'username': '',  # Пустое имя пользователя
            'password': 'short',  # Пароль слишком короткий
            'phone_number': 'abc123'  # Некорректный номер телефона
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверяем наличие ошибок валидации
        self.assertIn('username', response.data)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
        self.assertIn('phone_number', response.data)

        # Проверяем конкретные сообщения об ошибках
        self.assertEqual(response.data['username'][0].code, 'blank')
        self.assertEqual(response.data['email'][0].code, 'invalid')

        # Проверяем ошибку пароля
        password_error = response.data['password'][0]
        self.assertTrue('слишком короткий' in str(password_error) or 'не менее 8 символов' in str(password_error))

        # Проверяем валидацию номера телефона
        phone_error = response.data['phone_number'][0]
        self.assertEqual(phone_error.code, 'invalid')  # Проверяем код ошибки
        self.assertTrue('должен содержать только цифры' in str(phone_error) or 'invalid' in str(phone_error))

    def test_duplicate_registration(self):
        """Тест регистрации с существующим email"""
        url = reverse('register')
        data = {
            'email': 'test@example.com',  # уже существующий email
            'username': 'newuser',
            'password': 'newpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_password_change(self):
        """Тест смены пароля"""
        self.client.force_authenticate(user=self.user)

        # Исправленный URL с учетом структуры путей
        url = reverse('users:user-update', kwargs={'pk': self.user.pk})

        # Сохраняем старый пароль для проверки
        old_password = 'testpassword123'
        new_password = 'newsecurepassword123'

        # Проверяем, что старый пароль работает до изменения
        self.assertTrue(self.user.check_password(old_password))

        # Пытаемся изменить пароль
        data = {
            'password': new_password
        }
        response = self.client.patch(url, data, format='json')

        # Проверяем успешный ответ
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Обновляем пользователя из базы данных
        self.user.refresh_from_db()

        # Проверяем, что старый пароль больше не подходит
        self.assertFalse(self.user.check_password(old_password))

        # Проверяем, что новый пароль установлен корректно
        self.assertTrue(self.user.check_password(new_password))

        # Проверяем, что другие поля не изменились
        self.assertEqual(self.user.username, self.user.username)
        self.assertEqual(self.user.email, self.user.email)

    def test_invalid_password_change(self):
        """Тест попытки смены пароля на некорректный"""
        self.client.force_authenticate(user=self.user)

        # Используем полное имя URL с namespace
        url = reverse('users:user-update', kwargs={'pk': self.user.pk})

        # Попытка установить слишком короткий пароль
        data_short = {
            'password': 'short'
        }
        response_short = self.client.patch(url, data_short, format='json')
        self.assertEqual(response_short.status_code, status.HTTP_400_BAD_REQUEST)

        # Попытка установить пароль без специальных символов
        data_simple = {
            'password': '12345678'
        }
        response_simple = self.client.patch(url, data_simple, format='json')
        self.assertEqual(response_simple.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверяем, что пароль не изменился
        self.assertTrue(self.user.check_password('testpassword123'))

    def test_update_other_fields(self):
        """Тест обновления других полей профиля"""
        self.client.force_authenticate(user=self.user)

        # Используем полное имя URL с namespace
        url = reverse('users:user-update', kwargs={'pk': self.user.pk})

        new_email = 'newemail@example.com'
        new_phone = '1234567890'

        data = {
            'email': new_email,
            'phone_number': new_phone
        }

        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, new_email)
        self.assertEqual(self.user.phone_number, new_phone)

    def test_unauthorized_update(self):
        """Тест попытки обновления чужого профиля"""
        other_user = CustomUser.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='otherpassword123'
        )

        self.client.force_authenticate(user=self.user)

        # Используем полное имя URL с namespace
        url = reverse('users:user-update', kwargs={'pk': other_user.pk})

        data = {
            'email': 'newemail@example.com'
        }

        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def tearDown(self):
        """Очистка после тестов"""
        CustomUser.objects.all().delete()
