import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api import auth, projects, stories, analysis, health
from models import Base
from utils.database import get_db

# Общая тестовая БД в памяти
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Подменяем зависимость БД для всех тестов
app.dependency_overrides[get_db] = override_get_db
# Отключаем rate limiting slowapi в тестах
if hasattr(app.state, "limiter"):
    app.state.limiter.enabled = False
for module in (auth, projects, stories, analysis, health):
    if hasattr(module, "limiter"):
        module.limiter.enabled = False


@pytest.fixture(autouse=True)
def reset_db():
    """Чистая схема перед каждым тестом."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_user_credentials():
    # Пароль удовлетворяет политикам: 8+ символов, верхний/нижний регистр, цифра
    return {
        "email": "test@example.com",
        "password": "Testpass123",
        "full_name": "Test User",
    }


@pytest.fixture
def registered_user(client, test_user_credentials):
    # Регистрация может вернуть 400, если пользователь уже существует — это не критично
    client.post("/register", json=test_user_credentials)
    return test_user_credentials


@pytest.fixture
def tokens(client, registered_user):
    resp = client.post(
        "/token",
        data={"username": registered_user["email"], "password": registered_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    return data["access_token"], data.get("refresh_token")


@pytest.fixture
def auth_headers(tokens):
    access_token, _ = tokens
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def refresh_token(tokens):
    _, refresh = tokens
    return refresh

