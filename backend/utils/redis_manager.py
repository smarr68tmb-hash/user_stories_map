"""
Redis Manager - централизованная работа с Redis

Упрощает работу с Redis клиентом, аналогично организации тестов в классы.
"""
import logging
from typing import Optional
from config import settings

# Пытаемся импортировать redis, но не критично если не установлен
try:
    import redis
except ImportError:
    redis = None

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
                # Проверяем соединение с таймаутом
                cls._client.ping()
                return cls._client
            except Exception as e:
                logger.debug(f"Redis client ping failed, reconnecting: {e}")
                cls._client = None
        
        try:
            if redis is None:
                logger.debug("Redis library not installed")
                return None
            
            if not settings.REDIS_URL:
                logger.debug("Redis URL not configured")
                return None
            
            # Определяем, нужно ли использовать TLS (rediss:// для Upstash и других провайдеров)
            use_ssl = settings.REDIS_URL.startswith("rediss://")
            
            # Создаем клиент с параметрами таймаутов и переподключения
            cls._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                ssl=use_ssl,  # Включаем SSL для rediss://
                ssl_cert_reqs=None if use_ssl else None,  # Для Upstash не требуется проверка сертификата
                socket_connect_timeout=5,  # Таймаут подключения 5 секунд
                socket_timeout=5,  # Таймаут операций 5 секунд
                retry_on_timeout=True,  # Повторять при таймауте
                health_check_interval=30,  # Проверка здоровья каждые 30 секунд
                socket_keepalive=True,  # Поддержание соединения
                socket_keepalive_options={}  # Опции keepalive
            )
            
            # Проверяем соединение с таймаутом
            cls._client.ping()
            
            if settings.ENVIRONMENT == "production":
                logger.info(f"✅ Redis connection established to {settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else settings.REDIS_URL}")
            else:
                logger.debug(f"✅ Redis connection established to {settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else settings.REDIS_URL}")
            
            return cls._client
        except redis.ConnectionError as e:
            cls._client = None
            error_msg = f"Redis connection error: {e}"
            if settings.ENVIRONMENT == "production":
                logger.error(f"❌ {error_msg}. Caching disabled!")
                try:
                    import sentry_sdk
                    sentry_sdk.capture_message(
                        f"Redis connection failed: {e}",
                        level="error"
                    )
                except ImportError:
                    pass
            else:
                logger.warning(f"⚠️ {error_msg}. Caching disabled.")
                logger.debug(f"💡 Убедитесь, что Redis запущен. URL: {settings.REDIS_URL}")
                logger.debug("💡 Для Docker: docker-compose up redis")
                logger.debug("💡 Для локально: redis-server или brew services start redis")
            return None
        except redis.TimeoutError as e:
            cls._client = None
            error_msg = f"Redis connection timeout: {e}"
            if settings.ENVIRONMENT == "production":
                logger.error(f"❌ {error_msg}. Caching disabled!")
            else:
                logger.warning(f"⚠️ {error_msg}. Проверьте доступность Redis сервера.")
            return None
        except Exception as e:
            cls._client = None
            error_msg = f"Redis error: {type(e).__name__}: {e}"
            if settings.ENVIRONMENT == "production":
                logger.error(f"❌ Redis unavailable in production: {error_msg}. Caching disabled!")
                try:
                    import sentry_sdk
                    sentry_sdk.capture_message(
                        f"Redis connection failed: {e}",
                        level="error"
                    )
                except ImportError:
                    pass
            else:
                logger.warning(f"⚠️ Redis not available in development: {error_msg}. Caching disabled.")
                logger.debug(f"💡 Проверьте REDIS_URL: {settings.REDIS_URL}")
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

