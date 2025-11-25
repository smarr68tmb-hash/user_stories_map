import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from utils.database import get_db, SessionLocal
from models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Тестовая база данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Переопределяем get_db для тестов
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# Вспомогательная функция для создания тестового пользователя и получения токена
def get_test_user_token():
    """Создает тестового пользователя и возвращает access token"""
    # Регистрация пользователя
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "testpass123"}
    )
    
    # Логин для получения токена
    response = client.post(
        "/token",
        data={"username": "test@example.com", "password": "testpass123"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


# Получаем токен для всех тестов
test_token = None

@pytest.fixture(autouse=True)
def setup_auth():
    """Автоматически получаем токен перед каждым тестом"""
    global test_token
    if test_token is None:
        test_token = get_test_user_token()


def get_auth_headers():
    """Возвращает заголовки с авторизацией"""
    return {"Authorization": f"Bearer {test_token}"}


def test_generate_map_no_api_key():
    """Тест генерации карты без API ключа"""
    with patch('services.ai_service.client', None):
        response = client.post(
            "/generate-map", 
            json={"text": "Test requirements"}, 
            headers=get_auth_headers()
        )
        assert response.status_code == 503
        assert "AI API key not configured" in response.json()["detail"]


def test_generate_map_empty_text():
    """Тест с пустым текстом"""
    response = client.post(
        "/generate-map", 
        json={"text": ""}, 
        headers=get_auth_headers()
    )
    assert response.status_code == 400


def test_generate_map_short_text():
    """Тест с слишком коротким текстом"""
    response = client.post(
        "/generate-map", 
        json={"text": "short"}, 
        headers=get_auth_headers()
    )
    assert response.status_code == 400


def test_generate_map_long_text():
    """Тест с слишком длинным текстом"""
    long_text = "a" * 10001
    response = client.post(
        "/generate-map", 
        json={"text": long_text}, 
        headers=get_auth_headers()
    )
    assert response.status_code == 400


def test_get_project_not_found():
    """Тест получения несуществующего проекта"""
    response = client.get("/project/99999", headers=get_auth_headers())
    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]


def test_list_projects_empty():
    """Тест списка проектов (пустая БД)"""
    response = client.get("/projects", headers=get_auth_headers())
    assert response.status_code == 200
    # Список проектов возвращает dict с items, а не просто список
    assert "items" in response.json()
    assert isinstance(response.json()["items"], list)


@patch('services.ai_service.client')
def test_generate_map_rate_limit(mock_client):
    """Тест обработки rate limit ошибки"""
    from openai import RateLimitError
    
    # Создаем mock response
    mock_response = MagicMock()
    mock_response.request = MagicMock()
    
    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body=None
    )
    
    response = client.post(
        "/generate-map", 
        json={"text": "Valid requirements text with enough characters"}, 
        headers=get_auth_headers()
    )
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


@patch('services.ai_service.client')
def test_generate_map_timeout(mock_client):
    """Тест обработки timeout ошибки"""
    from openai import APITimeoutError
    
    mock_client.chat.completions.create.side_effect = APITimeoutError(
        request=MagicMock()
    )
    
    response = client.post(
        "/generate-map", 
        json={"text": "Valid requirements text with enough characters"}, 
        headers=get_auth_headers()
    )
    assert response.status_code == 504


@patch('services.ai_service.client')
def test_generate_map_invalid_json(mock_client):
    """Тест обработки невалидного JSON ответа"""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "not a json"
    mock_client.chat.completions.create.return_value = mock_completion
    
    response = client.post(
        "/generate-map", 
        json={"text": "Valid requirements text with enough characters"}, 
        headers=get_auth_headers()
    )
    assert response.status_code == 502


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

