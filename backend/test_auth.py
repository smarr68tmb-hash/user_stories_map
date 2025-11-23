#!/usr/bin/env python3
"""
Скрипт для тестирования аутентификации и миграций
"""
import requests
import json
import sys

API_URL = "http://127.0.0.1:8000"

def test_health():
    """Тест health check"""
    print("🔍 Тестирование health check...")
    try:
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        print("✅ Health check работает")
        return True
    except Exception as e:
        print(f"❌ Health check не работает: {e}")
        return False

def test_ready():
    """Тест readiness check"""
    print("\n🔍 Тестирование readiness check...")
    try:
        response = requests.get(f"{API_URL}/ready")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Readiness check работает: {json.dumps(data, indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Readiness check не работает: {e}")
        return False

def test_register():
    """Тест регистрации"""
    print("\n🔍 Тестирование регистрации...")
    test_email = f"test_{hash('test') % 10000}@example.com"
    test_password = "testpass123"
    
    try:
        response = requests.post(
            f"{API_URL}/register",
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test User"
            }
        )
        if response.status_code == 201:
            print(f"✅ Регистрация успешна: {test_email}")
            return test_email, test_password
        elif response.status_code == 400 and "already registered" in response.json().get("detail", ""):
            print(f"⚠️  Пользователь уже существует, используем существующий")
            return test_email, test_password
        else:
            print(f"❌ Ошибка регистрации: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Ошибка при регистрации: {e}")
        return None, None

def test_login(email, password):
    """Тест логина"""
    print("\n🔍 Тестирование логина...")
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={
                "username": email,
                "password": password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ Логин успешен, получен токен")
            return token
        else:
            print(f"❌ Ошибка логина: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка при логине: {e}")
        return None

def test_me(token):
    """Тест получения информации о пользователе"""
    print("\n🔍 Тестирование /me endpoint...")
    try:
        response = requests.get(
            f"{API_URL}/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Получена информация о пользователе: {json.dumps(user_data, indent=2)}")
            return True
        else:
            print(f"❌ Ошибка получения информации: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при запросе /me: {e}")
        return False

def test_protected_endpoint_without_token():
    """Тест защищенного эндпоинта без токена"""
    print("\n🔍 Тестирование защищенного эндпоинта без токена...")
    try:
        response = requests.get(f"{API_URL}/projects")
        if response.status_code == 401:
            print("✅ Защита работает: 401 Unauthorized без токена")
            return True
        else:
            print(f"❌ Защита не работает: получили {response.status_code} вместо 401")
            return False
    except Exception as e:
        print(f"❌ Ошибка при тесте защиты: {e}")
        return False

def test_projects(token):
    """Тест получения списка проектов"""
    print("\n🔍 Тестирование получения списка проектов...")
    try:
        response = requests.get(
            f"{API_URL}/projects",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            projects = response.json()
            print(f"✅ Получен список проектов: {len(projects.get('items', []))} проектов")
            return True
        else:
            print(f"❌ Ошибка получения проектов: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при запросе проектов: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ И МИГРАЦИЙ")
    print("=" * 60)
    
    results = []
    
    # Тест 1: Health check
    results.append(("Health Check", test_health()))
    
    # Тест 2: Readiness check
    results.append(("Readiness Check", test_ready()))
    
    # Тест 3: Регистрация
    email, password = test_register()
    results.append(("Регистрация", email is not None))
    
    if not email:
        print("\n❌ Не удалось зарегистрировать пользователя. Остановка тестов.")
        sys.exit(1)
    
    # Тест 4: Логин
    token = test_login(email, password)
    results.append(("Логин", token is not None))
    
    if not token:
        print("\n❌ Не удалось получить токен. Остановка тестов.")
        sys.exit(1)
    
    # Тест 5: /me endpoint
    results.append(("Получение информации о пользователе", test_me(token)))
    
    # Тест 6: Защита эндпоинтов
    results.append(("Защита эндпоинтов", test_protected_endpoint_without_token()))
    
    # Тест 7: Получение проектов
    results.append(("Получение списка проектов", test_projects(token)))
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nИтого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} тестов не пройдено")
        sys.exit(1)

if __name__ == "__main__":
    main()

