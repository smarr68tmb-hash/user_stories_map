# 🔄 Руководство по миграции на v2.0.0

## Для разработчиков, работавших с v1.x

Если вы работали со старой версией проекта (монолитный `main.py`), это руководство поможет вам быстро адаптироваться к новой модульной структуре.

---

## 📊 Что изменилось

### Основное изменение
**Монолитный main.py (1116 строк) → Модульная структура (20 файлов)**

### Структура ДО (v1.x)
```
backend/
└── main.py    # ВСЁ В ОДНОМ ФАЙЛЕ
    ├── Config
    ├── Models (User, Project, UserStory, etc.)
    ├── Schemas (Pydantic)
    ├── Business Logic
    └── API Endpoints
```

### Структура ПОСЛЕ (v2.0)
```
backend/
├── main.py              # Только FastAPI app setup
├── config.py            # Конфигурация
├── dependencies.py      # FastAPI dependencies
├── models/              # SQLAlchemy модели
├── schemas/             # Pydantic схемы
├── services/            # Бизнес-логика
├── api/                 # API endpoints
└── utils/               # Утилиты
```

---

## 🔧 Изменения в импортах

### ❌ Старые импорты (НЕ РАБОТАЮТ)

```python
# Было в v1.x
from main import app, get_db, SessionLocal
from main import User, Project, UserStory
from main import UserCreate, ProjectResponse
from main import create_access_token, authenticate_user
from main import generate_ai_map
```

### ✅ Новые импорты (v2.0)

```python
# Стало в v2.0
from main import app

# Database
from utils.database import get_db, SessionLocal

# Models
from models import User, Project, UserStory
from models.user import User, RefreshToken
from models.project import Project, Activity, UserTask, Release
from models.story import UserStory

# Schemas
from schemas import UserCreate, ProjectResponse
from schemas.user import UserCreate, UserResponse, Token
from schemas.project import ProjectResponse, RequirementsInput
from schemas.story import StoryCreate, StoryUpdate

# Services (бизнес-логика)
from services.auth_service import (
    create_access_token,
    authenticate_user,
    verify_password,
    get_password_hash
)
from services.ai_service import generate_ai_map

# Dependencies
from dependencies import get_current_user, get_current_active_user
```

---

## 📝 Обновление кода

### 1. Обновление тестов

#### Было (v1.x):
```python
from main import app, get_db
from main import User, Project

def test_something():
    # ...
```

#### Стало (v2.0):
```python
from main import app
from utils.database import get_db
from models import User, Project

def test_something():
    # ...
```

### 2. Работа с пользователями

#### Было (v1.x):
```python
from main import authenticate_user, create_access_token

user = authenticate_user(db, email, password)
token = create_access_token({"sub": str(user.id)})
```

#### Стало (v2.0):
```python
from services.auth_service import authenticate_user, create_access_token

user = authenticate_user(db, email, password)
token = create_access_token({"sub": str(user.id)})
```

### 3. Создание нового endpoint

#### Было (v1.x):
Добавить всё в `main.py`:
```python
# В main.py (внизу файла)
@app.post("/my-endpoint")
def my_endpoint():
    # Логика здесь же
    pass
```

#### Стало (v2.0):
1. Создать файл `api/my_feature.py`
2. Подключить в `main.py`

```python
# api/my_feature.py
from fastapi import APIRouter, Depends
from dependencies import get_current_active_user

router = APIRouter(prefix="", tags=["my-feature"])

@router.post("/my-endpoint")
def my_endpoint(current_user = Depends(get_current_active_user)):
    # Логика здесь
    pass
```

```python
# main.py
from api import my_feature
app.include_router(my_feature.router)
```

---

## 🎯 Частые сценарии

### Сценарий 1: "Где найти модель User?"

**Было:** `from main import User`  
**Стало:** `from models.user import User` или `from models import User`

### Сценарий 2: "Где функция authenticate_user?"

**Было:** `from main import authenticate_user`  
**Стало:** `from services.auth_service import authenticate_user`

