# Анализ проекта: AI User Story Mapper

**Дата анализа:** 2025-11-22  

**Версия:** 1.0.0  

**Размер кодовой базы:** ~1,440 строк кода

---

## 1. Обзор проекта

### Назначение

Веб-сервис для автоматической генерации User Story Map из текстовых требований с использованием AI (GPT-4o или Perplexity API).

### Бизнес-ценность

- Автоматизация создания User Story Map (экономия 4-8 часов ручной работы)
- Структурирование неформализованных требований
- Ускорение начальной фазы проектирования продукта

---

## 2. Архитектура

### Стек технологий

**Backend:**
- FastAPI 0.104.1 — современный async веб-фреймворк
- SQLAlchemy 2.0.23 — ORM с поддержкой async (используется в sync режиме)
- SQLite — база данных для MVP
- OpenAI API 1.3.0 — интеграция с GPT-4o/Perplexity
- Uvicorn — ASGI сервер

**Frontend:**
- React 18.2.0 — UI библиотека
- Vite 5.0.8 — современный сборщик
- Tailwind CSS 3.3.6 — utility-first CSS
- @dnd-kit — drag-and-drop функциональность
- Axios 1.6.0 — HTTP клиент

**Инфраструктура:**
- Docker + Docker Compose
- Bash скрипты для автоматизации

### Паттерны и подходы

**Backend:**
- Layered Architecture (DB → Models → API)
- Repository Pattern (через SQLAlchemy ORM)
- Dependency Injection (FastAPI Depends)
- Structured Logging

**Frontend:**
- Component-Based Architecture
- Controlled Components
- LocalStorage для черновиков
- Optimistic UI с прогресс-индикатором

---

## 3. Модель данных

### ER-структура

```
Project (1) ──< (N) Activity
              ──< (N) Release

Activity (1) ──< (N) UserTask

UserTask (1) ──< (N) UserStory
Release (1) ──< (N) UserStory
```

### Сущности

**Project:**
- id (PK)
- name
- raw_requirements (текст требований)

**Activity** (высокоуровневые цели):
- id (PK)
- project_id (FK)
- title
- position (порядок отображения)

**UserTask** (шаги для достижения целей):
- id (PK)
- activity_id (FK)
- title
- position

**Release** (релизные вехи):
- id (PK)
- project_id (FK)
- title (MVP, Release 1, Later)
- position

**UserStory:**
- id (PK)
- task_id (FK)
- release_id (FK, nullable)
- title
- description
- priority
- acceptance_criteria (JSON)
- position

### Особенности модели
- Cascade delete обеспечивает целостность при удалении
- Position поля для кастомного порядка сортировки
- JSON для хранения списка acceptance criteria
- Nullable release_id для stories без привязки к релизу

---

## 4. API эндпоинты

### POST /generate-map

**Назначение:** Генерация User Story Map из текста  
**Input:** `{ "text": "описание продукта" }`  
**Output:** `{ "project_id": 123, "message": "..." }`  
**Время выполнения:** 20-40 секунд  

**Процесс:**
1. Валидация входных данных (10-10000 символов)
2. Вызов AI API с структурированным промптом
3. Парсинг JSON ответа
4. Сохранение в БД с транзакциями
5. Возврат project_id

### GET /project/{project_id}

**Назначение:** Получение полного проекта с картой  
**Output:** Полная структура ProjectResponse с вложенными activities/tasks/stories  
**Оптимизация:** Использует `joinedload` для избежания N+1 проблемы

### GET /projects

**Назначение:** Список всех проектов  
**Output:** Список базовой информации о проектах  
**Проблема:** Отсутствует пагинация (technical debt)

### GET /docs

Swagger UI документация (автоматическая от FastAPI)

---

## 5. AI Integration

### Промпт-инжиниринг

**System Prompt:**
- Определяет роль: Product Manager + Business Analyst
- Указывает методологию: User Story Mapping
- Требует строго JSON на выходе

**User Prompt структура:**
1. Идентификация Personas
2. Создание Backbone (Activities + Tasks)
3. Разбивка на User Stories
4. Приоритизация (MVP/Release 1/Later)
5. Генерация Acceptance Criteria

**JSON Schema в промпте:**
```json
{
  "personas": [{"name": "...", "description": "..."}],
  "activities": [{
    "title": "...",
    "tasks": [{
      "title": "...",
      "stories": [{
        "title": "...",
        "description": "...",
        "priority": "MVP|Release 1|Later",
        "acceptance_criteria": ["..."]
      }]
    }]
  }],
  "releases": [{"title": "...", "order": 1}]
}
```

