# Рефакторинг: Использование классов для упрощения разработки

## Обзор

Аналогично тому, как тесты организованы в классы (например, `TestHelperFunctions`, `TestValidationLogic`), мы вынесли повторяющуюся логику в классы-хелперы. Это упрощает разработку и делает код более организованным.

## Созданные классы

### 1. `ResourceAccessValidator` (`utils/resource_validator.py`)

**Назначение:** Централизованная проверка доступа к ресурсам пользователя.

**Проблема:** В каждом endpoint повторялся код проверки доступа:
```python
# Старый подход
project = db.query(Project).filter(Project.id == project_id).filter(Project.user_id == user_id).first()
if not project:
    raise HTTPException(status_code=404, detail="Project not found")
```

**Решение:** Использование класса:
```python
# Новый подход
validator = ResourceAccessValidator(db, current_user.id)
project = validator.get_project(project_id)  # Автоматически выбрасывает 404 если нет доступа
```

**Методы:**
- `get_project(project_id)` - получение проекта
- `get_epic(epic_id)` - получение эпика
- `get_story(story_id)` - получение истории
- `get_activity(activity_id)` - получение активности
- `get_task(task_id)` - получение задачи
- `verify_same_project(story, epic)` - проверка принадлежности к одному проекту

**Преимущества:**
- ✅ Единая точка проверки доступа
- ✅ Меньше дублирования кода
- ✅ Легче тестировать
- ✅ Проще поддерживать

---

### 2. `ResponseFormatter` (`utils/response_formatter.py`)

**Назначение:** Централизованное форматирование ответов API.

**Проблема:** В каждом endpoint повторялся код создания ответов:
```python
# Старый подход
stories_data = [
    StoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        priority=story.priority,
        acceptance_criteria=story.acceptance_criteria or [],
        release_id=story.release_id,
        position=story.position,
        status=story.status or "todo"
    )
    for story in epic.stories
]
```

**Решение:** Использование класса:
```python
# Новый подход
formatter = ResponseFormatter()
stories_data = formatter.format_stories(epic.stories)
```

**Методы:**
- `format_story(story)` - форматирование одной истории
- `format_stories(stories)` - форматирование списка историй
- `format_task(task, include_stories=True)` - форматирование задачи
- `format_tasks(tasks, include_stories=True)` - форматирование списка задач
- `format_activity(activity, include_tasks=True)` - форматирование активности
- `format_activities(activities, include_tasks=True)` - форматирование списка активностей
- `format_release(release)` - форматирование релиза
- `format_releases(releases)` - форматирование списка релизов
- `format_project(project)` - форматирование проекта с полной структурой

**Преимущества:**
- ✅ Единая точка форматирования
- ✅ Меньше дублирования кода
- ✅ Легче изменить формат ответа (в одном месте)
- ✅ Консистентность ответов

---

### 3. `PositionManager` (`utils/position_manager.py`)

**Назначение:** Управление позициями элементов в списках.

**Проблема:** В каждом endpoint повторялась логика сдвига позиций:
```python
# Старый подход
if new_position < old_position:
    tasks_to_shift = db.query(UserTask)\
        .filter(UserTask.activity_id == task.activity_id)\
        .filter(UserTask.position >= new_position)\
        .filter(UserTask.position < old_position)\
        .filter(UserTask.id != task_id)\
        .all()
    for t in tasks_to_shift:
        t.position += 1
```

**Решение:** Использование класса:
```python
# Новый подход
position_manager = PositionManager(
    db=db,
    model_class=UserTask,
    position_column=UserTask.position,
    parent_column=UserTask.activity_id
)
position_manager.move_item(task_id, activity_id, old_position, new_position)
```

**Методы:**
- `get_max_position(parent_id)` - получение максимальной позиции
- `shift_positions_right(parent_id, from_position, exclude_id=None)` - сдвиг вправо
- `shift_positions_left(parent_id, from_position, exclude_id=None)` - сдвиг влево
- `normalize_position(parent_id, position)` - нормализация позиции
- `move_item(item_id, parent_id, old_position, new_position)` - перемещение элемента

**Преимущества:**
- ✅ Единая логика управления позициями
- ✅ Меньше ошибок при сдвиге позиций
- ✅ Легче тестировать
- ✅ Поддержка разных моделей (Activity, UserTask, UserStory)

