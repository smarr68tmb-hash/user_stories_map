#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Groq Compound моделей

Использование:
    # Тест с текущими моделями (по умолчанию)
    python test_groq_compound.py

    # Тест с Compound моделями
    GROQ_MODEL="groq/compound" GROQ_ENHANCEMENT_MODEL="groq/compound-mini" python test_groq_compound.py

    # Сравнение всех моделей
    python test_groq_compound.py --compare
"""
import os
import sys
import json
import time
from typing import Dict, List, Tuple
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import enhance_requirements, generate_ai_map, provider_registry
from config import settings


# Тестовые данные
TEST_ENHANCEMENT_TEXT = """Требования к приложению:
- Онлайн-бронирование столиков в ресторанах
- Просмотр ресторанов на карте
- Выбор даты и времени
- Подтверждение бронирования"""

TEST_GENERATION_TEXT = """Требования к мобильному приложению для онлайн-бронирования столиков в ресторанах.

Функционал:
- Просмотр доступных ресторанов на интерактивной карте города
- Фильтрация ресторанов по кухне, рейтингу, цене
- Выбор даты, времени и количества гостей для бронирования
- Просмотр меню ресторана
- Получение подтверждения бронирования по email и SMS
- История бронирований пользователя
- Отмена бронирования (минимум за 2 часа до визита)

