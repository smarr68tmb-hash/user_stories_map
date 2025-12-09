#!/bin/bash
# Entrypoint скрипт для Docker контейнера
# Применяет миграции перед запуском приложения

set -e

echo "🚀 Starting application..."

# Переходим в директорию backend
cd /app/backend || cd /app

# Применяем миграции (Alembic не применит их повторно, если они уже применены)
echo "🔄 Applying database migrations..."
if [ -f "migrate.sh" ]; then
    bash migrate.sh
elif [ -f "backend/migrate.sh" ]; then
    cd backend && bash migrate.sh
else
    # Fallback: напрямую через alembic
    if command -v alembic &> /dev/null; then
        alembic upgrade head || echo "⚠️ Migration failed, but continuing..."
    else
        echo "⚠️ Alembic not found, skipping migrations"
    fi
fi

# Запускаем приложение
echo "✅ Migrations completed, starting application..."
exec "$@"

