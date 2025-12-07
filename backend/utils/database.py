"""
Настройка базы данных и сессий
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

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
    # Supabase Session mode имеет ограничение на количество соединений
    # Рекомендуемые настройки для избежания ошибки MaxClientsInSessionMode
    # Можно переопределить через переменные окружения
    pool_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),  # Максимум 5 постоянных соединений в пуле
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),  # Не создавать дополнительные соединения сверх pool_size
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),  # Переиспользовать соединения каждые 3600 секунд (1 час)
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),  # Таймаут ожидания соединения из пула (30 секунд)
    })

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency для получения DB сессии"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

