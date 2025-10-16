FROM python:3.12-slim

WORKDIR /app

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

# Открытие порта
EXPOSE 8000

# Команда запуска (для разработки - runserver)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]