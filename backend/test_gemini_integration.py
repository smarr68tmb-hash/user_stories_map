"""
Тестовый скрипт для проверки Gemini API интеграции
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем модули
from config import settings
from services.ai_service import (
    gemini_client,
    rate_limiter,
    _get_model_for_provider,
    _call_gemini_api
)


def test_configuration():
    """Проверка конфигурации"""
    print("=" * 60)
    print("1. Проверка конфигурации")
    print("=" * 60)

    print(f"✓ GEMINI_API_KEY: {'Установлен' if settings.GEMINI_API_KEY else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"✓ AI_PROVIDER_PRIORITY: {settings.AI_PROVIDER_PRIORITY}")
    print(f"✓ Available providers: {settings.get_available_providers()}")
    print(f"✓ Gemini Enhancement Model: {settings.GEMINI_ENHANCEMENT_MODEL}")
    print(f"✓ Gemini Generation Model: {settings.GEMINI_GENERATION_MODEL}")
    print(f"✓ Gemini Assistant Model: {settings.GEMINI_ASSISTANT_MODEL}")
    print(f"✓ Gemini Pro Limit: {settings.GEMINI_PRO_LIMIT} RPD")
    print(f"✓ Gemini Flash Limit: {settings.GEMINI_FLASH_LIMIT} RPD")
    print()


def test_client_initialization():
    """Проверка инициализации клиента"""
    print("=" * 60)
    print("2. Проверка инициализации Gemini клиента")
    print("=" * 60)

    if gemini_client:
        print("✓ Gemini client initialized successfully")
    else:
        print("❌ Gemini client NOT initialized")
        return False

    print()
    return True


def test_rate_limiter():
    """Проверка rate limiter"""
    print("=" * 60)
    print("3. Проверка Rate Limiter")
    print("=" * 60)

    # Тестируем счетчик
    rate_limiter.increment("gemini", "gemini-2.0-flash-exp")
    count = rate_limiter.get_count("gemini", "gemini-2.0-flash-exp")
    print(f"✓ Rate limiter test: Count = {count}")

    # Проверяем should_skip
    should_skip = rate_limiter.should_skip_provider("gemini", "gemini-2.0-flash-exp")
    print(f"✓ Should skip provider: {should_skip}")

    print()
    return True


def test_model_selection():
    """Проверка выбора моделей"""
    print("=" * 60)
    print("4. Проверка выбора моделей")
    print("=" * 60)

    enhancement_model = _get_model_for_provider("gemini", is_enhancement=True, task_type="enhancement")
    generation_model = _get_model_for_provider("gemini", is_enhancement=False, task_type="generation")
    assistant_model = _get_model_for_provider("gemini", is_enhancement=False, task_type="assistant")

    print(f"✓ Enhancement model: {enhancement_model}")
    print(f"✓ Generation model: {generation_model}")
    print(f"✓ Assistant model: {assistant_model}")

    print()
    return True


def test_api_call():
    """Тестовый запрос к Gemini API"""
    print("=" * 60)
    print("5. Тестовый запрос к Gemini API")
    print("=" * 60)

    if not gemini_client:
        print("❌ Gemini client not initialized, skipping API test")
        return False

    try:
        messages = [
            {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко на русском языке."},
            {"role": "user", "content": "Скажи 'Привет! Интеграция работает!' одним предложением в JSON формате: {\"message\": \"...\"}\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."}
        ]

        model = settings.GEMINI_ENHANCEMENT_MODEL
        print(f"→ Отправляю запрос к модели {model}...")

        response_text = _call_gemini_api(messages, model, temperature=0.7, timeout=30.0)

        print(f"✓ Получен ответ от Gemini API:")
        print(f"  {response_text[:200]}...")

        # Увеличиваем счетчик
        rate_limiter.increment("gemini", model)

        return True

    except Exception as e:
        print(f"❌ Ошибка при вызове Gemini API: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ GEMINI API ИНТЕГРАЦИИ")
    print("=" * 60 + "\n")

    results = []

    # Запуск тестов
    test_configuration()
    results.append(("Client Init", test_client_initialization()))
    results.append(("Rate Limiter", test_rate_limiter()))
    results.append(("Model Selection", test_model_selection()))

    # API тест только если клиент инициализирован
    if gemini_client:
        results.append(("API Call", test_api_call()))
    else:
        print("⚠️ Пропускаю API тест - Gemini client не инициализирован")
        print("   Установите GEMINI_API_KEY в .env файле\n")

    # Результаты
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("=" * 60)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:<20} {status}")

    all_passed = all(result for _, result in results)
    print("=" * 60)

    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")

    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
