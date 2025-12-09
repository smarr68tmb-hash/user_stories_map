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

# Делаем скрипт миграции исполняемым
RUN chmod +x migrate.sh

# Открытие порта
EXPOSE 8000

# Запуск приложения
# Примечание: миграции должны выполняться через Build Command на Render.com:
# bash migrate.sh && uvicorn main:app --host 0.0.0.0 --port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

