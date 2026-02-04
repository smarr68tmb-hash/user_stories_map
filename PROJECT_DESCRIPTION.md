# Описание проекта для мастер-промпта

## AI User Story Mapper

**AI User Story Mapper** — веб-приложение для автоматической генерации карт пользовательских историй (User Story Maps) на основе текстовых требований с использованием искусственного интеллекта.

### Основная функциональность

Проект позволяет пользователям вводить текстовое описание продукта или требований, после чего AI автоматически генерирует структурированную карту пользовательских историй с иерархией: **Activities → User Tasks → User Stories**, распределёнными по релизам (MVP, Release 1, Later). Система автоматически выделяет роли пользователей (Personas), генерирует acceptance criteria для каждой истории и приоритизирует их.

### Технологический стек

**Backend:**
- FastAPI (Python) — REST API с модульной архитектурой (Clean Architecture)
- PostgreSQL (Supabase) — база данных
- SQLAlchemy + Alembic — ORM и миграции
- JWT аутентификация с Refresh Tokens
- Redis — кеширование AI ответов (опционально)
- Multiple AI Providers с автоматическим fallback: Gemini (приоритет) → Groq → OpenAI

**Frontend:**
- React + Vite — SPA приложение
- Tailwind CSS — стилизация
- @dnd-kit — drag & drop для перемещения историй
- Axios с автоматическим обновлением токенов

### Ключевые особенности

1. **Two-Stage AI Processing** — двухэтапная обработка: сначала AI улучшает и структурирует требования, затем генерирует карту
2. **Real-time Streaming** — генерация карты с live прогрессом через Server-Sent Events (SSE)
3. **AI Assistant** — точечное улучшение отдельных историй с Quick Actions (добавить детали, улучшить критерии, разделить, edge cases)
4. **Анализ качества** — TF-IDF анализ схожести историй для поиска дубликатов и валидация структуры карты с оценкой качества (0-100)
5. **Demo-режим** — возможность попробовать генерацию без регистрации (rate limit: 3 запроса/час)
6. **Статусы историй** — отслеживание прогресса: todo → in_progress → done → blocked

### Архитектура

Проект следует принципам Clean Architecture с разделением на слои:
- **Models** — SQLAlchemy ORM модели (User, Project, Activity, UserTask, Release, UserStory)
- **Schemas** — Pydantic схемы для валидации API
- **Services** — бизнес-логика (auth_service, ai_service, similarity_service, validation_service)
- **API** — FastAPI роутеры (auth, projects, stories, analysis, epics)

AI провайдеры реализованы через Strategy Pattern с единым интерфейсом, что позволяет легко добавлять новых провайдеров и автоматически переключаться между ними при ошибках или лимитах.

### Deployment

- Production: Render.com (backend + frontend)
- Database: Supabase (управляемая PostgreSQL)
- CI/CD: GitHub Actions с автоматическим тестированием

### Безопасность

- JWT аутентификация с token rotation
- Rate limiting для защиты от злоупотреблений
- CORS настройки
- Password hashing (bcrypt)
- Изоляция данных по пользователям
- HTTPS в production




