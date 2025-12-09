FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директории для БД
RUN mkdir -p /app && chmod 777 /app

# Делаем скрипты исполняемыми
RUN chmod +x migrate.sh docker-entrypoint.sh

# Открытие порта
EXPOSE 8000

# Используем entrypoint для автоматического применения миграций
ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

