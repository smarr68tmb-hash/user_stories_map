"""
AI User Story Mapper - Main Application
Рефакторенная модульная версия
"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Загрузка .env файла, если он существует
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Импорт конфигурации (валидация происходит здесь)
from config import settings

# Импорт утилит безопасности
from utils.security import SecureLoggingMiddleware

# Настройка логирования
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация Sentry (опционально)
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized")
    except ImportError:
        logger.warning("Sentry SDK not installed. Error tracking disabled.")
else:
    logger.info("Sentry DSN not configured. Error tracking disabled.")

# Создание таблиц в БД (только для development, в production используйте миграции Alembic)
from models import Base
from utils.database import engine
# В production таблицы должны создаваться через миграции Alembic, а не автоматически
# Это предотвращает создание лишних соединений при деплое
if settings.ENVIRONMENT == "development":
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified (development mode)")
    except Exception as e:
        logger.warning(f"⚠️  Could not create tables automatically: {e}")
        logger.info("💡 Use 'alembic upgrade head' to run migrations in production")

# Создание FastAPI приложения
app = FastAPI(
    title="AI User Story Mapper",
    version="2.0.0",
    description="Модульная версия с улучшенной архитектурой"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Secure logging middleware - маскирует пароли и токены в логах
# ВАЖНО: добавляется ДО CORS, чтобы CORS обрабатывался первым
app.add_middleware(SecureLoggingMiddleware)

# CORS настройки (должен быть последним из middleware для правильной обработки OPTIONS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Подключение роутеров
from api import health, auth, projects, stories, analysis

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(stories.router)
app.include_router(analysis.router)


@app.on_event("startup")
async def run_migrations_on_startup():
    """
    Автоматическое применение миграций при старте приложения.
    Это fallback, если миграции не были применены через Build Command.
    """
    try:
        import subprocess
        import os
        from pathlib import Path
        
        # Проверяем, нужно ли применять миграции
        # Пропускаем если это SQLite (для локальной разработки)
        if settings.DATABASE_URL.startswith("sqlite"):
            logger.info("📦 SQLite detected, skipping automatic migrations (use migrate.sh manually)")
            return
        
        # Проверяем, есть ли скрипт миграции
        backend_dir = Path(__file__).parent
        migrate_script = backend_dir / "migrate.sh"
        
        if not migrate_script.exists():
            logger.warning("⚠️ migrate.sh not found, skipping automatic migrations")
            return
        
        logger.info("🔄 Checking database migrations...")
        
        # Запускаем миграции в фоне (не блокируем старт приложения)
        try:
            result = subprocess.run(
                ["bash", str(migrate_script)],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=30,
                env=os.environ.copy()
            )
            
            if result.returncode == 0:
                logger.info("✅ Database migrations applied successfully")
            else:
                logger.warning(f"⚠️ Migration script returned non-zero exit code: {result.returncode}")
                logger.warning(f"Migration output: {result.stdout}")
                logger.warning(f"Migration errors: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("❌ Migration script timed out after 30 seconds")
        except Exception as e:
            logger.warning(f"⚠️ Failed to run migrations automatically: {e}")
            logger.info("💡 You can apply migrations manually: cd backend && bash migrate.sh")
            
    except Exception as e:
        logger.warning(f"⚠️ Error during migration check: {e}")
        logger.info("💡 Migrations will need to be applied manually or via Build Command")


logger.info(f"✅ Application started successfully")
logger.info(f"📦 Database: {settings.DATABASE_URL.split('@')[0] if '@' in settings.DATABASE_URL else settings.DATABASE_URL.split('///')[0]}")
logger.info(f"🤖 AI Provider: {settings.API_PROVIDER}")
logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
logger.info(f"🔒 Secure logging: enabled (sensitive data masked)")
logger.info(f"🍪 Cookie settings: SameSite={settings.COOKIE_SAMESITE}, Secure={settings.COOKIE_SECURE}, Domain={settings.COOKIE_DOMAIN or '(not set)'}")
logger.info(f"🌐 CORS origins: {settings.get_allowed_origins_list()}")

# Предупреждения о безопасности
if settings.ENVIRONMENT == "production":
    logger.warning("⚠️ PRODUCTION MODE: Убедитесь что используется HTTPS!")
    logger.warning("⚠️ Проверьте настройки reverse proxy (nginx/traefik) для SSL/TLS")
else:
    logger.warning("⚠️ DEVELOPMENT MODE: Не используйте HTTP в production!")
    logger.warning("⚠️ Токены и пароли передаются по сети. В production нужен HTTPS!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
