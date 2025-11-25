"""
Конфигурация приложения с валидацией через Pydantic Settings
"""
import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Настройки приложения (упрощенная версия для совместимости)"""
    
    def __init__(self):
        # API Keys
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
        self.API_PROVIDER = os.getenv("API_PROVIDER", "")
        self.API_MODEL = os.getenv("API_MODEL", "")
        self.API_TEMPERATURE = float(os.getenv("API_TEMPERATURE", "0.7"))
        
        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usm.db")
        
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # JWT
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # CORS
        self.ALLOWED_ORIGINS = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        )
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Sentry
        self.SENTRY_DSN = os.getenv("SENTRY_DSN", "")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # Автоопределение провайдера
        self._set_api_provider()
        self._set_default_model()
        self._validate_settings()
    
    def _set_api_provider(self):
        """Автоопределение API провайдера по ключу"""
        if self.API_PROVIDER:
            return
        
        api_key = self.get_api_key()
        if api_key.startswith("pplx-"):
            self.API_PROVIDER = "perplexity"
        elif api_key.startswith("sk-"):
            self.API_PROVIDER = "openai"
        else:
            self.API_PROVIDER = "openai"
    
    def _set_default_model(self):
        """Установка модели по умолчанию"""
        if self.API_MODEL:
            return
        
        if self.API_PROVIDER == "perplexity":
            self.API_MODEL = "sonar"
        else:
            self.API_MODEL = "gpt-4o"
    
    def _validate_settings(self):
        """Валидация настроек при запуске"""
        # Проверка JWT secret в production
        if self.ENVIRONMENT == "production":
            if self.JWT_SECRET_KEY == "your-secret-key-change-in-production":
                logger.error("❌ JWT_SECRET_KEY must be changed in production!")
                raise ValueError("JWT_SECRET_KEY must be set in production")
        
        if len(self.JWT_SECRET_KEY) < 32:
            logger.warning("⚠️ JWT_SECRET_KEY should be at least 32 characters long")
        
        # Предупреждения
        if self.is_sqlite():
            logger.warning("⚠️ SQLite используется! Для production установите DATABASE_URL на PostgreSQL.")
        
        if not self.get_api_key():
            logger.warning("⚠️ AI API key не настроен. AI функции будут недоступны.")
    
    def get_api_key(self) -> str:
        """Возвращает активный API ключ"""
        return self.OPENAI_API_KEY or self.PERPLEXITY_API_KEY
    
    def get_allowed_origins_list(self) -> List[str]:
        """Преобразует ALLOWED_ORIGINS в список"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    def is_sqlite(self) -> bool:
        """Проверяет, используется ли SQLite"""
        return self.DATABASE_URL.startswith("sqlite")


# Singleton instance
settings = Settings()

