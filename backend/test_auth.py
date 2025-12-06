import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert "status" in response.json()


def test_register(client, test_user_credentials):
    response = client.post("/register", json=test_user_credentials)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_credentials["email"]
    assert data["full_name"] == test_user_credentials["full_name"]


def test_login(client, registered_user):
    response = client.post(
        "/token",
        data={"username": registered_user["email"], "password": registered_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh(client, refresh_token):
    response = client.post("/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_logout(client, refresh_token):
    response = client.post("/logout", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


def test_me(client, auth_headers, test_user_credentials):
    response = client.get("/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_credentials["email"]


def test_protected_endpoint_without_token(client):
    response = client.get("/projects")
    assert response.status_code == 401


def test_projects(client, auth_headers):
    response = client.get("/projects", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert isinstance(body["items"], list)

