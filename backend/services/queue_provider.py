"""
Queue provider abstraction to allow switching drivers (Redis → RabbitMQ in future).

Current implementation: Redis + RQ.
"""
import logging
from typing import Optional

from fastapi import HTTPException

from config import settings

logger = logging.getLogger(__name__)

try:
    import redis  # type: ignore
    from rq import Queue  # type: ignore
    from rq import Retry  # type: ignore
    from rq.job import Job  # type: ignore
except ImportError as e:  # pragma: no cover - ImportError handled at runtime
    redis = None
    Queue = None
    Job = None
    logger.warning(f"RQ not installed: {e}")


class QueueAdapter:
    """Thin adapter to hide queue driver specifics."""

    def __init__(self, driver: str = "redis"):
        self.driver = driver
        self.queue: Optional[Queue] = None
        self.connection = None

        if driver == "redis":
            if not redis or not Queue:
                raise HTTPException(
                    status_code=503,
                    detail="Queue driver redis selected but rq/redis is not installed.",
                )
            self._init_redis_connection()
        else:
            raise HTTPException(status_code=503, detail=f"Queue driver '{driver}' is not supported yet.")

    def _init_redis_connection(self):
        """Инициализирует соединение с Redis. Вызывается при создании и переподключении."""
        try:
            # Поддержка TLS для Upstash и других провайдеров
            redis_url = settings.REDIS_URL
            
            # Логируем информацию о подключении (без пароля)
            safe_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
            logger.info(f"🔌 QueueAdapter: connecting to Redis at {safe_url}")
            
            # Если URL начинается с rediss://, используем SSL
            use_ssl = redis_url.startswith("rediss://")
            
            # Для RQ с decode_responses=False и SSL (rediss://) нужно использовать специальный подход
            # redis.from_url() автоматически определяет SSL по префиксу rediss://
            # Но для RQ с decode_responses=False может быть проблема с SSL параметрами
            # Используем from_url с минимальными параметрами - rediss:// уже указывает на SSL
            try:
                # Пробуем использовать from_url - он должен автоматически обработать rediss://
                self.connection = redis.from_url(
                    redis_url,
                    decode_responses=False,  # RQ требует bytes
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    socket_keepalive=True,
                    socket_keepalive_options={}
                )
            except (TypeError, AttributeError) as e:
                # Если from_url не работает с SSL для decode_responses=False, используем ручное создание
                if use_ssl and "ssl" in str(e).lower():
                    import ssl
                    from urllib.parse import urlparse
                    
                    # Парсим URL вручную
                    parsed = urlparse(redis_url)
                    
                    # Создаем ConnectionPool с SSL через connection_kwargs
                    pool = redis.ConnectionPool(
                        host=parsed.hostname,
                        port=parsed.port or 6379,
                        password=parsed.password,
                        db=int(parsed.path.lstrip('/')) if parsed.path else 0,
                        decode_responses=False,
                        connection_kwargs={
                            "ssl_cert_reqs": ssl.CERT_NONE,
                        },
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        retry_on_timeout=True,
                        health_check_interval=30,
                        socket_keepalive=True,
                        socket_keepalive_options={}
                    )
                    self.connection = redis.Redis(connection_pool=pool)
                else:
                    raise
            
            # Проверяем соединение с таймаутом
            self.connection.ping()
            self.queue = Queue("wireframes", connection=self.connection, default_timeout=90)
            logger.info(f"✅ QueueAdapter initialized with Redis RQ (TLS: {use_ssl}, queue: wireframes)")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"❌ Redis connection error: {e}")
            self.connection = None
            self.queue = None
            raise HTTPException(
                status_code=503,
                detail=f"Redis connection failed: {str(e)}. Please check REDIS_URL format (use rediss:// for TLS)."
            )
        except redis.exceptions.TimeoutError as e:
            logger.error(f"❌ Redis timeout: {e}")
            self.connection = None
            self.queue = None
            raise HTTPException(
                status_code=503,
                detail=f"Redis connection timeout: {str(e)}. Redis may be slow or unavailable."
            )
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {type(e).__name__}: {e}", exc_info=True)
            self.connection = None
            self.queue = None
            raise HTTPException(
                status_code=503,
                detail=f"Redis connection failed: {str(e)}. Please check REDIS_URL or use synchronous generation."
            )

    def _ensure_connection(self):
        """Проверяет соединение и переподключается при необходимости."""
        if self.connection is None or self.queue is None:
            logger.debug("QueueAdapter: connection lost, reconnecting...")
            self._init_redis_connection()
        else:
            try:
                # Проверяем соединение
                self.connection.ping()
            except Exception as e:
                logger.warning(f"QueueAdapter: connection check failed ({e}), reconnecting...")
                self.connection = None
                self.queue = None
                self._init_redis_connection()

    def enqueue(self, func, *args, **kwargs):
        """Ставит задачу в очередь. Автоматически переподключается при потере соединения."""
        self._ensure_connection()
        
        if not self.queue:
            raise HTTPException(status_code=503, detail="Queue is not initialized")
        
        try:
            # Позволяем переопределить retry через kwargs, но ставим дефолт для надёжности
            retry = kwargs.pop("retry", Retry(max=3, interval=[1, 2, 2]))
            job = self.queue.enqueue(func, *args, retry=retry, **kwargs)
            return job
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            logger.warning(f"QueueAdapter: enqueue failed ({e}), attempting reconnect...")
            # Пытаемся переподключиться один раз
            try:
                self.connection = None
                self.queue = None
                self._init_redis_connection()
                retry = kwargs.pop("retry", Retry(max=3, interval=[1, 2, 2]))
                job = self.queue.enqueue(func, *args, retry=retry, **kwargs)
                return job
            except Exception as reconnect_error:
                logger.error(f"QueueAdapter: reconnect failed: {reconnect_error}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Redis unavailable: {str(reconnect_error)}. Please check Redis connection."
                )

    def get_job(self, job_id: str) -> Optional[Job]:
        """Получает задачу по ID. Возвращает None при ошибке."""
        if not Job:
            return None
        
        if self.connection is None:
            return None
        
        try:
            # Проверяем соединение перед использованием
            self.connection.ping()
            return Job.fetch(job_id, connection=self.connection)
        except Exception as e:
            logger.debug(f"QueueAdapter: get_job failed for {job_id}: {e}")
            return None


