# Деплой на Render.com

## 🚀 Автоматическое применение миграций

**Решение:** Миграции применяются автоматически через Docker ENTRYPOINT при каждом старте контейнера.

### Как это работает:

1. **Dockerfile** настроен с `ENTRYPOINT ["/app/docker-entrypoint.sh"]`
2. Скрипт `docker-entrypoint.sh` автоматически применяет миграции перед запуском приложения
3. Миграции применяются при каждом деплое и рестарте контейнера
4. **Alembic не применяет миграции повторно** - он проверяет таблицу `alembic_version` в БД
5. Если миграция уже применена, она просто пропускается

### Структура файлов:

```
/
├── Dockerfile                    # Корневой Dockerfile для Render
├── backend/
│   ├── docker-entrypoint.sh     # Скрипт для применения миграций
│   ├── migrate.sh               # Скрипт миграций Alembic
│   ├── Dockerfile               # Альтернативный Dockerfile (если деплоите из backend/)
│   └── alembic/                 # Миграции Alembic
```

## 📋 Настройка в Render.com

### 1. Создание Web Service

1. В Render.com Dashboard перейдите в **New +** → **Web Service**
2. Подключите ваш GitHub репозиторий
3. Выберите **Docker** как тип сервиса

### 2. Настройка Build & Deploy

**Build Command:** (оставьте пустым, Docker сам соберет образ)

**Start Command:** (оставьте пустым, используется из Dockerfile CMD)

**Dockerfile Path:** `Dockerfile` (корневой Dockerfile)

### 3. Переменные окружения (Environment Variables)

Убедитесь, что настроены следующие переменные:

#### Обязательные:
- `DATABASE_URL` - URL PostgreSQL базы данных (например, от Supabase)
- `JWT_SECRET_KEY` - секретный ключ для JWT (минимум 32 символа, используйте случайную строку)
- `GEMINI_API_KEY` или другой AI API ключ (Groq, OpenAI)

#### Опциональные (для wireframe):
- `REDIS_URL` - URL Redis для очереди (если используется wireframe generation)
- `COOKIE_SAMESITE` - настройки cookie (по умолчанию: "lax")
- `COOKIE_SECURE` - secure cookie (по умолчанию: "false", установите "true" для HTTPS)
- `COOKIE_DOMAIN` - домен для cookie (опционально)

#### Другие:
- `ENVIRONMENT` - окружение (`production` для production)
- `ALLOWED_ORIGINS` - разрешенные CORS origins (через запятую, например: `https://your-frontend.onrender.com`)
- `LOG_LEVEL` - уровень логирования (`INFO`/`DEBUG`/`WARNING`/`ERROR`)

### 4. Health Check (опционально)

Render автоматически проверяет `/health` endpoint. Убедитесь, что он доступен.

## 🔍 Проверка работы миграций

После деплоя проверьте логи:

1. В Render.com Dashboard откройте ваш Web Service
2. Перейдите в **Logs**
3. Найдите строки:
   ```
   🚀 Starting application deployment...
   🔄 Applying database migrations...
   ✅ Миграции выполнены успешно!
   ✅ Migrations check completed, starting application...
   ```

## 🛠️ Ручное применение миграций (если нужно)

### Вариант 1: Через Shell в Render.com

1. В Render.com Dashboard откройте ваш Web Service
2. Перейдите в **Shell** (если доступен на вашем плане)
3. Выполните:
   ```bash
   cd /app
   bash migrate.sh
   ```

### Вариант 2: Локально перед деплоем

```bash
cd backend
export DATABASE_URL="your-production-database-url"
bash migrate.sh
```

Затем задеплойте изменения.

## 📊 Проверка состояния миграций

Чтобы проверить, какие миграции применены:

```bash
cd /app
alembic current
alembic history
```

## 🐛 Troubleshooting

### Ошибка: "column does not exist" или "share_token does not exist"

**Причина:** Миграции не применены.

**Решение:**
1. Проверьте логи деплоя на наличие ошибок миграций
2. Убедитесь, что `DATABASE_URL` правильно настроен
3. Примените миграции вручную через Shell (если доступен)

### Ошибка: "alembic: command not found"

**Причина:** Alembic не установлен.

**Решение:**
1. Убедитесь, что `requirements.txt` содержит `alembic`
2. Проверьте, что Dockerfile правильно копирует и устанавливает зависимости

### Миграции не применяются автоматически

**Проверьте:**
1. ✅ Dockerfile содержит `ENTRYPOINT ["/app/docker-entrypoint.sh"]`
2. ✅ Скрипт `docker-entrypoint.sh` имеет права на выполнение (`chmod +x`)
3. ✅ Скрипт `migrate.sh` существует и имеет права на выполнение
4. ✅ `DATABASE_URL` настроен в переменных окружения Render.com
5. ✅ Проверьте логи деплоя на наличие ошибок

### Ошибка: "DATABASE_URL is not set"

**Причина:** Переменная окружения `DATABASE_URL` не настроена в Render.com.

**Решение:**
1. Перейдите в Render.com Dashboard → ваш Web Service → **Environment**
2. Добавьте переменную `DATABASE_URL` со значением вашей PostgreSQL БД
3. Перезапустите сервис

## 📝 Новые миграции

При добавлении новых миграций (например, `share_token`):

1. Создайте миграцию локально:
   ```bash
   cd backend
   alembic revision --autogenerate -m "add share_token to projects"
   ```

2. Проверьте миграцию локально:
   ```bash
   alembic upgrade head
   ```

3. Закоммитьте и запушьте изменения:
   ```bash
   git add backend/alembic/versions/your_migration.py
   git commit -m "Add share_token migration"
   git push
   ```

4. Render автоматически применит миграцию при следующем деплое через `docker-entrypoint.sh`

## ✅ Чеклист перед деплоем

- [ ] `DATABASE_URL` настроен в Render.com
- [ ] `JWT_SECRET_KEY` настроен (минимум 32 символа)
- [ ] AI API ключ настроен (GEMINI_API_KEY или другой)
- [ ] `ALLOWED_ORIGINS` настроен для CORS
- [ ] `ENVIRONMENT=production` установлен
- [ ] Все миграции закоммичены и запушены
- [ ] Dockerfile использует `ENTRYPOINT` для миграций
- [ ] Скрипты `docker-entrypoint.sh` и `migrate.sh` имеют права на выполнение

## 🔗 Полезные ссылки

- [Render.com Documentation](https://render.com/docs)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

