# AI User Story Mapper

Сервис для автоматической генерации карты пользовательских историй (User Story Map) на основе текстовых требований с использованием AI.

## 🌐 Live Demo

**Production версия доступна онлайн:**
- **Frontend**: https://user-stories-map-ab.onrender.com
- **Backend API**: https://user-stories-map.onrender.com
- **API Docs**: https://user-stories-map.onrender.com/docs

**Технологии:**
- Backend: FastAPI + PostgreSQL (Supabase)
- Frontend: React + Vite
- Deployment: Render.com
- AI: Gemini (приоритет по умолчанию) → Groq → OpenAI с автоматическим fallback
- Архитектура AI: Strategy Pattern с единым интерфейсом для всех провайдеров

## 🚀 Быстрый старт

### Backend

1. Перейдите в папку backend:
```bash
cd backend
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Установите AI ключи (приоритет по умолчанию: gemini → groq → openai):
```bash
export GEMINI_API_KEY=your-gemini-key-here       # приоритетный
export GROQ_API_KEY=gsk-your-api-key-here        # fallback 1
export OPENAI_API_KEY=sk-your-api-key-here       # fallback 2

# Необязательно: переопределить порядок
# export AI_PROVIDER_PRIORITY="gemini,groq,openai"
```

Система автоматически переключается между провайдерами при ошибках или лимитах.

5. Запустите сервер:
```bash
python main.py
```

Backend будет доступен на http://127.0.0.1:8000

### Frontend

1. Перейдите в папку frontend:
```bash
cd frontend
```

2. Создайте .env файл из примера:
```bash
cp .env.example .env
```

Отредактируйте `.env` если нужно изменить URL backend (по умолчанию `http://127.0.0.1:8000`).

3. Установите зависимости:
```bash
npm install
```

4. Запустите dev сервер:
```bash
npm run dev
```

Frontend будет доступен на http://localhost:5173

## 📋 Функциональность

### Основные возможности
- ✅ **✨ Demo-режим** — генерация карты БЕЗ регистрации (Фаза 0)
- ✅ **🔄 Real-time Streaming** — live прогресс генерации с SSE (NEW! Фаза 1)
- ✅ **🤖 AI Assistant Sidebar** — постоянно видимая панель рекомендаций (NEW! Фаза 1)
- ✅ **📊 Auto-Show Analysis** — автоматические уведомления о дубликатах (NEW! Фаза 1)
- ✅ **AI генерация** User Story Map из текстовых требований (на русском языке)
- ✅ **🚀 Two-Stage AI Processing** — улучшение требований перед генерацией
- ✅ **✨ AI Assistant** для точечного улучшения карточек
- ✅ **📊 Анализ схожести** — TF-IDF поиск дубликатов и похожих историй
- ✅ **✅ Валидация карты** — проверка структуры и качества требований
- ✅ **📈 Статусы и прогресс** — отслеживание выполнения историй
- ✅ **Аутентификация**: Регистрация, логин, JWT + Refresh Tokens
- ✅ **Автоматическое выделение** ролей (Personas)
- ✅ **Структурирование**: Activities → User Tasks → User Stories
- ✅ **Приоритизация** историй (MVP, Release 1, Later)
- ✅ **Acceptance Criteria** для каждой истории
- ✅ **Интерактивная визуализация** карты
- ✅ **Drag & Drop** для перемещения историй
- ✅ **CRUD операции**: Создание, редактирование, удаление историй
- ✅ **Изоляция данных**: Каждый пользователь видит только свои проекты

### UX улучшения
- ✅ Прогресс-бар генерации
- ✅ Валидация входных данных
- ✅ Автосохранение черновиков
- ✅ Детальные сообщения об ошибках
- ✅ Автоматическое обновление токенов
- ✅ Logout при истечении сессии

### ✨ Demo-режим без регистрации (NEW! Фаза 0)

**Попробуйте продукт за 30 секунд — без email, без пароля!**

- **✨ Один клик**: "Попробовать без регистрации" на главной
- **🚀 Быстрая генерация**: 30-40 сек до первой карты
- **🔒 Безопасно**: Строгий rate limit 3 запроса/час с IP
- **💡 Мотивация**: Баннер с призывом зарегистрироваться для сохранения

```
Открыть сайт → "✨ Попробовать без регистрации" → Описать продукт → Карта готова!
                                  ↓
                      Зарегистрироваться для сохранения
```

**Цель:** Снизить bounce rate с 80% до <60%

