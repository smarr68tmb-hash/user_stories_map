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

# Создание таблиц в БД
from models import Base
from utils.database import engine
Base.metadata.create_all(bind=engine)

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

logger.info(f"✅ Application started successfully")
logger.info(f"📦 Database: {settings.DATABASE_URL.split('@')[0] if '@' in settings.DATABASE_URL else settings.DATABASE_URL.split('///')[0]}")
logger.info(f"🤖 AI Provider: {settings.API_PROVIDER}")
logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
logger.info(f"🔒 Secure logging: enabled (sensitive data masked)")

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
