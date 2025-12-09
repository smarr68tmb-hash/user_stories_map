# Инструкция по деплою на Render.com

## Настройка Pre-Deploy Command для автоматического применения миграций

**Важно:** Если вы используете Docker (есть Dockerfile), используйте **Pre-Deploy Command**, а не Build Command.

В Render.com Dashboard для вашего Web Service:

1. Перейдите в **Settings** → **Build & Deploy**
2. Найдите поле **Pre-Deploy Command (Optional)**
3. В это поле укажите:
```bash
cd backend && bash migrate.sh
```

Или если структура проекта другая:
```bash
bash backend/migrate.sh
```

**Pre-Deploy Command выполняется:**
- Автоматически при каждом деплое
- Перед запуском приложения (Start Command)
- Один раз за деплой (не при каждом рестарте)

## Если Build Command доступен (для non-Docker сервисов)

Если вы не используете Docker и видите поле **Build Command**, укажите там:
```bash
pip install -r requirements.txt && cd backend && bash migrate.sh
```

А в **Start Command**:
```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
```

## Переменные окружения (Environment Variables)

Убедитесь, что в Render.com настроены следующие переменные:

### Обязательные:
- `DATABASE_URL` - URL PostgreSQL базы данных
- `JWT_SECRET_KEY` - секретный ключ для JWT (минимум 32 символа)
- `GEMINI_API_KEY` или другой AI API ключ

### Опциональные (для wireframe):
- `REDIS_URL` - URL Redis для очереди (если используется wireframe generation)
- `COOKIE_SAMESITE` - настройки cookie (по умолчанию: "lax")
- `COOKIE_SECURE` - secure cookie (по умолчанию: "false")
- `COOKIE_DOMAIN` - домен для cookie (опционально)

### Другие:
- `ENVIRONMENT` - окружение (production/development)
- `ALLOWED_ORIGINS` - разрешенные CORS origins (через запятую)
- `LOG_LEVEL` - уровень логирования (INFO/DEBUG/WARNING/ERROR)

## Ручное применение миграций (если Pre-Deploy Command не работает)

Если миграции не применяются автоматически, выполните вручную через Shell:

1. В Render.com Dashboard откройте ваш Web Service
2. Перейдите в **Shell** или **Console** (вкладка в верхнем меню)
3. Выполните одну из команд:

**Вариант 1: Через скрипт миграции**
```bash
cd /app/backend
bash migrate.sh
```

**Вариант 2: Напрямую через Alembic**
```bash
cd /app/backend
alembic upgrade head
```

**Вариант 3: Если структура проекта другая**
```bash
cd /app
bash backend/migrate.sh
```

После выполнения вы увидите сообщение:
```
✅ Миграции выполнены успешно!
```

## Проверка состояния миграций

Чтобы проверить, какие миграции применены:

```bash
cd /app/backend
alembic current
alembic history
```

## Troubleshooting

### Ошибка: "column does not exist"
- Убедитесь, что миграции применены: `alembic upgrade head`
- Проверьте, что `DATABASE_URL` указывает на правильную БД

### Ошибка: "alembic: command not found"
- Убедитесь, что `alembic` установлен: `pip install alembic`
- Проверьте, что `requirements.txt` содержит `alembic==1.13.1`

### Миграции не применяются автоматически
- Проверьте Build Command в Render.com
- Убедитесь, что скрипт `migrate.sh` имеет права на выполнение
- Проверьте логи деплоя на наличие ошибок