### Обработка ошибок API

**Типы ошибок:**
- RateLimitError → 429 с Retry-After
- APITimeoutError → 504 Gateway Timeout
- APIConnectionError → 502 Bad Gateway
- APIError → 500 Internal Server Error

**Retry механизм:**
- Экспоненциальный backoff для RateLimit
- До 3 попыток с увеличивающимся интервалом

### Поддержка провайдеров
- OpenAI (gpt-4o по умолчанию)
- Perplexity (через совместимый API)
- Автоопределение по формату API ключа

---

## 6. Frontend компоненты

### App.jsx (213 строк)

**Ответственность:**
- Управление состоянием приложения
- Взаимодействие с API
- Валидация входных данных
- Автосохранение черновиков

**Ключевые features:**
- Прогресс-бар (симуляция 10% → 90%)
- LocalStorage для черновиков с debounce 1 сек
- Валидация 10-10000 символов
- Детальная обработка ошибок HTTP

### StoryMap.jsx (426 строк)

**Ответственность:**
- Визуализация User Story Map
- Drag-and-drop функциональность
- Интерактивное управление историями

**Структура:**
- Grid layout для Activity/Task/Story
- Цветовое кодирование приоритетов (MVP/Release 1/Later)
- Accordion для Acceptance Criteria
- Responsive дизайн

---

## 7. Качество кода

### Сильные стороны

**Backend:**
✅ Структурированное логирование  
✅ Dependency injection  
✅ Eager loading для оптимизации запросов  
✅ Детальная обработка ошибок API  
✅ Транзакционность БД операций  
✅ Типизация через Pydantic  

**Frontend:**
✅ Автосохранение UX  
✅ Прогресс-индикатор  
✅ Валидация на стороне клиента  
✅ Accessibility (aria-labels)  
✅ Responsive дизайн  

**DevOps:**
✅ Docker containerization  
✅ Автоматизированные скрипты  
✅ .env конфигурация  

### Проблемные зоны

**Безопасность:**
⚠️ SQLite не подходит для production (отсутствие concurrent writes)  
⚠️ Нет rate limiting на API эндпоинтах  
⚠️ Отсутствие аутентификации/авторизации  
⚠️ CORS настроен безопасно, но для production требует конкретных доменов  

**Производительность:**
⚠️ Отсутствует кеширование AI ответов  
⚠️ Нет пагинации в `/projects`  
⚠️ Синхронная обработка AI запросов (блокирующая)  

**Масштабируемость:**
⚠️ SQLite — single writer limitation  
⚠️ Отсутствие очередей для AI запросов  
⚠️ Нет горизонтального масштабирования  

**Maintainability:**
⚠️ Промпты захардкожены в коде (нет версионирования)  
⚠️ 675 строк в main.py (нужен рефакторинг на модули)  
⚠️ Отсутствие TypeScript во frontend  
⚠️ Нет CI/CD  

**Testing:**
⚠️ Минимальное покрытие тестами (только backend/test_main.py)  
⚠️ Отсутствие интеграционных тестов  
⚠️ Нет тестов frontend  

---

## 8. Technical Debt (из CHANGELOG.md)

### Критичный
- [ ] Миграция SQLite → PostgreSQL
- [ ] Rate limiting на API
- [ ] Аутентификация/авторизация
- [ ] Кеширование AI запросов

### Важный
- [ ] Пагинация в `/projects`
- [ ] Мониторинг и алерты
- [ ] CI/CD pipeline
- [ ] Автоматические тесты в CI

### Желательный
- [ ] Рефакторинг main.py на модули
- [ ] Вынос промптов в отдельные файлы
- [ ] TypeScript для frontend
- [ ] Bundle optimization
- [ ] Unit тесты для React компонентов

---

## 9. Зависимости и безопасность

### Устаревшие версии

**Потенциально уязвимые:**
- openai==1.3.0 (текущая 1.52+, требуется обновление)
- fastapi==0.104.1 (текущая 0.115+)
- axios==1.6.0 (текущая 1.7+, были security fixes)

**Рекомендация:** Провести `pip list --outdated` и `npm outdated`

### Отсутствующие зависимости для production
- gunicorn или hypercorn (production ASGI server)
- redis (для кеширования)
- celery (для фоновых задач)
- psycopg2 (PostgreSQL driver)
- sentry-sdk (error tracking)

---

## 10. Deployment readiness

### Текущий статус: MVP/Development

