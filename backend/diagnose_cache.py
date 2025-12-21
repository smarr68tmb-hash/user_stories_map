#!/usr/bin/env python3
"""
Диагностический скрипт для проверки работы кеширования AI-ответов в Redis.

Использование:
    python diagnose_cache.py
"""
import sys
import json
import hashlib
from pathlib import Path

# Добавляем путь к backend для импорта
sys.path.insert(0, str(Path(__file__).parent))

from utils.redis_manager import RedisManager
from services.ai_service import get_cache_key

def test_cache_key_generation():
    """Тестирует генерацию ключей кеша"""
    print("=" * 60)
    print("Тест 1: Генерация ключей кеша")
    print("=" * 60)
    
    texts = [
        "Тестовый текст",
        "Тестовый  текст",  # Два пробела
        "Тестовый\nтекст",  # С переносом строки
        "Тестовый\tтекст",  # С табуляцией
    ]
    
    for i, text in enumerate(texts, 1):
        key = get_cache_key(text, prefix="test")
        print(f"\nТекст {i}: {repr(text)}")
        print(f"Ключ: {key}")
        print(f"Хеш: {key.split(':')[1]}")
    
    # Проверяем, что нормализация работает
    text1 = "Текст с   множественными   пробелами"
    text2 = "Текст с множественными пробелами"
    key1 = get_cache_key(text1, prefix="test")
    key2 = get_cache_key(text2, prefix="test")
    
    print(f"\n{'='*60}")
    print("Проверка нормализации:")
    print(f"Текст 1: {repr(text1)}")
    print(f"Текст 2: {repr(text2)}")
    print(f"Ключ 1: {key1}")
    print(f"Ключ 2: {key2}")
    print(f"Ключи совпадают: {key1 == key2}")
    print("=" * 60)


def test_redis_connection():
    """Тестирует подключение к Redis"""
    print("\n" + "=" * 60)
    print("Тест 2: Подключение к Redis")
    print("=" * 60)
    
    redis_client = RedisManager.get_client()
    
    if redis_client is None:
        print("❌ Redis клиент недоступен!")
        print("\nВозможные причины:")
        print("1. Redis не запущен")
        print("2. REDIS_URL не настроен в .env")
        print("3. Проблемы с подключением к Redis серверу")
        return False
    
    try:
        # Проверяем ping
        result = redis_client.ping()
        print(f"✅ Redis ping: {result}")
        
        # Проверяем версию Redis
        info = redis_client.info()
        redis_version = info.get('redis_version', 'unknown')
        print(f"✅ Redis версия: {redis_version}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при подключении к Redis: {e}")
        return False


def test_cache_write_read():
    """Тестирует запись и чтение из кеша"""
    print("\n" + "=" * 60)
    print("Тест 3: Запись и чтение из кеша")
    print("=" * 60)
    
    redis_client = RedisManager.get_client()
    
    if redis_client is None:
        print("❌ Redis клиент недоступен, пропускаем тест")
        return False
    
    test_key = "test:cache:diagnostic"
    test_data = {
        "productName": "Тестовый продукт",
        "personas": ["Пользователь"],
        "map": [{"activity": "Тест", "tasks": []}]
    }
    
    try:
        # Записываем
        print(f"\nЗапись данных в ключ: {test_key}")
        result_json = json.dumps(test_data, ensure_ascii=False)
        print(f"Размер данных: {len(result_json)} байт")
        
        success = redis_client.setex(test_key, 60, result_json)  # TTL 60 секунд
        print(f"Результат setex: {success} (тип: {type(success)})")
        
        if success:
            print("✅ Данные успешно записаны")
        else:
            print("⚠️ setex вернул False")
        
        # Читаем
        print(f"\nЧтение данных из ключа: {test_key}")
        cached = redis_client.get(test_key)
        
        if cached:
            print(f"✅ Данные успешно прочитаны (размер: {len(cached)} байт)")
            parsed = json.loads(cached)
            print(f"Проверка данных: {parsed.get('productName') == test_data['productName']}")
        else:
            print("❌ Данные не найдены в кеше")
            return False
        
        # Проверяем TTL
        ttl = redis_client.ttl(test_key)
        print(f"TTL ключа: {ttl} секунд")
        
        # Удаляем тестовый ключ
        redis_client.delete(test_key)
        print(f"\n✅ Тестовый ключ удален")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с кешем: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_cache_keys():
    """Тестирует генерацию ключей для AI кеша"""
    print("\n" + "=" * 60)
    print("Тест 4: Генерация ключей для AI кеша")
    print("=" * 60)
    
    test_texts = [
        "Создать приложение для управления задачами",
        "Создать приложение для управления задачами",  # Дубликат
        "Создать приложение для управления проектами",  # Другой текст
    ]
    
    keys = []
    for i, text in enumerate(test_texts, 1):
        key = get_cache_key(text, prefix="ai_map")
        keys.append(key)
        print(f"\nТекст {i}: {text[:50]}...")
        print(f"Ключ: {key}")
    
    print(f"\n{'='*60}")
    print("Проверка уникальности:")
    print(f"Ключ 1 == Ключ 2 (одинаковый текст): {keys[0] == keys[1]}")
    print(f"Ключ 1 == Ключ 3 (разный текст): {keys[0] == keys[2]}")
    print("=" * 60)


def check_existing_cache_keys():
    """Проверяет существующие ключи в Redis"""
    print("\n" + "=" * 60)
    print("Тест 5: Проверка существующих ключей в Redis")
    print("=" * 60)
    
    redis_client = RedisManager.get_client()
    
    if redis_client is None:
        print("❌ Redis клиент недоступен, пропускаем тест")
        return
    
    try:
        # Ищем ключи с префиксами ai_map и enhance
        patterns = ["ai_map:*", "enhance:*"]
        
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            print(f"\nКлючи с паттерном '{pattern}': {len(keys)}")
            
            if keys:
                for key in keys[:5]:  # Показываем первые 5
                    ttl = redis_client.ttl(key)
                    value = redis_client.get(key)
                    size = len(value) if value else 0
                    print(f"  - {key[:60]}... (TTL: {ttl}s, размер: {size} байт)")
                
                if len(keys) > 5:
                    print(f"  ... и еще {len(keys) - 5} ключей")
            else:
                print(f"  Ключи не найдены")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке ключей: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Запускает все тесты"""
    print("\n" + "=" * 60)
    print("ДИАГНОСТИКА КЕШИРОВАНИЯ AI-ОТВЕТОВ")
    print("=" * 60)
    
    # Тест 1: Генерация ключей
    test_cache_key_generation()
    
    # Тест 2: Подключение к Redis
    redis_available = test_redis_connection()
    
    # Тест 3: Запись и чтение
    if redis_available:
        test_cache_write_read()
        check_existing_cache_keys()
    
    # Тест 4: Генерация ключей для AI
    test_ai_cache_keys()
    
    print("\n" + "=" * 60)
    print("ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 60)
    print("\nРекомендации:")
    print("1. Проверьте логи приложения на наличие ошибок Redis")
    print("2. Убедитесь, что Redis запущен и доступен")
    print("3. Проверьте настройки REDIS_URL в .env")
    print("4. Проверьте права доступа к Redis")
    print("=" * 60)


if __name__ == "__main__":
    main()

