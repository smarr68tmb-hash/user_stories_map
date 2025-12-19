"""
Redis Manager - централизованная работа с Redis

Упрощает работу с Redis клиентом, аналогично организации тестов в классы.
"""
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Класс для управления Redis соединением.
    
    Аналогично TestRedisCaching в тестах - группирует связанные функции.
    """
    
    _client: Optional[object] = None
    
    @classmethod
    def get_client(cls) -> Optional[object]:
        """
        Получает Redis клиент или возвращает None если недоступен.
        
        Returns:
            Optional[redis.Redis]: Redis клиент или None
        """
        if cls._client is not None:
            try:
                cls._client.ping()
                return cls._client
            except Exception:
                cls._client = None
        
        try:
            import redis
            if not settings.REDIS_URL:
                logger.debug("Redis URL not configured")
                return None
            
            cls._client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            cls._client.ping()
            
            if settings.ENVIRONMENT == "production":
                logger.info("✅ Redis connection established")
            else:
                logger.debug("✅ Redis connection established")
            
            return cls._client
        except Exception as e:
            cls._client = None
            if settings.ENVIRONMENT == "production":
                logger.error(f"❌ Redis unavailable in production: {e}. Caching disabled!")
                # В production можно отправить alert в Sentry
                try:
                    import sentry_sdk
                    sentry_sdk.capture_message(
                        f"Redis connection failed: {e}",
                        level="error"
                    )
                except ImportError:
                    pass
            else:
                logger.warning(f"⚠️ Redis not available in development: {e}. Caching disabled.")
            return None
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Проверяет, доступен ли Redis.
        
        Returns:
            bool: True если Redis доступен
        """
        client = cls.get_client()
        return client is not None
    
    @classmethod
    def reset_client(cls) -> None:
        """
        Сбрасывает кеш клиента (для тестирования или переподключения).
        """
        cls._client = None

