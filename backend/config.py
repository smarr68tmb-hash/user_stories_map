"""
Конфигурация приложения с валидацией через Pydantic Settings
"""
import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Настройки приложения (упрощенная версия для совместимости)"""
    
    def __init__(self):
        # API Keys
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.API_PROVIDER = os.getenv("API_PROVIDER", "")
        self.API_MODEL = os.getenv("API_MODEL", "")
        self.API_TEMPERATURE = float(os.getenv("API_TEMPERATURE", "0.7"))

        # Приоритет провайдеров для fallback (через запятую)
        # По умолчанию: gemini (бесплатно), groq, perplexity, openai
        self.AI_PROVIDER_PRIORITY = [
            p.strip() for p in os.getenv("AI_PROVIDER_PRIORITY", "gemini,groq,perplexity,openai").split(",")
            if p.strip()
        ]

        # Two-Stage AI Processing: модель для улучшения требований (Stage 1)
        # Если не указана, используется основная модель (API_MODEL)
        self.ENHANCEMENT_MODEL = os.getenv("ENHANCEMENT_MODEL", "")

        # Gemini модели
        self.GEMINI_ENHANCEMENT_MODEL = os.getenv("GEMINI_ENHANCEMENT_MODEL", "gemini-2.0-flash-exp")
        self.GEMINI_GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.0-flash-exp")
        self.GEMINI_ASSISTANT_MODEL = os.getenv("GEMINI_ASSISTANT_MODEL", "gemini-2.0-flash-exp")

        # Проактивные лимиты (переключаемся ДО исчерпания)
        self.GEMINI_PRO_LIMIT = int(os.getenv("GEMINI_PRO_LIMIT", "45"))  # Из 50 RPD
        self.GEMINI_FLASH_LIMIT = int(os.getenv("GEMINI_FLASH_LIMIT", "230"))  # Из 250 RPD
        
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

        # Определяем провайдера по первому доступному ключу в порядке приоритета
        for provider in self.AI_PROVIDER_PRIORITY:
            if provider == "gemini" and self.GEMINI_API_KEY:
                self.API_PROVIDER = "gemini"
                return
            elif provider == "groq" and self.GROQ_API_KEY:
                self.API_PROVIDER = "groq"
                return
            elif provider == "perplexity" and self.PERPLEXITY_API_KEY:
                self.API_PROVIDER = "perplexity"
                return
            elif provider == "openai" and self.OPENAI_API_KEY:
                self.API_PROVIDER = "openai"
                return

        # Fallback: определяем по формату ключа (для обратной совместимости)
        api_key = self.get_api_key()
        if api_key:
            # Только если ключ существует, определяем провайдера по формату
            if api_key.startswith("gsk_"):
                self.API_PROVIDER = "groq"
            elif api_key.startswith("pplx-"):
                self.API_PROVIDER = "perplexity"
            elif api_key.startswith("sk-"):
                self.API_PROVIDER = "openai"
            elif api_key.startswith("AIza"):
                self.API_PROVIDER = "gemini"
            # Если ключ есть, но формат не распознан, не устанавливаем провайдера
            # (оставляем пустую строку, что означает "не определен")
        # Если ключа нет, оставляем API_PROVIDER пустым (не устанавливаем по умолчанию)
    
    def _set_default_model(self):
        """Установка модели по умолчанию"""
        if self.API_MODEL:
            return

        # Устанавливаем модель только если провайдер определен
        if self.API_PROVIDER == "gemini":
            self.API_MODEL = "gemini-2.0-flash-exp"
        elif self.API_PROVIDER == "groq":
            self.API_MODEL = "llama-3.3-70b-versatile"
        elif self.API_PROVIDER == "perplexity":
            self.API_MODEL = "sonar"
        elif self.API_PROVIDER == "openai":
            self.API_MODEL = "gpt-4o"
        # Если провайдер не определен (нет ключей), оставляем API_MODEL пустым
        # Это предотвращает вводящее в заблуждение состояние
    
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
        
        available_providers = self.get_available_providers()
        if not available_providers:
            logger.warning("⚠️ AI API key не настроен. AI функции будут недоступны.")
        else:
            logger.info(f"✅ Настроены AI провайдеры (в порядке приоритета): {', '.join(available_providers)}")
    
    def get_api_key(self) -> str:
        """Возвращает активный API ключ (для обратной совместимости)"""
        # Возвращаем первый доступный ключ в порядке приоритета
        for provider in self.AI_PROVIDER_PRIORITY:
            if provider == "gemini" and self.GEMINI_API_KEY:
                return self.GEMINI_API_KEY
            elif provider == "groq" and self.GROQ_API_KEY:
                return self.GROQ_API_KEY
            elif provider == "perplexity" and self.PERPLEXITY_API_KEY:
                return self.PERPLEXITY_API_KEY
            elif provider == "openai" and self.OPENAI_API_KEY:
                return self.OPENAI_API_KEY
        return self.GEMINI_API_KEY or self.OPENAI_API_KEY or self.PERPLEXITY_API_KEY or self.GROQ_API_KEY
    
    def get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Возвращает API ключ для конкретного провайдера"""
        if provider == "gemini":
            return self.GEMINI_API_KEY
        elif provider == "groq":
            return self.GROQ_API_KEY
        elif provider == "perplexity":
            return self.PERPLEXITY_API_KEY
        elif provider == "openai":
            return self.OPENAI_API_KEY
        return None
    
    def get_available_providers(self) -> List[str]:
        """Возвращает список доступных провайдеров в порядке приоритета"""
        available = []
        for provider in self.AI_PROVIDER_PRIORITY:
            if self.get_api_key_for_provider(provider):
                available.append(provider)
        return available
    
    def get_enhancement_model(self) -> str:
        """Возвращает модель для Stage 1 (улучшение требований)"""
        return self.ENHANCEMENT_MODEL or self.API_MODEL
    
    def get_allowed_origins_list(self) -> List[str]:
        """Преобразует ALLOWED_ORIGINS в список"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    def is_sqlite(self) -> bool:
        """Проверяет, используется ли SQLite"""
        return self.DATABASE_URL.startswith("sqlite")


# Singleton instance
settings = Settings()

