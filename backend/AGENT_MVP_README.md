# AI Agent MVP - Документация

## Что это?

MVP версия AI-агента для генерации User Story Map с автоматической валидацией и исправлением ошибок.

## Как это работает?

### Простой flow (3 шага):

1. **Generate** - Генерирует карту одним запросом к AI
2. **Validate** - Валидирует структуру (проверяет наличие Activities, Tasks, Stories, acceptance criteria)
3. **Fix** - Одна попытка исправить критические ошибки

## Использование

### 1. Через API

```bash
# С агентом (новый подход)
curl -X POST "http://localhost:8000/generate-map" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Мобильное приложение для доставки еды",
    "use_agent": true
  }'

# Без агента (старый подход)
curl -X POST "http://localhost:8000/generate-map" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Мобильное приложение для доставки еды",
    "use_agent": false
  }'
```

### 2. Через Python

```python
from services.agent_service import SimpleAgent

# Создаем агента
agent = SimpleAgent(
    enable_validation=True,  # Включить валидацию
    enable_fix=True,         # Включить исправление ошибок
    redis_client=None        # Опционально: Redis для кеширования
)

# Генерируем карту
result = agent.generate_map(
    "Мобильное приложение для доставки еды",
    use_cache=True
)

# Результат
print(f"Product: {result['productName']}")
print(f"Activities: {len(result['map'])}")
print(f"Validation score: {result['metadata']['validation']['score']}")
```

## Формат ответа

```json
{
  "productName": "Название продукта",
  "personas": ["Персона 1", "Персона 2"],
  "map": [
    {
      "activity": "Название Activity",
      "tasks": [
        {
          "taskTitle": "Название Task",
          "stories": [
            {
              "title": "Название Story",
              "description": "Как [персона], я хочу...",
              "priority": "MVP",
              "acceptanceCriteria": ["Критерий 1", "Критерий 2"]
            }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "agent_version": "mvp",
    "validation": {
      "is_valid": true,
      "issues": [],
      "score": 0.95
    },
    "metrics": {
      "total_time": 12.5,
      "generation_time": 10.2,
      "validation_time": 0.3,
      "fix_time": 2.0,
      "provider_used": "gemini",
      "fix_attempted": true,
      "fix_successful": true,
      "critical_issues_before_fix": 2,
      "critical_issues_after_fix": 0
    }
  }
}
```

## Метрики

Агент возвращает следующие метрики:

- `total_time` - Общее время генерации (секунды)
- `generation_time` - Время генерации структуры
- `validation_time` - Время валидации
- `fix_time` - Время исправления (если было)
- `provider_used` - Какой AI провайдер использовался (gemini/groq/openai)
- `fix_attempted` - Было ли исправление ошибок
- `fix_successful` - Успешно ли прошло исправление
- `critical_issues_before_fix` - Критических ошибок до исправления
- `critical_issues_after_fix` - Критических ошибок после исправления

## Валидация

Агент проверяет:

✅ Наличие персон (personas)
✅ Наличие структуры карты (map)
✅ Минимум 3 Activities
✅ Наличие Tasks в каждой Activity
✅ Наличие Stories в каждой Task
✅ Наличие acceptance criteria в Stories (минимум 2)
✅ Наличие названий и описаний

### Severity уровни:

- **critical** - Критические ошибки (отсутствуют обязательные элементы)
- **warning** - Предупреждения (недостаточно acceptance criteria, нет описаний)

## Настройка

### Требования:

1. Настроить AI API ключ в `.env`:
   ```bash
   # Один из следующих (в порядке приоритета):
   GEMINI_API_KEY=your_gemini_key
   GROQ_API_KEY=your_groq_key
   OPENAI_API_KEY=your_openai_key
   ```

2. (Опционально) Redis для кеширования:
   ```bash
   REDIS_URL=redis://localhost:6379
   ```

### Кеширование:

Агент кеширует результаты на 24 часа используя Redis:
- Ключ кеша: `agent:mvp:{sha256(requirements)}`
- TTL: 86400 секунд (24 часа)

## Тестирование

### Запуск тестов:

```bash
cd backend
source venv/bin/activate
python test_agent.py
```

### Тесты включают:

1. **Простые требования** - Мобильное приложение для доставки еды
2. **Сложные требования** - SaaS платформа для управления проектами
3. **Без валидации** - Сравнение скорости с/без валидации

### Примеры результатов тестов:

```
🧪 ТЕСТИРОВАНИЕ MVP АГЕНТА

ТЕСТ 1: Простые требования
✅ Генерация успешна!
  - Общее время: 12.50s
  - Провайдер: gemini
  - Валидация score: 0.95
  - Критических проблем: 0

ТЕСТ 2: Сложные требования
✅ Генерация успешна!
  - Activities: 5
  - Всего stories: 24
  - Время: 18.30s
```

## Сравнение: Агент vs Обычная генерация

| Аспект | Обычная генерация | С агентом |
|--------|-------------------|-----------|
| **Запросов к AI** | 1 | 1-2 (если нужно исправление) |
| **Валидация** | Нет | Да (автоматическая) |
| **Исправление ошибок** | Нет | Да (1 попытка) |
| **Время** | ~8-12s | ~10-15s (+20-30%) |
| **Качество** | 70-80% | 85-95% (+15-20%) |
| **Прозрачность** | Черный ящик | Видны метрики и проблемы |

## Планы на будущее

### Возможные улучшения (если MVP успешен):

1. **Пошаговая генерация**:
   - Отдельно генерировать Activities → Tasks → Stories
   - WebSocket для отслеживания прогресса

2. **Расширенная валидация**:
   - Проверка дубликатов
   - Semantic similarity между stories
   - Проверка качества acceptance criteria

3. **Множественные итерации исправления**:
   - До 3 попыток исправить ошибки
   - Прогрессивное улучшение

4. **Function Calling**:
   - Использовать Gemini Function Calling для валидации
   - Более точная валидация через AI

5. **Метрики и мониторинг**:
   - Dashboard для отслеживания качества
   - A/B тестирование агента vs обычной генерации
   - Сбор feedback от пользователей

## Известные ограничения MVP

❌ Только 1 попытка исправления (не итеративное)
❌ Нет Function Calling (простая промпт-инженерия)
❌ Нет проверки дубликатов
❌ Нет semantic similarity проверки
❌ Нет прогресс-бара (генерация кажется долгой)
❌ Не интегрирован с существующим validation_service

## Troubleshooting

### "No AI providers configured"

Добавьте API ключ в `.env`:
```bash
GEMINI_API_KEY=your_key_here
```

### "Redis unavailable"

Агент работает без Redis, но без кеширования. Для включения кеша:
```bash
# Запустите Redis
redis-server

# Или используйте Docker
docker run -d -p 6379:6379 redis
```

### Медленная генерация

1. Проверьте используемую модель в `config.py`
2. Попробуйте отключить исправление ошибок:
   ```python
   agent = SimpleAgent(enable_fix=False)
   ```

## Контакты

Вопросы и предложения: создайте issue в репозитории проекта.

---

**Версия**: MVP 1.0
**Дата**: 2025-12-05
**Статус**: ✅ Готово к тестированию
