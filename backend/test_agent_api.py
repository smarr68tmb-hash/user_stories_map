"""
Тест API с использованием агента
"""
import requests
import json
import sys

API_URL = "http://localhost:8000"

def test_agent_api():
    """Тестирует API с use_agent=true"""
    
    print("="*80)
    print("ТЕСТ API: Генерация карты с агентом (use_agent=true)")
    print("="*80)
    
    # Сначала нужно получить токен (регистрация или логин)
    # Для теста используем простой подход - сначала регистрация
    # Используем abs() чтобы гарантировать положительное число (hash может быть отрицательным)
    test_email = f"test_agent_{abs(hash('test')) % 10000}@test.com"
    test_password = "test123456"
    
    print(f"\n1. Регистрация тестового пользователя: {test_email}")
    try:
        register_response = requests.post(
            f"{API_URL}/register",
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test User"
            },
            timeout=5
        )
        
        if register_response.status_code not in [200, 201, 400]:
            # Если 400 - пользователь уже существует, попробуем логин
            if register_response.status_code == 400:
                print("   Пользователь уже существует, логинимся...")
            else:
                print(f"   Ошибка регистрации: {register_response.status_code}")
                print(f"   Ответ: {register_response.text}")
                return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Не удалось подключиться к серверу")
        print("   Запустите сервер: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"   Ошибка: {e}")
        return False
    
    # Логин
    print("\n2. Логин...")
    try:
        login_response = requests.post(
            f"{API_URL}/token",
            data={
                "username": test_email,
                "password": test_password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        
        if login_response.status_code != 200:
            print(f"   ❌ Ошибка логина: {login_response.status_code}")
            print(f"   Ответ: {login_response.text}")
            return False
        
        token_data = login_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            print("   ❌ Токен не получен")
            return False
        
        print("   ✅ Токен получен")
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False
    
    # Генерация карты с агентом
    print("\n3. Генерация карты с агентом (use_agent=true)...")
    requirements = """
    Мобильное приложение для доставки еды.
    Пользователи могут заказывать еду из ресторанов, отслеживать заказы, оплачивать онлайн.
    Курьеры принимают заказы и доставляют их.
    """
    
    try:
        generate_response = requests.post(
            f"{API_URL}/generate-map",
            json={
                "text": requirements,
                "use_agent": True,  # ← Включаем агента
                "skip_enhancement": False
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=60
        )
        
        if generate_response.status_code != 200:
            print(f"   ❌ Ошибка генерации: {generate_response.status_code}")
            print(f"   Ответ: {generate_response.text}")
            return False
        
        result = generate_response.json()
        
        print("   ✅ Генерация успешна!")
        print(f"\n   📊 Результат:")
        print(f"      - Project ID: {result.get('project_id')}")
        print(f"      - Project Name: {result.get('project_name')}")
        
        # Проверяем метаданные агента
        agent_metadata = result.get("agent_metadata")
        if agent_metadata:
            print(f"\n   🤖 Метаданные агента:")
            
            validation = agent_metadata.get("validation", {})
            if validation:
                print(f"      - Валидация:")
                print(f"        * Валидна: {validation.get('is_valid', 'N/A')}")
                print(f"        * Score: {validation.get('score', 'N/A')}")
                print(f"        * Score (raw): {validation.get('score_raw', 'N/A')}")
                print(f"        * Проблем: {len(validation.get('issues', []))}")
                print(f"        * Рекомендации: {len(validation.get('recommendations', []))}")
            
            similarity = agent_metadata.get("similarity")
            if similarity:
                stats = similarity.get("stats", {})
                print(f"      - Similarity:")
                print(f"        * Групп похожих: {stats.get('similar_groups_found', 0)}")
                print(f"        * Дубликатов: {stats.get('duplicates_found', 0)}")
            
            metrics = agent_metadata.get("metrics", {})
            if metrics:
                print(f"      - Метрики:")
                print(f"        * Общее время: {metrics.get('total_time', 0):.2f}s")
                print(f"        * Время генерации: {metrics.get('generation_time', 0):.2f}s")
                print(f"        * Время валидации: {metrics.get('validation_time', 0):.2f}s")
                print(f"        * Провайдер: {metrics.get('provider_used', 'N/A')}")
                print(f"        * Исправление: {'Да' if metrics.get('fix_attempted') else 'Нет'}")
                if metrics.get('fix_attempted'):
                    print(f"        * Исправлено проблем: {metrics.get('critical_issues_before_fix', 0) - metrics.get('critical_issues_after_fix', 0)}")
        else:
            print("   ⚠️  Метаданные агента отсутствуют")
            return False
        
        print("\n   ✅ Все проверки пройдены!")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 ТЕСТИРОВАНИЕ API С АГЕНТОМ\n")
    
    success = test_agent_api()
    
    if success:
        print("\n" + "="*80)
        print("🎉 ТЕСТ API ПРОЙДЕН УСПЕШНО!")
        print("="*80)
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ ТЕСТ API ПРОВАЛЕН")
        print("="*80)
        sys.exit(1)

