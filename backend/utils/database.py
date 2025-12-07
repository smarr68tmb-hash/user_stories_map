"""
Настройка базы данных и сессий
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

logger = logging.getLogger(__name__)

# Настройка подключения
connect_args = {}
if settings.is_sqlite():
    connect_args = {"check_same_thread": False}

# Настройки пула соединений для PostgreSQL (особенно важно для Supabase)
pool_kwargs = {
    "pool_pre_ping": True,  # Проверка соединения перед использованием
}

# Для PostgreSQL (включая Supabase) устанавливаем ограничения пула
if not settings.is_sqlite():
    import os
    # Supabase Session mode имеет очень строгое ограничение на количество соединений
    # Для избежания ошибки MaxClientsInSessionMode используем минимальные настройки
    # Рекомендуется использовать Transaction mode pooler Supabase (порт 6543) вместо Session mode (порт 5432)
    # Можно переопределить через переменные окружения
    pool_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "2")),  # Минимум 2 соединения (для Supabase Free/Pro планов)
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),  # Не создавать дополнительные соединения сверх pool_size
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),  # Переиспользовать соединения каждые 1800 секунд (30 минут)
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "20")),  # Таймаут ожидания соединения из пула (20 секунд)
        "pool_reset_on_return": "commit",  # Сбрасывать транзакции при возврате соединения в пул
    })

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **pool_kwargs
)

# Логирование настроек пула для отладки
if not settings.is_sqlite():
    logger.info(f"📊 Database pool settings: pool_size={pool_kwargs.get('pool_size')}, "
                f"max_overflow={pool_kwargs.get('max_overflow')}, "
                f"pool_recycle={pool_kwargs.get('pool_recycle')}s")
    # Предупреждение о Supabase Session mode
    if "pooler.supabase.com" in settings.DATABASE_URL and ":5432" in settings.DATABASE_URL:
        logger.warning("⚠️  Используется Supabase Session mode (порт 5432) - очень строгие ограничения!")
        logger.warning("💡 Рекомендуется использовать Transaction mode pooler (порт 6543) для лучшей производительности")
        logger.warning("💡 Измените DATABASE_URL: замените порт 5432 на 6543 и добавьте ?pgbouncer=true")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency для получения DB сессии"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