**Готово для локальной разработки:**
✅ Docker Compose setup  
✅ Скрипты запуска  
✅ .env конфигурация  
✅ Базовое логирование  

**НЕ готово для production:**
❌ Нет HTTPS  
❌ Нет аутентификации  
❌ SQLite вместо PostgreSQL  
❌ Нет rate limiting  
❌ Нет мониторинга  
❌ Нет backup стратегии  
❌ Нет health check эндпоинтов  

---

## 11. Рекомендации по улучшению

### Приоритет 1 (критичный для production)

1. **Миграция на PostgreSQL**
   - Использовать Alembic для миграций
   - Настроить connection pooling
   - Добавить индексы на часто запрашиваемые поля

2. **Безопасность**
   - JWT authentication
   - Rate limiting (slowapi или middleware)
   - HTTPS обязательно
   - Environment secrets management (не .env файлы)

3. **Обработка AI запросов**
   - Async/await для AI вызовов
   - Очередь задач (Celery + Redis)
   - Кеширование ответов (Redis)
   - Timeout protection

### Приоритет 2 (важно для стабильности)

1. **Мониторинг**
   - Health check endpoints (`/health`, `/ready`)
   - Metrics (Prometheus)
   - Error tracking (Sentry)
   - Logging aggregation (ELK или Loki)

2. **Testing**
   - Unit тесты (coverage >80%)
   - Integration тесты для AI flow
   - E2E тесты (Playwright/Cypress)
   - Load testing (Locust)

3. **CI/CD**
   - GitHub Actions workflow
   - Автоматические тесты на PR
   - Docker image build & push
   - Deployment automation

### Приоритет 3 (улучшение качества)

1. **Code organization**
   - Разделить main.py на модули:
     - `models/` — SQLAlchemy models
     - `schemas/` — Pydantic schemas
     - `api/` — route handlers
     - `services/` — business logic
     - `ai/` — AI integration
   
2. **Frontend improvements**
   - TypeScript миграция
   - React Query для кеширования
   - Виртуализация для больших карт
   - Offline mode поддержка

3. **Developer Experience**
   - Pre-commit hooks (black, flake8)
   - .editorconfig
   - API documentation улучшения
   - Development troubleshooting guide

---

## 12. Метрики проекта

### Размер кодовой базы

```
Backend:  789 строк (main.py + test_main.py)
Frontend: 649 строк (App.jsx + StoryMap.jsx + main.jsx)
Total:    1,438 строк кода
```

### Сложность
- **Backend:** Средняя (монолитный файл, но хорошая структура)
- **Frontend:** Средняя (два основных компонента)
- **Infrastructure:** Низкая (простой Docker setup)

### Maintainability Index
- **Backend:** 6/10 (требует рефакторинга на модули)
- **Frontend:** 7/10 (компоненты можно разделить)
- **Tests:** 3/10 (минимальное покрытие)

---

## 13. Бизнес-метрики (оценка)

### Стоимость разработки
- Backend: ~40 часов
- Frontend: ~30 часов
- DevOps: ~10 часов
- **Total:** ~80 часов разработки

### ROI предпосылки
- Экономия времени PM: 4-8 часов на проект
- Стоимость AI API: ~$0.10-0.30 за карту
- Break-even: ~10-20 проектов при часовой ставке PM $50

### Потенциальные доработки
- Multi-tenant SaaS ($29-99/месяц)
- Интеграция с Jira/Trello (enterprise)
- White-label версия
- API для B2B интеграций

---

## 14. Выводы

### Что сделано хорошо
1. ✅ Четкая структура User Story Map (Activities → Tasks → Stories)
2. ✅ Хорошая обработка ошибок AI API
3. ✅ UX с автосохранением и прогресс-баром
4. ✅ Docker containerization для быстрого старта
5. ✅ Детальная документация (README, CHANGELOG, TESTING_GUIDE)

### Главные риски
1. ❌ Не готово для production (безопасность, масштабируемость)
2. ❌ Зависимость от AI API (single point of failure)
3. ❌ Отсутствие тестов (высокий риск регрессий)
4. ❌ Монолитная архитектура backend (сложность масштабирования)

### Рекомендация

**Текущий статус:** Работающий MVP для демонстрации концепции  

**Следующий шаг:** Провести security audit → миграция на PostgreSQL → добавить аутентификацию → настроить CI/CD

**Пригодность для разных сценариев:**
- Personal use: ✅ Готов
- Small team (<10 users): ✅ Готов с небольшими доработками
- Production SaaS: ❌ Требуется 2-3 месяца доработки

---

**Конец анализа**