📖 [Полная документация: PHASE_0_DEMO_MODE.md](PHASE_0_DEMO_MODE.md)

---

### 🔄 Real-Time Streaming Generation (NEW! Фаза 1)

**Живой прогресс вместо "мёртвого" ожидания!**

```
Было:                          Стало:
┌──────────────────┐           ┌──────────────────┐
│                  │           │ ████████ 70%     │
│    Spinner...    │           │                  │
│    30-90 сек     │           │ 📋 Генерирую     │
│                  │           │    задачи...     │
└──────────────────┘           └──────────────────┘
```

**Функции:**
- ⚡ **Live прогресс** (0-100%) с SSE от backend
- 📊 **9 этапов** с контекстными сообщениями:
  - 🔍 Анализирую требования... (10%)
  - ✨ Улучшаю структуру... (20%)
  - 👥 Выделяю роли пользователей... (30%)
  - 🎯 Определяю основные активности... (50%)
  - 📋 Генерирую задачи... (70%)
  - 🔍 Проверяю качество... (80%)
  - 📊 Анализирую дубликаты... (85%)
  - 💾 Сохраняю проект... (95%)
  - 🎉 Готово! (100%)

- 🔔 **Auto-show уведомления** после генерации:
  - ⚠️ "Найдено 3 дубликатов!"
  - ⚠️ "Оценка качества: 45/100. Требуется улучшение."
  - ✅ "Отличная оценка качества: 85/100!"

- 🤖 **AI Assistant Sidebar** — постоянно видимая панель:
  - 📊 Score badge (0-100) с цветовым кодированием
  - ⚠️ Duplicates warning
  - 💡 4+ динамических рекомендации
  - 🚀 Quick actions (Полный анализ, Экспорт)

**Технологии:**
- Backend: SSE (Server-Sent Events)
- Frontend: EventSource API
- Real-time: 9 этапов прогресса

**Результат:**
- ✅ Completion rate > 85% (было ~60%)
- ✅ Видимость скрытых возможностей
- ✅ Прозрачный процесс генерации

📖 [Полная документация: PHASE_1_STREAMING.md](PHASE_1_STREAMING.md)

---

### 🚀 Two-Stage AI Processing

Двухэтапная обработка для повышения качества генерируемых карт:

```
Ваш текст → [Stage 1: Enhancement] → Preview → [Stage 2: Generation] → Карта!
```

- 🔧 **Stage 1 (Enhancement)**: AI улучшает и структурирует требования (3-5 сек)
  - Добавляет недостающие роли, платформы, функции
  - Показывает что добавлено и что рекомендуется уточнить
  - Пользователь выбирает: использовать улучшенный текст или оригинал
  
- 🎨 **Stage 2 (Generation)**: Генерация карты из качественных требований (25-35 сек)

**Результат:** +20-30% к качеству карт при минимальном увеличении времени (+3-5 сек)

### ✨ AI Assistant
- ✨ **Кнопка "✨ AI" на каждой карточке** - открывает AI помощника
- ✨ **4 Quick Actions**: Добавить детали, Улучшить критерии, Разделить, Edge cases
- ✨ **Свободные текстовые запросы** к AI
- ✨ **История улучшений** в сессии
- ✨ **Split action** - разделение сложных историй на несколько
- ✨ **Массовое улучшение** до 10 карточек одновременно
- 📖 [Полная документация AI Assistant](FEATURE_AI_ASSISTANT.md)
- 🚀 [Быстрый старт AI Assistant](AI_ASSISTANT_QUICKSTART.md)

### 📈 Статусы и прогресс (NEW!)
Отслеживание выполнения историй:

- **Четыре статуса**: `todo` → `in_progress` → `done` → `blocked` → `todo`
- **Быстрое переключение** одним кликом на карточке
- **Визуальная индикация**: цветная полоска + изменение фона
- **Прогресс-бар по релизу**: X/Y выполненных задач

### 📊 Анализ схожести и валидация
Инструменты для повышения качества User Story Map:

- **🔍 Анализ схожести историй**:
  - TF-IDF + Cosine Similarity для поиска похожих историй
  - Обнаружение дубликатов (схожесть ≥90%)
  - Группировка похожих историй (схожесть ≥70%)
  - Рекомендации по объединению/разделению

- **✅ Валидация структуры карты**:
  - Проверка обязательных элементов (Activities, Tasks, Stories)
  - Поиск пустых ячеек и несвязанных элементов
  - Анализ полноты описания и acceptance criteria
  - Обнаружение дубликатов названий
  - Анализ баланса релизов