# Singleton для кеширования экземпляра QueueAdapter
_adapter_instance: Optional[QueueAdapter] = None


def get_queue_adapter(driver: str = "redis") -> Optional[QueueAdapter]:
    """
    Получает кешированный экземпляр QueueAdapter или создает новый.
    Возвращает None если Redis недоступен (graceful degradation).
    
    Args:
        driver: Драйвер очереди (по умолчанию "redis")
    
    Returns:
        QueueAdapter или None если недоступен
    """
    global _adapter_instance
    
    if _adapter_instance is not None:
        try:
            # Проверяем, что соединение еще работает
            if _adapter_instance.connection:
                _adapter_instance.connection.ping()
                logger.debug("QueueAdapter: cached instance connection OK")
                return _adapter_instance
            else:
                # Соединение потеряно, сбрасываем и создаем новое
                logger.warning("⚠️ QueueAdapter: cached instance lost connection, resetting...")
                _adapter_instance = None
        except Exception as e:
            # Соединение не работает, сбрасываем и создаем новое
            logger.warning(f"⚠️ QueueAdapter: cached instance connection check failed ({e}), resetting...")
            _adapter_instance = None
    
    # Создаем новый экземпляр
    try:
        _adapter_instance = QueueAdapter(driver=driver)
        logger.info(f"✅ QueueAdapter initialized successfully (driver: {driver})")
        return _adapter_instance
    except HTTPException as e:
        # Redis недоступен, возвращаем None для graceful degradation
        logger.warning(f"⚠️ QueueAdapter: Redis unavailable for queue operations (driver: {driver}): {e.detail}")
        return None
    except Exception as e:
        logger.error(f"❌ QueueAdapter: unexpected error creating adapter: {e}", exc_info=True)
        return None


def reset_queue_adapter():
    """Сбрасывает кешированный экземпляр (для тестирования или принудительного переподключения)."""
    global _adapter_instance
    _adapter_instance = None

