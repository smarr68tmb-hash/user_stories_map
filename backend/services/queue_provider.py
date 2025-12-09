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
            try:
                self.connection = redis.from_url(settings.REDIS_URL)
                # Проверяем соединение
                self.connection.ping()
                self.queue = Queue("wireframes", connection=self.connection, default_timeout=90)
                logger.info("✅ QueueAdapter initialized with Redis RQ")
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, Exception) as e:
                logger.error(f"❌ Failed to connect to Redis: {e}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Redis connection failed: {str(e)}. Please check REDIS_URL or use synchronous generation."
                )
        else:
            raise HTTPException(status_code=503, detail=f"Queue driver '{driver}' is not supported yet.")

    def enqueue(self, func, *args, **kwargs):
        if not self.queue:
            raise HTTPException(status_code=503, detail="Queue is not initialized")
        # Позволяем переопределить retry через kwargs, но ставим дефолт для надёжности
        retry = kwargs.pop("retry", Retry(max=3, interval=[1, 2, 2]))
        job = self.queue.enqueue(func, *args, retry=retry, **kwargs)
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        if not Job or not self.connection:
            return None
        try:
            return Job.fetch(job_id, connection=self.connection)
        except Exception:
            return None