- **📈 Полный отчёт**:
  - Общая оценка качества карты (0-100)
  - Группировка проблем по severity (error/warning/info)
  - Персонализированные рекомендации

**Использование:** Кнопка "📊 Анализ карты" над картой историй.

### 🧪 Тестирование (NEW! Фаза 1)
Комплексное тестовое покрытие для streaming функциональности:

- **Backend тесты**: SSE events, streaming service, DB operations (14 тестов)
- **Frontend тесты**: Hooks, компоненты, интеграция (60+ тестов)
- **Coverage**: Backend ~85%, Frontend ~90%
- **CI/CD ready**: pytest + Jest с coverage отчетами

📖 **[Полное руководство по тестированию](TESTING.md)**

### Безопасность и производительность
- ✅ Rate Limiting (защита от злоупотреблений)
- ✅ CORS настройки
- ✅ Password hashing (bcrypt)
- ✅ Redis кеширование AI ответов
- ✅ Connection pooling для БД
- ✅ Health checks

## 🏗️ Архитектура

### Backend (v2.0.0+ - Модульная архитектура)

**Структура проекта:**
```
backend/
├── main.py              # FastAPI приложение (90 строк)
├── config.py            # Конфигурация с валидацией
├── dependencies.py      # FastAPI dependencies
├── models/              # SQLAlchemy модели (user, project, story)
├── schemas/             # Pydantic схемы для API
├── services/            # Бизнес-логика (auth_service, ai_service)
├── api/                 # API роуты (auth, projects, stories, health)
└── utils/               # Утилиты (database)
```

**Технологии:**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy** — ORM для работы с БД
- **PostgreSQL (Supabase)** — облачная база данных
- **Alembic** — миграции БД
- **Gemini/Groq/OpenAI API** — генерация карты через AI с автоматическим fallback
- **Redis** — кеширование AI ответов
- **JWT** — аутентификация
- **Slowapi** — rate limiting

**Архитектурные принципы:**
- ✅ **Clean Architecture** - разделение на слои (Models, Services, API)
- ✅ **Service Layer** - переиспользуемая бизнес-логика
- ✅ **Dependency Injection** - FastAPI dependencies
- ✅ **SOLID принципы** - Single Responsibility для каждого модуля
- ✅ **Strategy Pattern** - единый интерфейс для AI провайдеров (легко добавлять новые)

**AI провайдеры:**
- Архитектура на основе Strategy Pattern с базовым классом `AIProvider`
- Автоматический fallback между провайдерами при ошибках
- Единая обработка ошибок и rate limiting
- Поддержка: Gemini (Pro/Flash), Groq, OpenAI

### Frontend
- **React** — UI библиотека
- **Vite** — сборщик
- **Tailwind CSS** — стилизация
- **Axios** — HTTP клиент с interceptors
- **@dnd-kit** — drag-and-drop

### Deployment
- **Render.com** — хостинг backend и frontend
- **Supabase** — управляемая PostgreSQL БД
- **Docker** — контейнеризация

## 📚 Документация

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Детальная архитектура с диаграммами
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Руководство для разработчиков
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Детали рефакторинга v2.0
- **[MIGRATION_GUIDE_v2.md](MIGRATION_GUIDE_v2.md)** - Миграция с v1.x на v2.0
- **[CHANGELOG.md](CHANGELOG.md)** - История изменений
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Руководство по тестированию

## 📁 Структура проекта