### Сценарий 3: "Где get_db?"

**Было:** `from main import get_db`  
**Стало:** `from utils.database import get_db`

### Сценарий 4: "Где схемы Pydantic?"

**Было:** `from main import UserCreate, ProjectResponse`  
**Стало:** `from schemas import UserCreate, ProjectResponse`

### Сценарий 5: "Как добавить новый endpoint?"

**Было:** Дописать в конец `main.py`  
**Стало:** Создать файл в `api/` и подключить роутер

---

## 🔍 Где что находится - Шпаргалка

| Что ищу | Где было (v1.x) | Где теперь (v2.0) |
|---------|-----------------|-------------------|
| FastAPI app | `main.py` | `main.py` (без изменений) |
| Database models | `main.py` | `models/*.py` |
| Pydantic schemas | `main.py` | `schemas/*.py` |
| Бизнес-логика | `main.py` | `services/*.py` |
| API endpoints | `main.py` | `api/*.py` |
| JWT функции | `main.py` | `services/auth_service.py` |
| AI генерация | `main.py` | `services/ai_service.py` |
| get_db | `main.py` | `utils/database.py` |
| ENV конфигурация | `main.py` (сверху) | `config.py` |

---

## ✅ Что НЕ изменилось

- ✅ **API endpoints** - те же URL и поведение
- ✅ **Database schema** - те же таблицы
- ✅ **Аутентификация** - тот же JWT механизм
- ✅ **Frontend** - работает без изменений
- ✅ **Deployment** - те же команды
- ✅ **Docker** - тот же Dockerfile

**Обратная совместимость на 100%!** Функциональность не изменилась, только структура кода.

---

## 🧪 Проверка после миграции

### 1. Обновить импорты в ваших файлах

Найти и заменить:
- `from main import` → проверить таблицу выше
- Обновить согласно новой структуре

### 2. Запустить тесты

```bash
cd backend
source venv/bin/activate
pytest test_main.py -v
```

Должно быть: **9 passed**

### 3. Запустить приложение

```bash
python main.py
```

Должно запуститься без ошибок и показать:
```
✅ Application started successfully
📦 Database: postgresql://...
🤖 AI Provider: perplexity
🌍 Environment: development
```

### 4. Проверить API

```bash
curl http://localhost:8000/health
# {"status":"healthy","timestamp":"..."}

curl http://localhost:8000/docs
# Swagger UI должен открыться
```

---

## 🚨 Возможные проблемы

### Проблема 1: ImportError

```
ImportError: cannot import name 'User' from 'main'
```

**Решение:** Обновить импорт на `from models import User`

### Проблема 2: Тесты не находят fixtures

```
NameError: name 'get_db' is not defined
```

**Решение:** Добавить `from utils.database import get_db`

### Проблема 3: Приложение не запускается

```
ModuleNotFoundError: No module named 'models'
```

**Решение:** Убедиться, что вы в правильной директории (`backend/`)

---

## 📞 Нужна помощь?

1. **Смотри полный список файлов:** `REFACTORING_SUMMARY.md`
2. **Смотри архитектуру:** `ARCHITECTURE.md`
3. **Смотри руководство разработчика:** `DEVELOPER_GUIDE.md`
4. **Используй старую версию** (если критично): `main_old.py`

### Откат на старую версию (крайний случай)

```bash
cd backend
mv main.py main_v2.py
mv main_old.py main.py
python main.py
```

Но лучше обновить импорты - это займет 5-10 минут!

---

## 🎉 Преимущества новой структуры

После миграции вы получите:

- ✅ **Читаемость** - легко найти нужный код
- ✅ **Поддерживаемость** - изменения локализованы
- ✅ **Тестируемость** - можно тестировать модули по отдельности
- ✅ **Масштабируемость** - легко добавлять функции
- ✅ **Best Practices** - следование Clean Architecture

---

**Версия:** 2.0.0  
**Дата:** 25 ноября 2025  
**Время миграции:** ~10 минут для обновления импортов

