# AI Agent MVP - Упрощенный план

## Фаза 0: MVP (3-4 дня вместо 17)

### День 1-2: Простой агент с 3 шагами

```python
class SimpleStoryMapAgent:
    """Минимальная версия агента"""

    def generate_map(self, requirements: str) -> Dict:
        # Step 1: Один запрос для структуры
        structure = self._generate_full_structure(requirements)

        # Step 2: Валидация
        validation = self._validate(structure)

        # Step 3: Одна попытка исправления (если нужно)
        if not validation["is_valid"]:
            structure = self._fix_once(structure, validation["issues"])

        return structure
```

### День 3: Интеграция

- Добавить флаг `use_agent=True` в существующий endpoint
- A/B тестирование: старый подход vs агент

### День 4: Метрики

- Сравнить качество (validation score)
- Замерить время генерации
- Решить: развивать дальше или остановиться

## Почему MVP лучше

1. **Быстрая проверка гипотезы**: 4 дня vs 17 дней
2. **Минимальный риск**: не переписываете существующий код
3. **Реальные метрики**: сразу видите реальное улучшение
4. **Легко откатиться**: если не работает, просто отключаете флаг

## Когда развивать дальше

Только если MVP покажет:
- **Качество**: validation score > 85% (против текущих ~70-80%)
- **Время**: генерация < 60 секунд
- **Стабильность**: успешные генерации > 90%

## Что НЕ делать в MVP

- ❌ WebSocket для прогресса (можно добавить потом)
- ❌ Сложное кеширование (используйте существующее)
- ❌ Множественные итерации исправлений (одной достаточно)
- ❌ AI-валидация качества (используйте validation_service)
- ❌ Отдельный endpoint (флаг в существующем)

## Переход к полной версии

Если MVP успешен, развивайте постепенно:

1. **Неделя 2**: Добавить пошаговую генерацию (Activities → Tasks → Stories)
2. **Неделя 3**: Улучшить валидацию (AI + structural)
3. **Неделя 4**: Добавить прогресс-бар и итеративные исправления

## Код MVP

