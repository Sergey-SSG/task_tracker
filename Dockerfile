FROM python:3.12-slim

WORKDIR /app

# Создаем non-root пользователя
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

# Установка системных зависимостей
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание директорий для статики и медиа
RUN mkdir -p /app/staticfiles /app/media

# Сборка статических файлов (выполняется один раз при сборке образа)
RUN python manage.py collectstatic --noinput

# Установка владельца для директорий
RUN chown -R appuser:appuser /app

# Переключение на non-root пользователя
USER appuser

# Открытие порта
EXPOSE 8000

# Команда запуска (Gunicorn)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]