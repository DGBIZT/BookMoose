# Инструкция по настройке CI/CD с GitHub Actions и Yandex Cloud

Эта инструкция поможет настроить автоматический деплой вашего приложения на сервер Yandex Cloud при каждом push в GitHub.

## 📋 Содержание

1. [Подготовка сервера Yandex Cloud](#1-подготовка-сервера-yandex-cloud)
2. [Настройка SSH доступа](#2-настройка-ssh-доступа)
3. [Настройка GitHub Secrets](#3-настройка-github-secrets)
4. [Настройка GitHub Actions](#4-настройка-github-actions)
5. [Проверка работоспособности](#5-проверка-работоспособности)
6. [Устранение неполадок](#6-устранение-неполадок)

---

## 1. Подготовка сервера Yandex Cloud

### 1.1 Создание виртуальной машины

1. Войдите в [консоль Yandex Cloud](https://console.cloud.yandex.ru/)
2. Перейдите в раздел **Compute Cloud** → **Виртуальные машины**
3. Нажмите **Создать ВМ**
4. Настройте параметры:
   - **Имя**: `bookmoose-server` (или любое другое)
   - **Зона доступности**: выберите ближайшую к вам
   - **Образ**: Ubuntu 22.04 LTS или Ubuntu 20.04 LTS
   - **Платформа**: Intel Ice Lake
   - **vCPU**: минимум 2 ядра
   - **RAM**: минимум 4 ГБ
   - **Диск**: минимум 20 ГБ SSD
5. В разделе **Доступ**:
   - Выберите или создайте сервисный аккаунт
   - Включите **Доступ через SSH**
   - Добавьте свой SSH-ключ (если есть) или создайте новый
6. Нажмите **Создать ВМ**

### 1.2 Настройка сетевых правил

1. Перейдите в **VPC** → **Группы безопасности**
2. Найдите группу безопасности вашей ВМ
3. Добавьте правила для входящего трафика:
   - **HTTP (80)**: `0.0.0.0/0`
   - **HTTPS (443)**: `0.0.0.0/0`
   - **SSH (22)**: ваш IP-адрес или `0.0.0.0/0` (менее безопасно)
   - **Порт 8000** (для Django): `0.0.0.0/0` (если нужно)

### 1.3 Получение внешнего IP-адреса

1. В списке ВМ найдите вашу машину
2. Запишите **Публичный IPv4** адрес (например, `51.250.XX.XX`)
3. Этот адрес понадобится для настройки GitHub Secrets

---

## 2. Настройка SSH доступа

### 2.1 Подключение к серверу

```bash
ssh ubuntu@<ВАШ_IP_АДРЕС>
# или
ssh <USERNAME>@<ВАШ_IP_АДРЕС>
```

**Примечание**: Имя пользователя зависит от образа:
- Ubuntu: `ubuntu`
- CentOS: `centos`
- Debian: `debian`

### 2.2 Установка необходимого ПО на сервере

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Установка Git
sudo apt install git -y

# Добавление пользователя в группу docker (чтобы не использовать sudo)
sudo usermod -aG docker $USER
newgrp docker

# Проверка установки
docker --version
docker-compose --version
git --version
```

### 2.3 Клонирование репозитория на сервер

```bash
# Создайте директорию для проекта
sudo mkdir -p /BookMoose
sudo chown $USER:$USER /BookMoose

# Перейдите в директорию
cd /BookMoose

# Клонируйте репозиторий
git clone https://github.com/<ВАШ_USERNAME>/BookMoose.git .

# Или если используете SSH:
git clone git@github.com:<ВАШ_USERNAME>/BookMoose.git .
```

### 2.4 Создание файла .env на сервере

```bash
cd /BookMoose
nano .env
```

Добавьте все необходимые переменные окружения:

```env
SECRET_KEY=ваш-секретный-ключ
DEBUG=False
DATABASE_NAME=bookmoose_db
DATABASE_USER=postgres
DATABASE_PASSWORD=ваш-надежный-пароль
DATABASE_HOST=db
DATABASE_PORT=5432
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
ALLOWED_HOSTS=ваш-ip-адрес,ваш-домен.ru
EMAIL_HOST_USER=ваш-email@yandex.ru
EMAIL_HOST_PASSWORD=ваш-пароль-приложения
```

Сохраните файл: `Ctrl+O`, `Enter`, `Ctrl+X`

### 2.5 Первый запуск приложения

```bash
cd /BookMoose

# Соберите и запустите контейнеры
docker-compose build
docker-compose up -d

# Примените миграции
docker-compose exec web python manage.py migrate

# Создайте суперпользователя (опционально)
docker-compose exec web python manage.py createsuperuser

# Проверьте статус контейнеров
docker-compose ps
```

---

## 3. Настройка GitHub Secrets

### 3.1 Генерация SSH ключа для GitHub Actions

**На вашем локальном компьютере:**

```bash
# Создайте новый SSH ключ специально для GitHub Actions
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy

# НЕ устанавливайте пароль (просто нажмите Enter дважды)
```

### 3.2 Добавление публичного ключа на сервер

```bash
# Скопируйте публичный ключ
cat ~/.ssh/github_actions_deploy.pub
```

**На сервере Yandex Cloud:**

```bash
# Войдите на сервер
ssh ubuntu@<ВАШ_IP_АДРЕС>

# Добавьте публичный ключ в authorized_keys
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ВАШ_ПУБЛИЧНЫЙ_КЛЮЧ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3.3 Добавление Secrets в GitHub

1. Перейдите в ваш репозиторий на GitHub
2. Откройте **Settings** → **Secrets and variables** → **Actions**
3. Нажмите **New repository secret**
4. Добавьте следующие секреты:

#### `SERVER_HOST`
- **Name**: `SERVER_HOST`
- **Value**: IP-адрес вашего сервера (например, `51.250.XX.XX`)

#### `SERVER_USERNAME`
- **Name**: `SERVER_USERNAME`
- **Value**: имя пользователя на сервере (обычно `ubuntu`)

#### `SERVER_SSH_KEY`
- **Name**: `SERVER_SSH_KEY`
- **Value**: содержимое **приватного** ключа:

```bash
# На вашем локальном компьютере
cat ~/.ssh/github_actions_deploy
```

Скопируйте весь вывод (включая `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`)

---

## 4. Настройка GitHub Actions

### 4.1 Проверка файла workflow

Убедитесь, что файл `.github/workflows/ci.yml` существует и содержит правильную конфигурацию.

### 4.2 Включение GitHub Actions

1. Перейдите в **Settings** → **Actions** → **General**
2. В разделе **Workflow permissions**:
   - Выберите **Read and write permissions**
   - Отметьте **Allow GitHub Actions to create and approve pull requests**
3. В разделе **Actions permissions**:
   - Выберите **Allow all actions and reusable workflows**
4. Нажмите **Save**

### 4.3 Коммит и push workflow файла

```bash
# На вашем локальном компьютере
cd /path/to/BookMoose

# Добавьте workflow файл (если еще не добавлен)
git add .github/workflows/ci.yml

# Закоммитьте изменения
git commit -m "Настройка CI/CD для автоматического деплоя"

# Отправьте в репозиторий
git push origin feature/library
```

---

## 5. Проверка работоспособности

### 5.1 Проверка запуска workflow

1. Перейдите в ваш репозиторий на GitHub
2. Откройте вкладку **Actions**
3. Вы должны увидеть запущенный workflow **CI/CD Pipeline**
4. Нажмите на него, чтобы увидеть прогресс выполнения

### 5.2 Мониторинг выполнения

Workflow выполняет следующие шаги:
1. ✅ **Set up Python** - установка Python 3.11
2. ✅ **Install dependencies** - установка зависимостей
3. ✅ **Run linting** - проверка кода (flake8, black, isort)
4. ✅ **Run migrations** - применение миграций к тестовой БД
5. ✅ **Run tests with coverage** - запуск тестов
6. ✅ **Build and test Docker images** - сборка и тестирование Docker образов
7. ✅ **Deploy to server** - деплой на сервер Yandex Cloud

### 5.3 Проверка деплоя на сервере

**На сервере:**

```bash
# Подключитесь к серверу
ssh ubuntu@<ВАШ_IP_АДРЕС>

# Перейдите в директорию проекта
cd /BookMoose

# Проверьте статус контейнеров
docker-compose ps

# Проверьте логи
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Проверьте последний коммит
git log -1
```

### 5.4 Тестирование приложения

```bash
# Проверьте доступность приложения
curl http://localhost:8000

# Или откройте в браузере
http://<ВАШ_IP_АДРЕС>:8000
```

---

## 6. Устранение неполадок

### 6.1 Workflow не запускается

**Проблема**: Workflow не появляется во вкладке Actions после push

**Решения**:
- ✅ Убедитесь, что файл `.github/workflows/ci.yml` закоммичен и запушен
- ✅ Проверьте, что вы пушите в ветку `feature/library`
- ✅ Убедитесь, что GitHub Actions включен в настройках репозитория
- ✅ Проверьте синтаксис YAML файла (можно использовать онлайн валидатор)

### 6.2 Ошибка подключения SSH

**Проблема**: `Error: Process completed with exit code 255` в шаге Deploy

**Решения**:
- ✅ Проверьте правильность `SERVER_HOST` в Secrets
- ✅ Проверьте правильность `SERVER_USERNAME` в Secrets
- ✅ Убедитесь, что приватный ключ `SERVER_SSH_KEY` скопирован полностью
- ✅ Проверьте, что публичный ключ добавлен в `~/.ssh/authorized_keys` на сервере
- ✅ Убедитесь, что порт 22 открыт в группе безопасности Yandex Cloud
- ✅ Проверьте, что сервер доступен: `ping <ВАШ_IP_АДРЕС>`

### 6.3 Ошибка при выполнении команд на сервере

**Проблема**: Ошибки при выполнении `git pull` или `docker-compose`

**Решения**:
- ✅ Убедитесь, что путь `/BookMoose` существует и доступен
- ✅ Проверьте права доступа: `ls -la /BookMoose`
- ✅ Убедитесь, что Git настроен на сервере
- ✅ Проверьте, что Docker и Docker Compose установлены
- ✅ Убедитесь, что пользователь добавлен в группу docker: `groups`

### 6.4 Ошибки при сборке Docker образов

**Проблема**: Ошибки при выполнении `docker-compose build`

**Решения**:
- ✅ Проверьте наличие файла `docker-compose.yml`
- ✅ Убедитесь, что файл `.env` существует на сервере
- ✅ Проверьте логи: `docker-compose logs`
- ✅ Убедитесь, что на сервере достаточно места: `df -h`

### 6.5 Проблемы с базой данных

**Проблема**: Ошибки подключения к PostgreSQL

**Решения**:
- ✅ Проверьте переменные окружения в `.env`
- ✅ Убедитесь, что контейнер `db` запущен: `docker-compose ps`
- ✅ Проверьте логи БД: `docker-compose logs db`
- ✅ Убедитесь, что миграции применены: `docker-compose exec web python manage.py migrate`

### 6.6 Просмотр логов workflow

1. Перейдите в **Actions** → выберите нужный workflow run
2. Нажмите на шаг, который завершился с ошибкой
3. Разверните секции с логами для детальной информации

### 6.7 Ручной запуск workflow

Если нужно запустить workflow вручную:

1. Перейдите в **Actions** → **CI/CD Pipeline**
2. Нажмите **Run workflow**
3. Выберите ветку и нажмите **Run workflow**

---

## 7. Дополнительные настройки

### 7.1 Настройка домена

Если у вас есть домен:

1. Настройте DNS записи, указывающие на IP-адрес сервера
2. Обновите `ALLOWED_HOSTS` в `.env` на сервере
3. Настройте Nginx для работы с доменом (если используется)

### 7.2 Настройка SSL сертификата

Для HTTPS используйте Let's Encrypt:

```bash
# На сервере
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d ваш-домен.ru
```

### 7.3 Настройка автоматических бэкапов

Рекомендуется настроить автоматические бэкапы базы данных:

```bash
# Создайте скрипт бэкапа
nano /BookMoose/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/BookMoose/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker-compose exec -T db pg_dump -U postgres bookmoose_db > $BACKUP_DIR/backup_$DATE.sql

# Удалите бэкапы старше 7 дней
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

```bash
chmod +x /BookMoose/backup.sh

# Добавьте в crontab (ежедневно в 3:00)
crontab -e
# Добавьте строку:
0 3 * * * /BookMoose/backup.sh
```

---

## 8. Безопасность

### 8.1 Рекомендации по безопасности

- ✅ Используйте сильные пароли для базы данных
- ✅ Ограничьте доступ SSH только с вашего IP-адреса
- ✅ Регулярно обновляйте систему: `sudo apt update && sudo apt upgrade`
- ✅ Используйте firewall (ufw): `sudo ufw enable`
- ✅ Не храните секретные ключи в репозитории
- ✅ Используйте разные ключи для разных серверов
- ✅ Регулярно ротируйте SSH ключи

### 8.2 Настройка firewall

```bash
# На сервере
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

---

## 📞 Поддержка

Если у вас возникли проблемы:

1. Проверьте логи workflow в GitHub Actions
2. Проверьте логи на сервере: `docker-compose logs`
3. Убедитесь, что все шаги из инструкции выполнены
4. Проверьте документацию:
   - [GitHub Actions Documentation](https://docs.github.com/en/actions)
   - [Yandex Cloud Documentation](https://cloud.yandex.ru/docs/)

---

**Успешного деплоя! 🚀**