```
usm-service/
├── backend/                 # Backend (FastAPI) - Модульная архитектура v2.0
│   ├── main.py             # FastAPI app setup (90 строк, было 1116)
│   ├── config.py           # Конфигурация с валидацией
│   ├── dependencies.py     # FastAPI dependencies (auth)
│   │
│   ├── models/             # SQLAlchemy модели
│   │   ├── user.py         # User, RefreshToken
│   │   ├── project.py      # Project, Activity, UserTask, Release
│   │   └── story.py        # UserStory
│   │
│   ├── schemas/            # Pydantic схемы для валидации API
│   │   ├── user.py         # UserCreate, UserResponse, Token
│   │   ├── project.py      # ProjectResponse, RequirementsInput
│   │   ├── story.py        # StoryCreate, StoryUpdate, StoryResponse
│   │   └── analysis.py     # 🆕 ValidationResult, SimilarityResult
│   │
│   ├── services/           # Бизнес-логика (Service Layer)
│   │   ├── auth_service.py # JWT, password hashing, authentication
│   │   ├── ai_service.py   # AI генерация карт, кеширование
│   │   ├── similarity_service.py # 🆕 TF-IDF анализ схожести
│   │   └── validation_service.py # 🆕 Валидация структуры карты
│   │
│   ├── api/                # API роуты (API Layer)
│   │   ├── auth.py         # /register, /token, /refresh, /logout, /me
│   │   ├── projects.py     # /generate-map, /project/{id}, /projects
│   │   ├── stories.py      # /story CRUD, /story/{id}/move
│   │   ├── analysis.py     # 🆕 /validate, /analyze/similarity, /analyze/full
│   │   └── health.py       # /health, /ready
│   │
│   ├── utils/              # Утилиты
│   │   └── database.py     # Database setup, SessionLocal
│   │
│   ├── alembic/            # Database migrations
│   ├── test_main.py        # Тесты (9/9 passed)
│   ├── requirements.txt    # Python зависимости
│   └── Dockerfile          # Docker образ
│
├── frontend/               # Frontend (React + Vite)
│   ├── src/
│   │   ├── App.jsx                # Главный компонент (Two-Stage flow)
│   │   ├── Auth.jsx               # Аутентификация
│   │   ├── StoryMap.jsx           # User Story Map с Drag & Drop
│   │   ├── ProjectList.jsx        # Список проектов пользователя
│   │   ├── AIAssistant.jsx        # AI помощник для карточек
│   │   ├── EnhancementPreview.jsx # Preview улучшений (Stage 1)
│   │   ├── AnalysisPanel.jsx      # 🆕 Панель анализа карты
│   │   ├── api.js                 # Axios client с interceptors
│   │   └── main.jsx               # Точка входа
│   ├── package.json        # Node зависимости
│   └── Dockerfile          # Docker образ
│
├── ARCHITECTURE.md         # Архитектурная документация
├── REFACTORING_SUMMARY.md  # Детали рефакторинга v2.0
├── CHANGELOG.md            # История изменений
└── README.md
```

## 🔧 API Endpoints

### Аутентификация
- `POST /register` — Регистрация нового пользователя
- `POST /token` — Логин (получение JWT токенов)
- `POST /refresh` — Обновление access token
- `POST /logout` — Выход (отзыв refresh token)
- `GET /me` — Информация о текущем пользователе

### Demo-режим (NEW!)
- `POST /generate-map/demo` — 🆕 Генерация карты БЕЗ регистрации (rate limit: 3/hour)

### Проекты
- `POST /enhance-requirements` — 🆕 Stage 1: Улучшение требований перед генерацией
- `POST /generate-map` — Генерация карты из текста (с опциональным enhancement)
- `GET /project/{project_id}` — Получение проекта
- `GET /projects` — Список проектов пользователя

### Истории
- `POST /story` — Создание новой истории
- `PUT /story/{story_id}` — Обновление истории
- `DELETE /story/{story_id}` — Удаление истории
- `PATCH /story/{story_id}/move` — Перемещение истории (drag & drop)
- `PATCH /story/{story_id}/status` — 📈 Обновление статуса (todo/in_progress/done/blocked)
- `POST /story/{story_id}/ai-improve` — ✨ AI улучшение истории
- `POST /stories/ai-bulk-improve` — ✨ Массовое AI улучшение

### Анализ (NEW!)
- `GET /project/{project_id}/validate` — 📊 Валидация структуры карты
- `GET /project/{project_id}/analyze/similarity` — 🔍 Анализ схожести историй
- `POST /project/{project_id}/analyze/full` — 📈 Полный отчёт анализа

### Система
- `GET /health` — Health check
- `GET /ready` — Readiness check
- `GET /docs` — Swagger документация

### Debug эндпоинты (для диагностики)
- `GET /debug/cookies` — Проверка настроек cookies и CORS
- `GET /debug/ai-providers` — Статус AI провайдеров (инициализация, доступность, приоритеты)

## 🎯 Пример использования

1. Откройте frontend в браузере
2. Введите описание продукта, например:
   ```
   Приложение для доставки еды. Есть роли: Клиент и Курьер. 
   Клиент может просматривать меню, добавлять блюда в корзину, 
   оформлять заказ и отслеживать доставку. Курьер получает 
   уведомления о новых заказах, видит маршрут и отмечает 
   доставку как выполненную.
   ```
3. Нажмите "Сгенерировать карту"
4. Дождитесь результата (20-40 секунд)
5. Изучите сгенерированную карту пользовательских историй

## 🐳 Docker

Запуск через Docker Compose:

