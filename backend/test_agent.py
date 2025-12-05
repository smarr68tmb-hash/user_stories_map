"""
Тест MVP агента для генерации User Story Map

Использование:
    python test_agent.py
"""
import sys
import json
import logging
from services.agent_service import SimpleAgent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def _make_serializable(obj):
    """Конвертирует ValidationIssue и другие объекты в dict для JSON"""
    if hasattr(obj, 'dict'):
        return obj.dict()
    elif hasattr(obj, '__dict__'):
        return {k: _make_serializable(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)


def test_simple_requirements():
    """Тест на простых требованиях"""
    print("\n" + "="*80)
    print("ТЕСТ 1: Простые требования - Мобильное приложение для доставки еды")
    print("="*80 + "\n")

    requirements = """
    Мобильное приложение для доставки еды.
    Пользователи могут заказывать еду из ресторанов, отслеживать заказы, оплачивать онлайн.
    Курьеры принимают заказы и доставляют их.
    Рестораны управляют меню и заказами.
    """

    agent = SimpleAgent(enable_validation=True, enable_fix=True)

    try:
        result = agent.generate_map(requirements, use_cache=False)

        print("\n✅ Генерация успешна!")
        print(f"\nПродукт: {result.get('productName')}")
        print(f"Персоны: {', '.join(result.get('personas', []))}")
        print(f"Activities: {len(result.get('map', []))}")

        # Метаданные
        metadata = result.get("metadata", {})
        metrics = metadata.get("metrics", {})

        print(f"\n⏱️  Метрики:")
        print(f"  - Общее время: {metrics.get('total_time', 0):.2f}s")
        print(f"  - Время генерации: {metrics.get('generation_time', 0):.2f}s")
        print(f"  - Время валидации: {metrics.get('validation_time', 0):.2f}s")
        print(f"  - Провайдер: {metrics.get('provider_used', 'unknown')}")

        # Валидация
        validation = metadata.get("validation", {})
        print(f"\n✅ Валидация:")
        print(f"  - Валидна: {validation.get('is_valid', False)}")
        print(f"  - Score: {validation.get('score', 0):.2f}")
        print(f"  - Проблем: {len(validation.get('issues', []))}")

        if metrics.get("fix_attempted"):
            print(f"\n🔧 Исправление:")
            print(f"  - Критических проблем до: {metrics.get('critical_issues_before_fix', 0)}")
            print(f"  - Критических проблем после: {metrics.get('critical_issues_after_fix', 0)}")
            print(f"  - Успешно: {metrics.get('fix_successful', False)}")

        # Показываем структуру
        print(f"\n📋 Структура карты:")
        for idx, activity in enumerate(result.get('map', []), 1):
            print(f"\n  {idx}. Activity: {activity.get('activity')}")
            for t_idx, task in enumerate(activity.get('tasks', []), 1):
                print(f"     {idx}.{t_idx} Task: {task.get('taskTitle')}")
                stories_count = len(task.get('stories', []))
                print(f"         → {stories_count} stories")

        # Сохраняем результат (конвертируем ValidationIssue в dict)
        result_serializable = _make_serializable(result)
        with open('/tmp/agent_test_result_1.json', 'w', encoding='utf-8') as f:
            json.dump(result_serializable, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Результат сохранен в /tmp/agent_test_result_1.json")

        return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.error("Test failed", exc_info=True)
        return False


def test_complex_requirements():
    """Тест на сложных требованиях"""
    print("\n" + "="*80)
    print("ТЕСТ 2: Сложные требования - SaaS платформа для управления проектами")
    print("="*80 + "\n")

    requirements = """
    SaaS платформа для управления проектами в стиле Agile.

    Основные возможности:
    - Управление командами и участниками
    - Создание проектов и задач
    - Kanban и Scrum доски
    - Спринты и бэклог
    - Отчеты и аналитика
    - Интеграции с Git, Slack, Jira
    - Уведомления в реальном времени
    - Файловое хранилище

    Роли: Администратор, Project Manager, Developer, Viewer
    """

    agent = SimpleAgent(enable_validation=True, enable_fix=True)

    try:
        result = agent.generate_map(requirements, use_cache=False)

        print("\n✅ Генерация успешна!")

        # Метрики
        metadata = result.get("metadata", {})
        metrics = metadata.get("metrics", {})
        validation = metadata.get("validation", {})

        print(f"\n📊 Результаты:")
        print(f"  - Activities: {len(result.get('map', []))}")
        print(f"  - Персоны: {len(result.get('personas', []))}")
        print(f"  - Время: {metrics.get('total_time', 0):.2f}s")
        print(f"  - Валидация score: {validation.get('score', 0):.2f}")
        print(f"  - Провайдер: {metrics.get('provider_used', 'unknown')}")

        # Подсчет общего количества stories
        total_stories = sum(
            len([story for task in activity.get('tasks', []) for story in task.get('stories', [])])
            for activity in result.get('map', [])
        )
        print(f"  - Всего stories: {total_stories}")

        # Сохраняем результат (конвертируем ValidationIssue в dict)
        result_serializable = _make_serializable(result)
        with open('/tmp/agent_test_result_2.json', 'w', encoding='utf-8') as f:
            json.dump(result_serializable, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Результат сохранен в /tmp/agent_test_result_2.json")

        return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.error("Test failed", exc_info=True)
        return False


def test_with_validation_off():
    """Тест с отключенной валидацией для сравнения"""
    print("\n" + "="*80)
    print("ТЕСТ 3: Генерация БЕЗ валидации и исправления")
    print("="*80 + "\n")

    requirements = "Интернет-магазин электроники с корзиной, оплатой и доставкой"

    agent = SimpleAgent(enable_validation=False, enable_fix=False)

    try:
        result = agent.generate_map(requirements, use_cache=False)

        metadata = result.get("metadata", {})
        metrics = metadata.get("metrics", {})

        print("\n✅ Генерация успешна!")
        print(f"  - Время генерации: {metrics.get('generation_time', 0):.2f}s")
        print(f"  - Время валидации: {metrics.get('validation_time', 0):.2f}s (отключена)")
        print(f"  - Общее время: {metrics.get('total_time', 0):.2f}s")

        return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.error("Test failed", exc_info=True)
        return False


def main():
    """Запускает все тесты"""
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ MVP АГЕНТА")
    print("="*80)

    results = {
        "test_1_simple": test_simple_requirements(),
        "test_2_complex": test_complex_requirements(),
        "test_3_no_validation": test_with_validation_off()
    }

    # Итоги
    print("\n" + "="*80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")

    print(f"\nИтого: {passed}/{total} тестов пройдено")

    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("\n⚠️  Некоторые тесты провалились")
        return 1


if __name__ == "__main__":
    sys.exit(main())