```python
# backend/services/agent_service.py (минимальная версия)

from typing import Dict, List
import logging
from services.gemini_service import call_gemini
from services.validation_service import validate_project_structure

logger = logging.getLogger(__name__)

class SimpleAgent:
    """Простой агент: generate → validate → fix"""

    def __init__(self, model: str = "gemini-2.5-pro"):
        self.model = model

    def generate_map(self, requirements: str) -> Dict:
        """
        Простой flow:
        1. Генерация (один запрос)
        2. Валидация
        3. Одно исправление если нужно
        """

        # Генерация
        structure = self._generate(requirements)

        # Валидация
        issues = self._validate(structure)

        # Исправление (только если критические ошибки)
        if self._has_critical_issues(issues):
            logger.info(f"Found {len(issues)} issues, attempting fix")
            structure = self._fix(structure, issues)
            issues = self._validate(structure)

        return {
            "personas": structure.get("personas", []),
            "map": structure.get("activities", []),
            "validation": {
                "is_valid": len(issues) == 0,
                "issues": issues
            }
        }

    def _generate(self, requirements: str) -> Dict:
        """Один запрос к Gemini"""
        prompt = f"""Создай User Story Map для:
{requirements}

Используй JSON формат:
{{
  "personas": ["роль1", "роль2"],
  "activities": [
    {{
      "title": "Activity",
      "tasks": [
        {{
          "title": "Task",
          "stories": [
            {{
              "title": "Story",
              "description": "As a X, I want Y, so that Z",
              "priority": "MVP",
              "acceptance_criteria": ["критерий 1", "критерий 2"]
            }}
          ]
        }}
      ]
    }}
  ]
}}

Требования:
- Минимум 3-4 activities
- 2-3 tasks на activity
- 2-4 stories на task
- Все stories с acceptance_criteria"""

        response = call_gemini(prompt, model=self.model)
        return self._parse_json(response)

    def _validate(self, structure: Dict) -> List[Dict]:
        """Простая валидация структуры"""
        issues = []

        # Проверка наличия обязательных полей
        if not structure.get("personas"):
            issues.append({"type": "missing_personas", "severity": "critical"})

        if not structure.get("activities"):
            issues.append({"type": "missing_activities", "severity": "critical"})
            return issues

        # Проверка каждой activity
        for activity in structure["activities"]:
            if not activity.get("tasks"):
                issues.append({
                    "type": "missing_tasks",
                    "severity": "critical",
                    "activity": activity.get("title")
                })

            # Проверка каждой task
            for task in activity.get("tasks", []):
                if not task.get("stories"):
                    issues.append({
                        "type": "missing_stories",
                        "severity": "critical",
                        "task": task.get("title")
                    })

                # Проверка stories
                for story in task.get("stories", []):
                    if not story.get("acceptance_criteria"):
                        issues.append({
                            "type": "missing_criteria",
                            "severity": "warning",
                            "story": story.get("title")
                        })

        return issues

    def _has_critical_issues(self, issues: List[Dict]) -> bool:
        """Есть ли критические ошибки"""
        return any(i.get("severity") == "critical" for i in issues)

    def _fix(self, structure: Dict, issues: List[Dict]) -> Dict:
        """Одна попытка исправить критические ошибки"""

        critical = [i for i in issues if i.get("severity") == "critical"]

        prompt = f"""Исправь следующие ошибки в User Story Map:

Текущая структура:
{structure}

Ошибки:
{critical}

Верни исправленную структуру в том же JSON формате."""

        response = call_gemini(prompt, model=self.model)
        return self._parse_json(response)

    def _parse_json(self, response: str) -> Dict:
        """Парсит JSON из ответа"""
        import json
        import re

        # Ищем JSON в markdown блоке или просто в тексте
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)

        return json.loads(response)


# Интеграция в существующий endpoint
# backend/api/projects.py

@router.post("/generate-map")
def generate_map(
    req: RequirementsInput,
    use_agent: bool = False,  # Новый параметр
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Генерирует User Story Map"""

    if use_agent:
        # Новый агентный подход
        from services.agent_service import SimpleAgent

        agent = SimpleAgent()
        result = agent.generate_map(req.text)

        # Сохранение в БД (существующая логика)
        project = create_project_from_result(result, db, current_user)

        return {
            "status": "success",
            "project_id": project.id,
            "validation": result["validation"]
        }
    else:
        # Существующий подход
        # ... текущая логика
```

## Тестирование MVP

```python
# tests/test_simple_agent.py

def test_simple_agent_basic():
    """Базовый тест агента"""
    agent = SimpleAgent()

    requirements = "Мобильное приложение для доставки еды"
    result = agent.generate_map(requirements)

    assert result["personas"]
    assert result["map"]
    assert len(result["map"]) >= 3  # минимум 3 activities

def test_agent_vs_current():
    """Сравнение агента с текущим подходом"""
    requirements = "Интернет-магазин электроники"

    # Текущий подход
    current_result = generate_map_current(requirements)
    current_score = validate(current_result)

    # Агент
    agent = SimpleAgent()
    agent_result = agent.generate_map(requirements)
    agent_score = validate(agent_result)

    print(f"Current: {current_score}, Agent: {agent_score}")
    assert agent_score >= current_score  # должен быть лучше или равен
```

## Метрики для решения

После недели использования MVP соберите:

```python
# Структура для сравнения
comparison = {
    "current_approach": {
        "avg_validation_score": 0.75,
        "avg_generation_time": 30,
        "success_rate": 0.82,
        "user_satisfaction": "средняя"
    },
    "agent_approach": {
        "avg_validation_score": 0.88,  # должно быть выше
        "avg_generation_time": 45,     # допустимо немного дольше
        "success_rate": 0.91,           # должно быть выше
        "user_satisfaction": "высокая"
    },
    "decision": "continue" if agent_better else "stop"
}
```

## Итого

**MVP агента = 3-4 дня работы**
- День 1-2: Код агента (300 строк)
- День 3: Интеграция (флаг в endpoint)
- День 4: Тестирование и метрики

**Критерий успеха**: Если validation score улучшился на 10%+ → развивать дальше

**Критерий провала**: Если разницы нет или хуже → вернуться к оптимизации промптов

Это намного безопаснее чем 17 дней разработки без проверки гипотезы.
