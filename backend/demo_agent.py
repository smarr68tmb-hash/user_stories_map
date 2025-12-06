"""
Демонстрация разницы между обычной генерацией и AI-агентом

Показывает:
1. Как работает обычная генерация
2. Как работает агент с валидацией
3. Сравнение метрик

Использование:
    python demo_agent.py
"""
import json
from services.agent_service import SimpleAgent
from services.ai_service import generate_ai_map


def demo_comparison():
    """Сравнивает обычную генерацию и агента"""

    print("="*80)
    print("🎯 ДЕМОНСТРАЦИЯ: Обычная генерация vs AI-агент")
    print("="*80)

    requirements = """
    Интернет-магазин электроники.
    Пользователи могут искать товары, добавлять в корзину, оформлять заказы.
    Есть личный кабинет с историей заказов.
    Админ-панель для управления каталогом.
    """

    print(f"\n📝 Требования:")
    print(requirements)

    # =====================================================
    # 1. Обычная генерация (БЕЗ агента)
    # =====================================================
    print("\n" + "="*80)
    print("1️⃣  ОБЫЧНАЯ ГЕНЕРАЦИЯ (без агента)")
    print("="*80)

    try:
        print("\n⏳ Генерация...")
        result_standard = generate_ai_map(requirements, redis_client=None, use_cache=False)

        print("✅ Успешно!")
        print(f"\n📊 Результат:")
        print(f"  - Продукт: {result_standard.get('productName', 'N/A')}")
        print(f"  - Персоны: {len(result_standard.get('personas', []))}")
        print(f"  - Activities: {len(result_standard.get('map', []))}")

        # Подсчет stories
        total_stories = sum(
            len(story for task in activity.get('tasks', []) for story in task.get('stories', []))
            for activity in result_standard.get('map', [])
        )
        print(f"  - Всего stories: {total_stories}")

        # Проверка acceptance criteria
        stories_with_criteria = 0
        for activity in result_standard.get('map', []):
            for task in activity.get('tasks', []):
                for story in task.get('stories', []):
                    if story.get('acceptanceCriteria') and len(story.get('acceptanceCriteria', [])) >= 2:
                        stories_with_criteria += 1

        print(f"  - Stories с >= 2 acceptance criteria: {stories_with_criteria}/{total_stories}")
        print(f"\n⚠️  Валидация: НЕ ПРОВОДИЛАСЬ")
        print(f"⚠️  Исправление ошибок: НЕТ")
        print(f"⚠️  Метрики: НЕТ")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return

    # =====================================================
    # 2. Генерация с агентом
    # =====================================================
    print("\n" + "="*80)
    print("2️⃣  ГЕНЕРАЦИЯ С AI-АГЕНТОМ")
    print("="*80)

    try:
        print("\n⏳ Генерация через агента...")
        agent = SimpleAgent(enable_validation=True, enable_fix=True)
        result_agent = agent.generate_map(requirements, use_cache=False)

        print("✅ Успешно!")
        print(f"\n📊 Результат:")
        print(f"  - Продукт: {result_agent.get('productName', 'N/A')}")
        print(f"  - Персоны: {len(result_agent.get('personas', []))}")
        print(f"  - Activities: {len(result_agent.get('map', []))}")

        # Подсчет stories
        total_stories_agent = sum(
            len(story for task in activity.get('tasks', []) for story in task.get('stories', []))
            for activity in result_agent.get('map', [])
        )
        print(f"  - Всего stories: {total_stories_agent}")

        # Метаданные агента
        metadata = result_agent.get('metadata', {})
        validation = metadata.get('validation', {})
        metrics = metadata.get('metrics', {})

        print(f"\n✅ Валидация:")
        print(f"  - Статус: {'✅ ВАЛИДНА' if validation.get('is_valid') else '❌ ОШИБКИ'}")
        print(f"  - Score: {validation.get('score', 0):.2f} (0.0-1.0)")
        print(f"  - Проблем найдено: {len(validation.get('issues', []))}")

        if validation.get('issues'):
            print(f"\n  Проблемы:")
            for issue in validation.get('issues', [])[:5]:  # Первые 5
                severity = issue.get('severity', 'unknown')
                message = issue.get('message', 'No message')
                emoji = "🔴" if severity == "critical" else "🟡"
                print(f"    {emoji} [{severity.upper()}] {message}")

        print(f"\n⏱️  Метрики:")
        print(f"  - Общее время: {metrics.get('total_time', 0):.2f}s")
        print(f"  - Время генерации: {metrics.get('generation_time', 0):.2f}s")
        print(f"  - Время валидации: {metrics.get('validation_time', 0):.2f}s")
        print(f"  - Провайдер: {metrics.get('provider_used', 'unknown')}")

        if metrics.get('fix_attempted'):
            print(f"\n🔧 Исправление:")
            print(f"  - Попытка исправления: ✅ ДА")
            print(f"  - Критических проблем ДО: {metrics.get('critical_issues_before_fix', 0)}")
            print(f"  - Критических проблем ПОСЛЕ: {metrics.get('critical_issues_after_fix', 0)}")
            print(f"  - Успешно: {'✅ ДА' if metrics.get('fix_successful') else '❌ НЕТ'}")
        else:
            print(f"\n🔧 Исправление: Не потребовалось (нет критических ошибок)")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return

    # =====================================================
    # 3. Сравнение
    # =====================================================
    print("\n" + "="*80)
    print("📊 СРАВНЕНИЕ")
    print("="*80)

    print(f"""
┌─────────────────────────────┬──────────────────┬──────────────────┐
│ Метрика                     │ Обычная          │ С агентом        │
├─────────────────────────────┼──────────────────┼──────────────────┤
│ Activities                  │ {len(result_standard.get('map', [])):16} │ {len(result_agent.get('map', [])):16} │
│ Stories                     │ {total_stories:16} │ {total_stories_agent:16} │
│ Валидация                   │ ❌ Нет          │ ✅ Да           │
│ Validation score            │ ??? (неизвестно) │ {validation.get('score', 0):.2f} (0.0-1.0)  │
│ Исправление ошибок          │ ❌ Нет          │ {'✅ Да' if metrics.get('fix_attempted') else '❌ Нет':16} │
│ Метрики генерации           │ ❌ Нет          │ ✅ Да           │
│ Провайдер использован       │ ??? (неизвестно) │ {metrics.get('provider_used', 'unknown'):16} │
└─────────────────────────────┴──────────────────┴──────────────────┘
""")

    print("\n💡 Выводы:")
    print("  1. Агент добавляет валидацию и исправление ошибок")
    print("  2. Агент предоставляет метрики для отслеживания качества")
    print("  3. Агент может автоматически исправлять критические проблемы")
    print("  4. Время генерации может быть чуть дольше (+20-30%)")

    print("\n🎯 Рекомендация:")
    print("  Используйте агента если:")
    print("  - Нужна высокая надежность генерации (validation score > 0.9)")
    print("  - Важна прозрачность (метрики, логи)")
    print("  - Хотите автоматическое исправление ошибок")

    print("\n" + "="*80)
    print("✅ Демонстрация завершена!")
    print("="*80)


if __name__ == "__main__":
    try:
        demo_comparison()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