---

### 4. `RedisManager` (`utils/redis_manager.py`)

**Назначение:** Централизованная работа с Redis.

**Проблема:** В каждом файле повторялся код получения Redis клиента:
```python
# Старый подход
def get_redis_client():
    try:
        import redis
        if settings.REDIS_URL:
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()
            return redis_client
    except Exception:
        pass
    return None
```

**Решение:** Использование класса:
```python
# Новый подход
redis_client = RedisManager.get_client()
```

**Методы:**
- `get_client()` - получение Redis клиента (с кешированием)
- `is_available()` - проверка доступности Redis
- `reset_client()` - сброс кеша клиента (для тестирования)

**Преимущества:**
- ✅ Единая точка работы с Redis
- ✅ Кеширование соединения
- ✅ Правильная обработка ошибок
- ✅ Логирование в production

---

## Пример использования

### До рефакторинга (`api/epics.py`):

```python
def get_project_epics(project_id: int, current_user: User, db: Session):
    # Проверка доступа
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .filter(Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Получение эпиков
    epics = db.query(Epic).filter(Epic.project_id == project_id).all()
    
    # Форматирование ответа
    result = []
    for epic in epics:
        stories_data = [
            StoryResponse(
                id=story.id,
                title=story.title,
                # ... много полей
            )
            for story in epic.stories
        ]
        result.append(EpicWithStoriesResponse(...))
    
    return result
```

### После рефакторинга:

```python
def get_project_epics(project_id: int, current_user: User, db: Session):
    # Проверка доступа
    validator = ResourceAccessValidator(db, current_user.id)
    project = validator.get_project(project_id)
    
    # Получение эпиков
    epics = db.query(Epic).filter(Epic.project_id == project_id).all()
    
    # Форматирование ответа
    formatter = ResponseFormatter()
    result = []
    for epic in epics:
        stories_data = formatter.format_stories(epic.stories)
        result.append(EpicWithStoriesResponse(..., stories=stories_data))
    
    return result
```

**Результат:**
- ✅ Код стал короче и читабельнее
- ✅ Меньше дублирования
- ✅ Легче тестировать
- ✅ Проще поддерживать

---

## Миграция существующего кода

### Шаг 1: Импорт классов

```python
from utils import ResourceAccessValidator, ResponseFormatter, PositionManager, RedisManager
```

### Шаг 2: Замена проверок доступа

**Было:**
```python
project = get_project_for_user(project_id, current_user.id, db)
```

**Стало:**
```python
validator = ResourceAccessValidator(db, current_user.id)
project = validator.get_project(project_id)
```

### Шаг 3: Замена форматирования

**Было:**
```python
stories_data = [StoryResponse(...) for story in stories]
```

**Стало:**
```python
formatter = ResponseFormatter()
stories_data = formatter.format_stories(stories)
```

### Шаг 4: Замена работы с Redis

**Было:**
```python
redis_client = get_redis_client()
```

**Стало:**
```python
redis_client = RedisManager.get_client()
```

---

## Файлы для рефакторинга

Следующие файлы можно рефакторить аналогично `api/epics.py`:

1. ✅ `api/epics.py` - уже рефакторен
2. ⏳ `api/projects.py` - можно использовать все классы
3. ⏳ `api/stories.py` - можно использовать `ResourceAccessValidator` и `ResponseFormatter`
4. ⏳ `api/analysis.py` - можно использовать `RedisManager`

---

## Преимущества подхода

1. **Организация кода** - связанные функции сгруппированы в классы
2. **Меньше дублирования** - логика вынесена в переиспользуемые классы
3. **Легче тестировать** - можно мокировать классы целиком
4. **Проще поддерживать** - изменения в одном месте
5. **Консистентность** - единый подход к решению задач

---

## Аналогия с тестами

Так же, как в тестах мы используем:
- `TestHelperFunctions` - для вспомогательных функций
- `TestValidationLogic` - для валидации
- `TestFallbackGrouping` - для fallback логики

В основном коде мы используем:
- `ResourceAccessValidator` - для проверки доступа
- `ResponseFormatter` - для форматирования
- `PositionManager` - для управления позициями
- `RedisManager` - для работы с Redis

Это делает код более организованным и упрощает разработку! 🎉