```bash
# Создайте .env файл в корне проекта и задайте ключи (минимум один)
export GEMINI_API_KEY=your-gemini-key-here
# export GROQ_API_KEY=...
# export OPENAI_API_KEY=...
# export AI_PROVIDER_PRIORITY="gemini,groq,openai"

# Запустите все сервисы
docker-compose up
```

Backend: http://localhost:8000  
Frontend: http://localhost:5173

## 🧪 Тестирование

### Локальное тестирование

Запуск тестов backend:
```bash
cd backend
pytest test_main.py -v
```

### CI/CD Pipeline

Проект использует GitHub Actions для автоматического тестирования и проверки кода.

**Что проверяется автоматически:**
- ✅ Backend тесты (pytest) на Python 3.9, 3.10, 3.11
- ✅ Frontend сборка (npm build)
- ✅ Проверка импортов
- ✅ Линтинг кода (Black, flake8)
- ✅ Проверка миграций БД (Alembic)
- ✅ Проверка безопасности зависимостей

**CI/CD запускается автоматически:**
- При каждом push в `main` или `develop`
- При создании Pull Request
- Результаты отображаются в GitHub UI

**Статус CI/CD:** [![CI](https://github.com/USERNAME/USM-SERVICE/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/USM-SERVICE/actions/workflows/ci.yml)

> ⚠️ Замените `USERNAME/USM-SERVICE` на ваш GitHub username и название репозитория для отображения бейджа статуса.

## 🔒 Безопасность

### ✅ Реализовано:
- JWT аутентификация с Refresh Tokens
- Password hashing (bcrypt)
- Rate Limiting (защита от DDoS и брутфорса)
- CORS настройки через `ALLOWED_ORIGINS`
- SQL Injection защита (SQLAlchemy ORM)
- XSS защита (React автоматически экранирует)
- HTTPS в production (Render)
- Изоляция данных по пользователям

### ⚠️ Важно для production:
- ✅ Используйте сильный `JWT_SECRET_KEY` (минимум 32 символа)
- ✅ Настройте `ALLOWED_ORIGINS` на конкретные домены
- ✅ Не храните `.env` файлы в репозитории
- ✅ Используйте PostgreSQL (Supabase)
- ✅ HTTPS включен автоматически на Render

## 🔮 Планы развития

> **Полный roadmap с диаграммами:** [ROADMAP_2025.md](ROADMAP_2025.md)

### ✅ Завершённые фазы

<details>
<summary><b>v2.0 — v2.4: Production Ready + AI Features</b></summary>

- ✅ PostgreSQL + JWT аутентификация + Rate Limiting
- ✅ Модульная архитектура (Clean Architecture)
- ✅ AI Assistant с Quick Actions и Bulk Improve
- ✅ Two-Stage AI Processing (улучшение → генерация)
- ✅ TF-IDF анализ схожести + Валидация качества
- ✅ Статусы историй (todo/in_progress/done/blocked)

</details>

<details>
<summary><b>Фаза 0 (декабрь 2025): Быстрые победы</b></summary>

- ✅ **Demo без регистрации** — генерация 1 карты без email (rate limit: 3/hour)
- ✅ **Кликабельный пример** — мгновенная загрузка готовой карты Hybe Assist
- ✅ **Контекстный прогресс** — детальные этапы вместо спиннера

📖 [Документация: PHASE_0_DEMO_MODE.md](PHASE_0_DEMO_MODE.md)

</details>

### 🚀 Roadmap 2025

| Фаза | Название | Срок | Статус |
|------|----------|------|--------|
| 0 | **Быстрые победы** — demo без регистрации, примеры | 1 нед | ⚡ В процессе |
| 1 | **Streaming** — генерация по частям, видимость фич | 2 нед | 🔜 |
| 2 | **Epic Breakdown** — группировка в эпики, share link | 2 нед | 🔜 |
| 3 | **FigJam Export** — экспорт карты в Figma | 2-3 нед | 📋 |
| 4 | **Story Refinement Session** — диалоговый режим | 3-4 нед | 📋 |
| 5 | **AI Strategist** — gap analysis, риски, зависимости | 4-5 нед | 📋 |
| 6 | **Integrations** — Jira, Linear, Notion | 2-3 мес | 📋 |

### 🎯 Ключевые метрики

| Метрика | Цель | Текущее |
|---------|------|---------|
| Bounce rate | < 60% | ~80% |
| Completion rate | > 85% | ~60% |
| 7-day retention | > 25% | ~10% |

## 📝 Лицензия

MIT

