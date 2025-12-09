# Инструкция по деплою на Render.com

## Автоматическое применение миграций (для бесплатной версии)

**Решение для бесплатной версии Render.com:** Миграции применяются автоматически через Docker ENTRYPOINT при каждом старте контейнера.

### Как это работает:

1. **Dockerfile** настроен с `ENTRYPOINT`, который автоматически применяет миграции перед запуском приложения
2. Миграции применяются при каждом деплое и рестарте контейнера
3. **Alembic не применяет миграции повторно** - он проверяет таблицу `alembic_version` в БД
4. Если миграция уже применена, она просто пропускается

### Если у вас есть доступ к Pre-Deploy Command (платная версия):

В Render.com Dashboard для вашего Web Service:

1. Перейдите в **Settings** → **Build & Deploy**
2. Найдите поле **Pre-Deploy Command (Optional)**
3. В это поле укажите:
```bash
cd backend && bash migrate.sh
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

## Ручное применение миграций (если автоматическое не работает)

### Вариант 1: Через Docker Command (если доступен)

В Render.com Dashboard:
1. Перейдите в **Settings** → **Build & Deploy**
2. Найдите поле **Docker Command**
3. В это поле укажите:
```bash
bash -c "cd backend && bash migrate.sh && uvicorn main:app --host 0.0.0.0 --port 8000"
```

### Вариант 2: Через Shell (если доступен на вашем плане)

1. В Render.com Dashboard откройте ваш Web Service
2. Перейдите в **Shell** или **Console** (вкладка в верхнем меню)
3. Выполните одну из команд:

**Через скрипт миграции:**
```bash
cd /app/backend
bash migrate.sh
```

**Напрямую через Alembic:**
```bash
cd /app/backend
alembic upgrade head
```

После выполнения вы увидите сообщение:
```
✅ Миграции выполнены успешно!
```

### Вариант 3: Локально перед деплоем

Если у вас нет доступа к Shell, можно применить миграции локально перед пушем:

```bash
cd backend
export DATABASE_URL="your-production-database-url"
bash migrate.sh
```

Затем задеплойте изменения.

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

