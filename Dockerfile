FROM python:3.13.2

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Проверяем наличие файлов
RUN if [ ! -f pyproject.toml ]; then echo "pyproject.toml not found!" && exit 1; fi
RUN if [ ! -f poetry.lock ]; then echo "poetry.lock not found!" && exit 1; fi

# Настраиваем Poetry
ENV POETRY_VIRTUALENVS_PATH=/app/.venv
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Устанавливаем зависимости (только основные, без dev)
RUN poetry install --only main

# Копируем код проекта
COPY . .

# Выставляем права
RUN chmod -R 755 /app

# Переменные окружения
ENV SECRET_KEY="django-insecure-kunte+d^%hhlph8_@k9i+h88zmo%b+!*qselqzwb989xbcd(a-"
ENV CELERY_BROKER_URL="redis://localhost:6379/1"
ENV CELERY_BACKEND="redis://localhost:6379/1"

# Создаём директорию для медиа
RUN mkdir -p /app/media


EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]