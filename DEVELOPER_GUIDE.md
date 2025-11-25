# 👨‍💻 Руководство разработчика (v2.0.0)

## 🎯 Быстрый старт для новых разработчиков

### Структура проекта

```
backend/
├── main.py              ← Точка входа (90 строк)
├── config.py            ← Конфигурация
├── dependencies.py      ← FastAPI dependencies
├── models/              ← SQLAlchemy модели (БД структура)
├── schemas/             ← Pydantic схемы (API валидация)
├── services/            ← Бизнес-логика
├── api/                 ← API endpoints
└── utils/               ← Утилиты
```

### Принцип работы

```
HTTP Request
    ↓
main.py (роутинг)
    ↓
api/module.py (endpoint handler)
    ↓
dependencies.py (авторизация)
    ↓
services/module_service.py (бизнес-логика)
    ↓
models/module.py (работа с БД)
    ↓
schemas/module.py (валидация ответа)
    ↓
HTTP Response
```

---

## 📝 Как добавить новую функциональность

### Пример: Добавить комментарии к историям

#### Шаг 1: Создать модель (models/comment.py)

```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.database import Base

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("user_stories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    story = relationship("UserStory", back_populates="comments")
    user = relationship("User")
```

#### Шаг 2: Обновить связи в models/story.py

```python
class UserStory(Base):
    # ... существующие поля ...
    
    # Добавить relationship
    comments = relationship("Comment", back_populates="story", cascade="all, delete-orphan")
```

#### Шаг 3: Создать схему (schemas/comment.py)

```python
from datetime import datetime
from pydantic import BaseModel

class CommentCreate(BaseModel):
    story_id: int
    text: str

class CommentResponse(BaseModel):
    id: int
    story_id: int
    user_id: int
    text: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

#### Шаг 4: Создать сервис (опционально, если нужна сложная логика)

```python
# services/comment_service.py
from sqlalchemy.orm import Session
from models import Comment

def create_comment(db: Session, story_id: int, user_id: int, text: str) -> Comment:
    """Создает комментарий с валидацией"""
    # Бизнес-логика здесь
    comment = Comment(story_id=story_id, user_id=user_id, text=text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
```

#### Шаг 5: Создать API endpoints (api/comments.py)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils.database import get_db
from models import Comment, User
from schemas.comment import CommentCreate, CommentResponse
from dependencies import get_current_active_user

router = APIRouter(prefix="", tags=["comments"])

@router.post("/comment", response_model=CommentResponse)
def create_comment(
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создает комментарий к истории"""
    # Проверка прав доступа
    # ...
    
    comment = Comment(
        story_id=comment_data.story_id,
        user_id=current_user.id,
        text=comment_data.text
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return comment

@router.get("/story/{story_id}/comments")
def get_comments(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получает комментарии к истории"""
    comments = db.query(Comment).filter(Comment.story_id == story_id).all()
    return comments
```

#### Шаг 6: Подключить роутер в main.py

```python
from api import health, auth, projects, stories, comments

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(stories.router)
app.include_router(comments.router)  # ← Добавить
```

#### Шаг 7: Создать миграцию

```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "Add comments table"
alembic upgrade head
```

---

## 🔧 Работа с существующим кодом

### Как найти нужную логику?

| Что ищу | Где искать |
|---------|------------|
| Структура БД таблицы | `models/{название}.py` |
| Валидация API запроса/ответа | `schemas/{название}.py` |
| Бизнес-логика (JWT, AI, etc.) | `services/{название}_service.py` |
| API endpoint | `api/{название}.py` |
| Конфигурация (ENV) | `config.py` |
| Проверка авторизации | `dependencies.py` |

### Примеры частых задач

#### 1. Изменить валидацию API

```python
# schemas/story.py
class StoryCreate(BaseModel):
    title: str
    description: Optional[str] = None
    # Добавить новое поле:
    tags: Optional[List[str]] = []
```

#### 2. Добавить бизнес-логику

```python
# services/story_service.py
def validate_story_title(title: str) -> bool:
    """Валидирует заголовок истории"""
    if len(title) < 5:
        return False
    if len(title) > 100:
        return False
    return True
```

#### 3. Использовать сервис в endpoint

```python
# api/stories.py
from services.story_service import validate_story_title

@router.post("/story")
def create_story(story: StoryCreate, ...):
    if not validate_story_title(story.title):
        raise HTTPException(400, "Invalid story title")
    # ...
```

#### 4. Добавить индекс в БД

```python
# models/comment.py
from sqlalchemy import Index

class Comment(Base):
    # ... поля ...
    
    __table_args__ = (
        Index('idx_comment_story_created', 'story_id', 'created_at'),
    )
```

---

## 🧪 Тестирование

### Структура тестов

```python
# test_my_feature.py
import pytest
from fastapi.testclient import TestClient
from main import app
from utils.database import get_db

client = TestClient(app)

def test_my_endpoint():
    # Получить токен
    response = client.post("/token", data={...})
    token = response.json()["access_token"]
    
    # Тестировать endpoint
    response = client.post(
        "/my-endpoint",
        json={...},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

### Запуск тестов

```bash
cd backend
source venv/bin/activate
pytest test_main.py -v
```

---

## 🔍 Отладка

### Логирование

```python
import logging
logger = logging.getLogger(__name__)

# В коде
logger.info("User authenticated successfully")
logger.warning("Redis connection failed")
logger.error("Database query failed", exc_info=True)
```

### Проверка запросов

```bash
# Swagger UI
open http://localhost:8000/docs

# Проверка здоровья
curl http://localhost:8000/health
```

---

## 📚 Best Practices

### 1. Именование

- **Models**: CamelCase (User, UserStory)
- **Functions**: snake_case (create_user, authenticate_user)
- **Files**: snake_case (auth_service.py)
- **Constants**: UPPER_CASE (JWT_SECRET_KEY)

### 2. Структура функций

```python
def my_function(
    required_param: str,
    optional_param: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ReturnType:
    """
    Краткое описание.
    
    Args:
        required_param: Описание
        optional_param: Описание
        
    Returns:
        Описание возвращаемого значения
        
    Raises:
        HTTPException: Когда возникает ошибка
    """
    # Валидация
    if not required_param:
        raise HTTPException(400, "Required param missing")
    
    # Бизнес-логика
    result = do_something(required_param)
    
    # Возврат
    return result
```

### 3. Обработка ошибок

```python
try:
    # Опасная операция
    result = dangerous_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(500, "Operation failed")
```

### 4. Использование dependencies

```python
# ✅ Хорошо - используем dependency
@router.get("/protected")
def protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    return {"user": current_user.email}

# ❌ Плохо - ручная проверка токена
@router.get("/protected")
def protected_endpoint(token: str):
    # Повторяем логику из dependencies
    ...
```

---

## 🚀 Deployment

### Локальная разработка

```bash
cd backend
source venv/bin/activate
python main.py
```

### Production (Render.com)

Изменения автоматически деплоятся при push в main ветку.

---

## 📞 Помощь

Если что-то непонятно:
1. Смотри `ARCHITECTURE.md` для общего понимания
2. Смотри `REFACTORING_SUMMARY.md` для деталей рефакторинга
3. Смотри примеры в существующем коде (api/, services/)

---

**Версия:** 2.0.0  
**Обновлено:** 25 ноября 2025

