#!/bin/bash
# Entrypoint скрипт для Docker контейнера
# Применяет миграции перед запуском приложения
# Используется при деплое на Render.com

set -e

echo "🚀 Starting application deployment..."
echo "📦 Working directory: $(pwd)"

# Переходим в рабочую директорию (файлы уже в /app)
cd /app

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  WARNING: DATABASE_URL is not set"
    echo "⚠️  Migrations will be skipped, but application will start"
    echo "⚠️  Make sure DATABASE_URL is configured in Render.com environment variables"
else
    echo "✅ DATABASE_URL is configured"
fi

# Применяем миграции (Alembic не применит их повторно, если они уже применены)
echo "🔄 Applying database migrations..."
if [ -f "migrate.sh" ]; then
    echo "📄 Using migrate.sh script..."
    bash migrate.sh || {
        echo "⚠️  Migration script failed, but continuing..."
        echo "⚠️  Application will start anyway"
        echo "⚠️  You may need to apply migrations manually"
    }
else
    echo "⚠️  migrate.sh not found, trying direct alembic..."
    # Fallback: напрямую через alembic
    if command -v alembic &> /dev/null; then
        echo "📊 Current migration state:"
        alembic current || echo "⚠️  No migrations applied yet"
        echo "🚀 Applying migrations..."
        alembic upgrade head || {
            echo "⚠️  Direct alembic migration failed, but continuing..."
            echo "⚠️  Application will start anyway"
        }
    else
        echo "⚠️  Alembic not found, skipping migrations"
        echo "⚠️  Make sure alembic is installed: pip install alembic"
    fi
fi

# Запускаем приложение
echo "✅ Migrations check completed, starting application..."
echo "🎯 Executing: $@"
exec "$@"

