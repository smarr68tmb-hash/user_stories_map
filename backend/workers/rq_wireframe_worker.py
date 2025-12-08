#!/usr/bin/env python3
"""
RQ worker for wireframe generation.

Runs: rq worker wireframes --path backend
"""
import logging
import sys
from pathlib import Path

from rq import Worker, Queue, Connection  # type: ignore

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    import redis  # type: ignore

    redis_url = settings.REDIS_URL
    conn = redis.from_url(redis_url)

    listen_queues = ["wireframes"]
    logger.info(f"Starting RQ worker for queues: {listen_queues}, redis={redis_url}")

    with Connection(conn):
        worker = Worker(map(Queue, listen_queues))
        worker.work()


if __name__ == "__main__":
    main()

