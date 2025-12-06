from unittest.mock import patch
from fastapi import HTTPException


def test_generate_map_no_api_key(client, auth_headers):
    """Если нет ключа, сервис должен вернуть 503."""
    with patch("api.projects.generate_ai_map") as mock_generate:
        mock_generate.side_effect = HTTPException(
            status_code=503, detail="AI API key not configured"
        )
        response = client.post(
            "/generate-map",
            json={"text": "Test requirements"},
            headers=auth_headers,
        )
    assert response.status_code == 503
    assert "AI API key not configured" in response.json()["detail"]


def test_generate_map_empty_text(client, auth_headers):
    """Тест с пустым текстом"""
    response = client.post(
        "/generate-map", 
        json={"text": ""}, 
        headers=auth_headers
    )
    assert response.status_code == 400


def test_generate_map_short_text(client, auth_headers):
    """Тест с слишком коротким текстом"""
    response = client.post(
        "/generate-map", 
        json={"text": "short"}, 
        headers=auth_headers
    )
    assert response.status_code == 400


def test_generate_map_long_text(client, auth_headers):
    """Тест с слишком длинным текстом"""
    long_text = "a" * 10001
    response = client.post(
        "/generate-map", 
        json={"text": long_text}, 
        headers=auth_headers
    )
    assert response.status_code == 400


def test_get_project_not_found(client, auth_headers):
    """Тест получения несуществующего проекта"""
    response = client.get("/project/99999", headers=auth_headers)
    assert response.status_code == 404
    assert "Project not found" in response.json()["detail"]


def test_list_projects_empty(client, auth_headers):
    """Тест списка проектов (пустая БД)"""
    response = client.get("/projects", headers=auth_headers)
    assert response.status_code == 200
    # Список проектов возвращает dict с items, а не просто список
    assert "items" in response.json()
    assert isinstance(response.json()["items"], list)


def test_generate_map_rate_limit(client, auth_headers):
    """При rate limit должен вернуться 429."""
    with patch("api.projects.generate_ai_map") as mock_generate:
        mock_generate.side_effect = HTTPException(
            status_code=429, detail="Rate limit exceeded"
        )
        response = client.post(
            "/generate-map",
            json={"text": "Valid requirements text with enough characters"},
            headers=auth_headers,
        )
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_generate_map_timeout(client, auth_headers):
    """При таймауте должен вернуться 504."""
    with patch("api.projects.generate_ai_map") as mock_generate:
        mock_generate.side_effect = HTTPException(
            status_code=504, detail="AI request timed out"
        )
        response = client.post(
            "/generate-map",
            json={"text": "Valid requirements text with enough characters"},
            headers=auth_headers,
        )
    assert response.status_code == 504


def test_generate_map_invalid_json(client, auth_headers):
    """При невалидном ответе должен вернуться 502."""
    with patch("api.projects.generate_ai_map") as mock_generate:
        mock_generate.side_effect = HTTPException(
            status_code=502, detail="Invalid AI response"
        )
        response = client.post(
            "/generate-map",
            json={"text": "Valid requirements text with enough characters"},
            headers=auth_headers,
        )
    assert response.status_code == 502