Ограничения:
- Бронирование возможно за 30 дней вперёд
- Минимальное время для отмены — 2 часа до визита
- Максимальное количество гостей — 20 человек"""


class ModelTester:
    """Класс для тестирования моделей"""
    
    def __init__(self):
        self.results: List[Dict] = []
        
    def test_enhancement(self, model_name: str, test_text: str) -> Dict:
        """Тестирует функцию enhancement"""
        print(f"\n🔄 Тестирую enhancement с моделью: {model_name}")
        
        # Временно устанавливаем модель
        original_model = os.environ.get("GROQ_ENHANCEMENT_MODEL")
        os.environ["GROQ_ENHANCEMENT_MODEL"] = model_name
        
        try:
            start_time = time.time()
            result = enhance_requirements(test_text, redis_client=None, use_cache=False)
            elapsed_time = time.time() - start_time
            
            # Проверяем результат
            is_valid = isinstance(result, dict) and "enhanced_text" in result
            enhanced_length = len(result.get("enhanced_text", "")) if is_valid else 0
            confidence = result.get("confidence", 0) if is_valid else 0
            
            return {
                "task": "enhancement",
                "model": model_name,
                "success": is_valid,
                "time_seconds": round(elapsed_time, 2),
                "enhanced_length": enhanced_length,
                "confidence": confidence,
                "error": None
            }
        except Exception as e:
            return {
                "task": "enhancement",
                "model": model_name,
                "success": False,
                "time_seconds": 0,
                "enhanced_length": 0,
                "confidence": 0,
                "error": str(e)
            }
        finally:
            # Восстанавливаем оригинальную модель
            if original_model:
                os.environ["GROQ_ENHANCEMENT_MODEL"] = original_model
            elif "GROQ_ENHANCEMENT_MODEL" in os.environ:
                del os.environ["GROQ_ENHANCEMENT_MODEL"]
    
    def test_generation(self, model_name: str, test_text: str) -> Dict:
        """Тестирует функцию generation"""
        print(f"\n🔄 Тестирую generation с моделью: {model_name}")
        
        # Временно устанавливаем модель
        original_model = os.environ.get("GROQ_MODEL")
        os.environ["GROQ_MODEL"] = model_name
        
        try:
            start_time = time.time()
            result = generate_ai_map(test_text, redis_client=None, use_cache=False)
            elapsed_time = time.time() - start_time
            
            # Проверяем результат
            is_valid = isinstance(result, dict) and "map" in result
            map_items = len(result.get("map", [])) if is_valid else 0
            personas = len(result.get("personas", [])) if is_valid else 0
            
            return {
                "task": "generation",
                "model": model_name,
                "success": is_valid,
                "time_seconds": round(elapsed_time, 2),
                "map_items": map_items,
                "personas": personas,
                "error": None
            }
        except Exception as e:
            return {
                "task": "generation",
                "model": model_name,
                "success": False,
                "time_seconds": 0,
                "map_items": 0,
                "personas": 0,
                "error": str(e)
            }
        finally:
            # Восстанавливаем оригинальную модель
            if original_model:
                os.environ["GROQ_MODEL"] = original_model
            elif "GROQ_MODEL" in os.environ:
                del os.environ["GROQ_MODEL"]
    
    def print_results(self):
        """Выводит результаты тестирования"""
        print("\n" + "="*80)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("="*80)
        
        # Группируем по задачам
        enhancement_results = [r for r in self.results if r["task"] == "enhancement"]
        generation_results = [r for r in self.results if r["task"] == "generation"]
        
        # Enhancement результаты
        if enhancement_results:
            print("\n📝 ENHANCEMENT (Улучшение требований):")
            print("-" * 80)
            print(f"{'Модель':<30} {'Успех':<10} {'Время (сек)':<15} {'Длина':<10} {'Confidence':<10}")
            print("-" * 80)
            for r in enhancement_results:
                status = "✅" if r["success"] else "❌"
                print(f"{r['model']:<30} {status:<10} {r['time_seconds']:<15} {r['enhanced_length']:<10} {r.get('confidence', 0):<10}")
                if r.get("error"):
                    print(f"  ⚠️  Ошибка: {r['error']}")
        
        # Generation результаты
        if generation_results:
            print("\n🗺️  GENERATION (Генерация карты):")
            print("-" * 80)
            print(f"{'Модель':<30} {'Успех':<10} {'Время (сек)':<15} {'Activities':<12} {'Personas':<10}")
            print("-" * 80)
            for r in generation_results:
                status = "✅" if r["success"] else "❌"
                print(f"{r['model']:<30} {status:<10} {r['time_seconds']:<15} {r['map_items']:<12} {r['personas']:<10}")
                if r.get("error"):
                    print(f"  ⚠️  Ошибка: {r['error']}")
        
        # Сравнение (если есть несколько моделей)
        if len(enhancement_results) > 1:
            self._print_comparison(enhancement_results, "enhancement")
        
        if len(generation_results) > 1:
            self._print_comparison(generation_results, "generation")
    
    def _print_comparison(self, results: List[Dict], task_type: str):
        """Выводит сравнение результатов"""
        successful = [r for r in results if r["success"]]
        if len(successful) < 2:
            return
        
        print(f"\n📈 СРАВНЕНИЕ ({task_type.upper()}):")
        print("-" * 80)
        
        # Находим лучшую по времени
        fastest = min(successful, key=lambda x: x["time_seconds"])
        print(f"⚡ Самая быстрая: {fastest['model']} ({fastest['time_seconds']} сек)")
        
        # Для enhancement - лучшая по confidence
        if task_type == "enhancement":
            best_conf = max(successful, key=lambda x: x.get("confidence", 0))
            print(f"🎯 Высший confidence: {best_conf['model']} ({best_conf.get('confidence', 0)})")
        
        # Для generation - лучшая по количеству элементов
        if task_type == "generation":
            most_items = max(successful, key=lambda x: x.get("map_items", 0))
            print(f"📦 Больше всего элементов: {most_items['model']} ({most_items.get('map_items', 0)} activities)")


def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование Groq Compound моделей")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Сравнить все доступные модели"
    )
    parser.add_argument(
        "--enhancement-only",
        action="store_true",
        help="Тестировать только enhancement"
    )
    parser.add_argument(
        "--generation-only",
        action="store_true",
        help="Тестировать только generation"
    )
    
    args = parser.parse_args()
    
    # Проверяем наличие Groq API ключа
    if not settings.GROQ_API_KEY:
        print("❌ Ошибка: GROQ_API_KEY не установлен!")
        print("Установите переменную окружения: export GROQ_API_KEY='your-key-here'")
        sys.exit(1)
    
    print("🧪 Тестирование Groq моделей")
    print("="*80)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Groq API ключ: {'✅ Установлен' if settings.GROQ_API_KEY else '❌ Не установлен'}")
    
    tester = ModelTester()
    
    # Определяем модели для тестирования
    if args.compare:
        # Сравниваем все модели
        enhancement_models = [
            "llama-3.1-8b-instant",  # Текущая по умолчанию
            "groq/compound-mini",    # Новая Compound Mini
        ]
        generation_models = [
            "llama-3.3-70b-versatile",  # Текущая по умолчанию
            "groq/compound",             # Новая Compound
        ]
    else:
        # Используем модели из переменных окружения или по умолчанию
        enhancement_models = [
            os.getenv("GROQ_ENHANCEMENT_MODEL", "llama-3.1-8b-instant")
        ]
        generation_models = [
            os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        ]
    
    # Тестируем enhancement
    if not args.generation_only:
        print("\n" + "="*80)
        print("📝 ТЕСТИРОВАНИЕ ENHANCEMENT")
        print("="*80)
        for model in enhancement_models:
            result = tester.test_enhancement(model, TEST_ENHANCEMENT_TEXT)
            tester.results.append(result)
            if result["success"]:
                print(f"✅ Успешно! Время: {result['time_seconds']} сек, Confidence: {result.get('confidence', 0)}")
            else:
                print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
    
    # Тестируем generation
    if not args.enhancement_only:
        print("\n" + "="*80)
        print("🗺️  ТЕСТИРОВАНИЕ GENERATION")
        print("="*80)
        for model in generation_models:
            result = tester.test_generation(model, TEST_GENERATION_TEXT)
            tester.results.append(result)
            if result["success"]:
                print(f"✅ Успешно! Время: {result['time_seconds']} сек, Activities: {result.get('map_items', 0)}")
            else:
                print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
    
    # Выводим результаты
    tester.print_results()
    
    print("\n" + "="*80)
    print("✅ Тестирование завершено!")
    print("="*80)


if __name__ == "__main__":
    main()

