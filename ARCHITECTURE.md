# Архитектура AI User Story Mapper

## Обзор системы

AI User Story Mapper — это веб-приложение для автоматической генерации карт пользовательских историй (User Story Maps) на основе текстовых требований с использованием AI.

## Технологический стек

### Backend (v2.0.0+ - Модульная архитектура)

**Структура:**
```
backend/
├── main.py              # FastAPI app (90 строк)
├── config.py            # Конфигурация с валидацией
├── dependencies.py      # FastAPI dependencies
├── models/              # SQLAlchemy ORM модели
├── schemas/             # Pydantic валидация API
├── services/            # Бизнес-логика (Service Layer)
├── api/                 # API роуты (Endpoint handlers)
└── utils/               # Утилиты (database setup)
```

**Технологии:**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy** — ORM для работы с БД
- **PostgreSQL** — база данных (production)
- **Alembic** — миграции БД
- **AI провайдеры** — Gemini (приоритет по умолчанию) → Groq → OpenAI с автоматическим fallback
- **Two-Stage AI** — отдельные модели для enhancement/generation/assistant (по умолчанию Gemini `gemini-2.0-flash-exp`)
- **Redis** — кеширование AI ответов
- **JWT** — аутентификация
- **Slowapi** — rate limiting

**Архитектурные принципы:**
- **Clean Architecture** - разделение на слои
- **Service Layer Pattern** - переиспользуемая бизнес-логика
- **Dependency Injection** - FastAPI dependencies
- **SOLID** - Single Responsibility Principle

### Frontend
- **React** — UI библиотека
- **Vite** — сборщик
- **Tailwind CSS** — стилизация
- **Axios** — HTTP клиент
- **@dnd-kit** — drag-and-drop функциональность

---

## Backend Модульная архитектура (v2.0.0)

### Разделение на слои (Clean Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                   API Layer (api/)                      │
│  ┌───────────┬──────────────┬──────────────┬─────────┐ │
│  │ auth.py   │ projects.py  │ stories.py   │health.py│ │
│  │           │ analysis.py  │              │         │ │
│  └─────┬─────┴──────┬───────┴──────┬───────┴────┬────┘ │
└────────┼────────────┼──────────────┼────────────┼──────┘
         │            │              │            │
         ↓            ↓              ↓            ↓
┌─────────────────────────────────────────────────────────┐
│              Service Layer (services/)                  │
│  ┌──────────────────────┬──────────────────────────┐   │
│  │  auth_service.py     │   ai_service.py          │   │
│  │  - authenticate_user │   - two-stage AI flow    │   │
│  │  - create_tokens     │   - provider fallback    │   │
│  │  - verify_password   │   - cache_results        │   │
│  ├──────────────────────┼──────────────────────────┤   │
│  │  similarity_service  │   validation_service     │   │
│  │  - analyze_similarity│   - validate_project_map │   │
│  │  - TF-IDF vectors    │   - calculate_score      │   │
│  │  - find_duplicates   │   - get_recommendations  │   │
│  └──────────┬───────────┴──────────┬───────────────┘   │
└─────────────┼──────────────────────┼───────────────────┘
              │                      │
              ↓                      ↓
┌─────────────────────────────────────────────────────────┐
│              Data Layer (models/ + schemas/)            │
│  ┌──────────────┬───────────────┬──────────────┐       │
│  │ models/      │ schemas/      │ utils/       │       │
│  │ - user.py    │ - user.py     │ - database.py│       │
│  │ - project.py │ - project.py  │              │       │
│  │ - story.py   │ - story.py    │              │       │
│  └──────────────┴───────────────┴──────────────┘       │
└─────────────────────────────────────────────────────────┘
```

### Файловая структура backend/

```
backend/
├── main.py                    # 90 строк - FastAPI app setup
│   └── Подключает роуты из api/
│
├── config.py                  # Конфигурация с валидацией
│   ├── Загрузка ENV переменных
│   ├── Валидация JWT_SECRET_KEY
│   └── Автоопределение AI провайдера
│
├── dependencies.py            # Переиспользуемые dependencies
│   ├── get_current_user()
│   ├── get_current_active_user()
│   └── OAuth2 scheme
│
├── models/                    # SQLAlchemy ORM модели
│   ├── user.py               # User, RefreshToken
│   ├── project.py            # Project, Activity, UserTask, Release
│   └── story.py              # UserStory + композитные индексы
│
├── schemas/                   # Pydantic схемы (API validation)
│   ├── user.py               # UserCreate, UserResponse, Token
│   ├── project.py            # ProjectResponse, RequirementsInput
│   ├── story.py              # StoryCreate, StoryUpdate, StoryMove
│   └── analysis.py           # ValidationResult, SimilarityResult (v2.3.0)
│
├── services/                  # Бизнес-логика (Service Layer)
│   ├── auth_service.py       # JWT, password hashing, authentication
│   │   ├── verify_password()
│   │   ├── create_access_token()
│   │   ├── create_refresh_token()
│   │   └── authenticate_user()
│   │
│   ├── ai_service.py         # AI генерация карт
│   │   ├── generate_ai_map()
│   │   ├── enhance_requirements()
│   │   ├── get_cache_key()
│   │   ├── Fallback Gemini → Groq → OpenAI
│   │   └── Настраиваемые модели для Stage1/Stage2/assistant
│   │
│   ├── similarity_service.py # Анализ схожести историй (v2.3.0)
│   │   ├── analyze_similarity()
│   │   ├── calculate_similarity_tfidf()
│   │   ├── find_similar_groups()
│   │   └── get_similarity_summary()
│   │
│   └── validation_service.py # Валидация структуры карты (v2.3.0)
│       ├── validate_project_map()
│       ├── calculate_validation_score()
│       └── get_validation_summary()
│
├── api/                       # API роуты (Endpoint handlers)
│   ├── auth.py               # POST /register, /token, /refresh, /logout
│   │                         # GET /me
│   │
│   ├── projects.py           # POST /generate-map, /enhance-requirements
│   │                         # GET /project/{id}, /projects
│   │
│   ├── stories.py            # POST /story, /story/{id}/ai-improve
│   │                         # PUT /story/{id}
│   │                         # DELETE /story/{id}
│   │                         # PATCH /story/{id}/move
│   │
│   ├── analysis.py           # GET /project/{id}/validate (v2.3.0)
│   │                         # GET /project/{id}/analyze/similarity
│   │                         # POST /project/{id}/analyze/full
│   │
│   └── health.py             # GET /health, /ready
│
└── utils/
    └── database.py           # Database setup, SessionLocal, get_db
```

### Поток запроса (Request Flow)

```
1. HTTP Request → main.py (FastAPI app)
   ↓
2. Middleware (CORS, Rate Limiting)
   ↓
3. api/{module}.py (роутер обрабатывает endpoint)
   ↓
4. dependencies.py (проверка авторизации)
   ↓
5. services/{module}_service.py (бизнес-логика)
   ↓
6. models/{module}.py (работа с БД через SQLAlchemy)
   ↓
7. schemas/{module}.py (валидация и сериализация ответа)
   ↓
8. HTTP Response
```

### Преимущества модульной архитектуры

#### 1. Separation of Concerns
- **Models** - только структура данных (SQLAlchemy)
- **Schemas** - только валидация API (Pydantic)
- **Services** - только бизнес-логика
- **API** - только обработка HTTP запросов

#### 2. Переиспользование кода
```python
# Сервис можно использовать из любого endpoint
from services.auth_service import authenticate_user

# В auth.py
user = authenticate_user(db, email, password)

# В другом endpoint тоже можно использовать
user = authenticate_user(db, form_data.username, form_data.password)
```

#### 3. Легкое тестирование
```python
# Можно тестировать сервис независимо от API
def test_authenticate_user():
    user = authenticate_user(test_db, "test@example.com", "password")
    assert user is not None
```

#### 4. Масштабируемость
Добавление новой функциональности:
1. Создать модель в `models/my_feature.py`
2. Создать схему в `schemas/my_feature.py`
3. Создать сервис в `services/my_feature_service.py`
4. Создать роуты в `api/my_feature.py`
5. Подключить роутер в `main.py`

---

## Общая архитектура системы

```plantuml
@startuml
!define RECTANGLE class

skinparam componentStyle rectangle
skinparam backgroundColor #FEFEFE
skinparam component {
  BackgroundColor<<frontend>> LightBlue
  BackgroundColor<<backend>> LightGreen
  BackgroundColor<<database>> LightYellow
  BackgroundColor<<external>> LightCoral
}

package "Frontend (React)" <<frontend>> {
  [Auth Component] as Auth
  [App Component] as App
  [StoryMap Component] as StoryMap
  [Analysis Panel] as AnalysisPanel
  [AI Assistant UI] as AIAssistantFE
  [API Client (Axios)] as ApiClient
}

package "Backend (FastAPI)" <<backend>> {
  [Authentication] as AuthAPI
  [Projects API] as ProjectsAPI
  [Stories API] as StoriesAPI
  [Analysis API] as AnalysisAPI
  [AI Assistant API] as AIAssistantAPI
  [AI Generation] as AIGen
  [Rate Limiter] as RateLimit
}

package "Data Layer" <<database>> {
  database "PostgreSQL\n(Supabase)" as DB
  database "Redis\n(Cache, optional)" as Cache
}

package "External Services" <<external>> {
  [AI Providers\n(Gemini/Groq/OpenAI)] as AI
}

Auth --> ApiClient
App --> ApiClient
StoryMap --> ApiClient
AnalysisPanel --> ApiClient
AIAssistantFE --> ApiClient

ApiClient --> AuthAPI : JWT Token
ApiClient --> ProjectsAPI : CRUD Operations
ApiClient --> StoriesAPI : CRUD Operations
ApiClient --> AnalysisAPI : Analyze/Validate
ApiClient --> AIAssistantAPI : Improve/Split

AuthAPI --> DB : Users, Tokens
ProjectsAPI --> DB : Projects, Activities
StoriesAPI --> DB : Stories, Tasks
AnalysisAPI --> DB : Projects, Stories
AIGen --> AI : Generate Map
AIGen --> Cache : Cache Results
RateLimit --> Cache : Track Requests
note right of Cache
  Optional: AI cache + rate limit counters
end note

ProjectsAPI --> AIGen : Generate
StoriesAPI --> AIAssistantAPI : AI Improve
AnalysisAPI --> AIGen : Optional AI scoring
@enduml
```

**AI провайдеры и fallback**

- Приоритет по умолчанию: `gemini → groq → openai`
- Gemini: модели `gemini-2.0-flash-exp` для enhancement/generation/assistant
- Проактивные лимиты Gemini: 230 req/day (flash), 45 req/day (pro) для автопереключения
- Настройка моделей: `GEMINI_*_MODEL`, `GROQ_*_MODEL`, `PERPLEXITY_*_MODEL`, `OPENAI_*_MODEL`, `ENHANCEMENT_MODEL`
- Настройка приоритета: `AI_PROVIDER_PRIORITY`

---

## Модель данных

```plantuml
@startuml
skinparam classAttributeIconSize 0
skinparam backgroundColor #FEFEFE

entity "User" as user {
  * id : Integer <<PK>>
  --
  * email : String
  * hashed_password : String
  full_name : String
  is_active : Boolean
  created_at : DateTime
}

entity "RefreshToken" as refresh_token {
  * id : Integer <<PK>>
  --
  * user_id : Integer <<FK>>
  * token : String
  * expires_at : DateTime
  created_at : DateTime
  revoked : Boolean
}

entity "Project" as project {
  * id : Integer <<PK>>
  --
  * user_id : Integer <<FK>>
  * name : String
  description : Text
  requirements_text : Text
  personas : JSON
  created_at : DateTime
  updated_at : DateTime
}

entity "Activity" as activity {
  * id : Integer <<PK>>
  --
  * project_id : Integer <<FK>>
  * title : String
  position : Integer
}

entity "UserTask" as user_task {
  * id : Integer <<PK>>
  --
  * activity_id : Integer <<FK>>
  * title : String
  position : Integer
}

entity "Release" as release {
  * id : Integer <<PK>>
  --
  * project_id : Integer <<FK>>
  * title : String
  position : Integer
}

entity "UserStory" as user_story {
  * id : Integer <<PK>>
  --
  * task_id : Integer <<FK>>
  * release_id : Integer <<FK>>
  * title : String
  description : Text
  priority : String
  status : String <<enum: todo|in_progress|done|blocked>>
  acceptance_criteria : JSON
  position : Integer
}

user ||--o{ refresh_token : "has many"
user ||--o{ project : "owns"
project ||--o{ activity : "contains"
project ||--o{ release : "has"
activity ||--o{ user_task : "contains"
user_task ||--o{ user_story : "has"
release ||--o{ user_story : "categorizes"
@enduml
```

### Сводный поток анализа/валидации

```plantuml
@startuml
actor User
participant "Frontend" as FE
participant "AnalysisPanel" as Panel
participant "Backend API" as BE
participant "analysis services" as ASRV

User -> FE: Открывает карту
User -> Panel: Выбирает режим\nValidate / Similarity / Full
Panel -> BE: REST call\n/validate | /analyze/similarity | /analyze/full
BE -> BE: Загружает проект/истории
BE -> ASRV: run_validation() or analyze_similarity() or full_report()
ASRV --> BE: issues, groups, score
BE --> Panel: JSON (score, issues, groups)
Panel --> User: Отображает badge/группы/рекомендации
@enduml
```

---

## Поток аутентификации

```plantuml
@startuml
actor User
participant "Frontend" as FE
participant "Backend API" as BE
database "PostgreSQL" as DB
database "Redis" as Cache

== Регистрация ==
User -> FE: Заполняет форму регистрации
FE -> BE: POST /register\n{email, password, full_name}
BE -> BE: Хеширует пароль (bcrypt)
BE -> DB: Создает User
DB --> BE: User created
BE --> FE: 201 Created
FE --> User: Успешная регистрация

== Логин ==
User -> FE: Вводит email и password
FE -> BE: POST /token\n{username, password}
BE -> DB: Находит User по email
DB --> BE: User data
BE -> BE: Проверяет пароль (bcrypt)
BE -> BE: Генерирует Access Token (JWT, 30 мин)
BE -> BE: Генерирует Refresh Token (7 дней)
BE -> DB: Сохраняет Refresh Token
BE --> FE: {access_token, refresh_token}
FE -> FE: Сохраняет токены в localStorage
FE --> User: Успешный вход

== Защищенный запрос ==
User -> FE: Выполняет действие
FE -> BE: GET /projects\nAuthorization: Bearer <access_token>
BE -> BE: Проверяет JWT токен
BE -> DB: Получает данные
DB --> BE: Projects data
BE --> FE: 200 OK + data
FE --> User: Отображает данные

== Обновление токена (401) ==
FE -> BE: GET /projects\nAuthorization: Bearer <expired_token>
BE --> FE: 401 Unauthorized
FE -> FE: Axios Interceptor перехватывает 401
FE -> BE: POST /refresh\n{refresh_token}
BE -> DB: Проверяет Refresh Token
DB --> BE: Token valid
BE -> BE: Генерирует новый Access Token
BE -> BE: Генерирует новый Refresh Token (rotation)
BE -> DB: Отзывает старый, сохраняет новый
BE --> FE: {access_token, refresh_token}
FE -> FE: Обновляет токены в localStorage
FE -> BE: Повторяет GET /projects\nAuthorization: Bearer <new_token>
BE --> FE: 200 OK + data
FE --> User: Отображает данные

== Выход ==
User -> FE: Нажимает Logout
FE -> BE: POST /logout\n{refresh_token}
BE -> DB: Отзывает Refresh Token
DB --> BE: Token revoked
BE --> FE: 200 OK
FE -> FE: Удаляет токены из localStorage
FE --> User: Перенаправление на страницу входа
@enduml
```

---

## Поток генерации User Story Map (Two-Stage)

```plantuml
@startuml
actor User
participant "Frontend" as FE
participant "Backend API" as BE
participant "AI Service" as AI
database "Redis Cache" as Cache
database "PostgreSQL" as DB

User -> FE: Вводит требования к продукту
FE -> FE: Валидация (мин. 50 символов)

== Stage 1: Enhancement (по умолчанию включен) ==
FE -> BE: POST /enhance-requirements\n{requirements_text}
BE -> BE: Rate Limiting (30 req/hour)
BE -> Cache: Проверяет кеш (TTL 24ч)
alt Кеш найден
  Cache --> BE: Cached enhancement
else
  BE -> AI: Enhance (выбор модели + fallback)
  AI --> BE: Enhanced text + confidence
  BE -> Cache: Сохраняет enhancement (TTL 24ч)
end
BE --> FE: {enhanced_text, added_aspects, confidence}
alt Использовать enhanced
  User -> FE: Выбирает enhanced_text
else Оставить original
  User -> FE: Выбирает original_text
end

== Stage 2: Generation ==
FE -> BE: POST /generate-map\n{requirements_text, use_enhanced_text}
BE -> BE: Rate Limiting (5 req/min)
BE -> BE: Генерирует cache_key\n(hash от текста)
BE -> Cache: Проверяет кеш (TTL 1ч)
alt Кеш найден
  Cache --> BE: Cached map
else
  BE -> AI: Generate map (fallback gemini→groq→openai)
  AI --> BE: JSON response
  BE -> Cache: Сохраняет результат (TTL 1ч)
  BE -> DB: Создает Project/Activities/Tasks/Releases/UserStories
end

BE --> FE: 200 OK + {project_id, map}
FE -> FE: Рендерит StoryMap компонент
FE --> User: Отображает интерактивную карту

== Редактирование ==
User -> FE: Drag & Drop карточки
FE -> BE: PATCH /story/{id}/move\n{task_id, release_id, position}
BE -> DB: Обновляет позицию Story
DB --> BE: Updated
BE --> FE: 200 OK
FE -> BE: GET /project/{id}
BE -> DB: Получает обновленный проект
DB --> BE: Project data
BE --> FE: 200 OK + project
FE --> User: Обновляет карту
@enduml
```

---

## Компонентная архитектура Frontend

```plantuml
@startuml
package "Frontend Application" {
  component "App.jsx" as App {
    [Authentication State]
    [Project State]
    [Loading State]
  }
  
  component "Auth.jsx" as Auth {
    [Login Form]
    [Register Form]
  }
  
  component "StoryMap.jsx" as StoryMap {
    [DnD Context]
    [Story Cards]
    [Add Story Form]
    [Edit Story Form]
  }
  
  component "api.js" as API {
    [Axios Instance]
    [Request Interceptor]
    [Response Interceptor]
    [Auth Methods]
  }
}

App --> Auth : "renders when not authenticated"
App --> StoryMap : "renders when authenticated"
Auth --> API : "uses auth.login/register"
StoryMap --> API : "uses api.get/post/put/delete"

API --> [localStorage] : "stores tokens"
API --> [Backend API] : "HTTP requests"

note right of API
  Автоматическое обновление токена:
  - Перехватывает 401
  - Обновляет через /refresh
  - Повторяет запрос
end note
@enduml
```

---

## Последовательность Drag & Drop

```plantuml
@startuml
actor User
participant "StoryCard" as Card
participant "DndContext" as DnD
participant "StoryMap" as Map
participant "API" as API
participant "Backend" as BE
database "PostgreSQL" as DB

User -> Card: Начинает перетаскивание
Card -> DnD: onDragStart(event)
DnD -> DnD: Сохраняет active.id

User -> Card: Перемещает над другой ячейкой
Card -> DnD: onDragOver(event)
DnD -> DnD: Обновляет over.id

User -> Card: Отпускает карточку
Card -> DnD: onDragEnd(event)
DnD -> Map: handleDragEnd({active, over})

Map -> Map: Парсит active.id\n(storyId, sourceTaskId, sourceReleaseId)
Map -> Map: Парсит over.id\n(targetTaskId, targetReleaseId)

Map -> API: PATCH /story/{storyId}/move\n{task_id, release_id, position}
API -> BE: HTTP Request + JWT
BE -> DB: UPDATE user_stories\nSET task_id, release_id, position
DB --> BE: Updated
BE --> API: 200 OK
API --> Map: Success

Map -> API: GET /project/{projectId}
API -> BE: HTTP Request + JWT
BE -> DB: SELECT project with relations
DB --> BE: Project data
BE --> API: 200 OK + project
API --> Map: Updated project

Map -> Map: onUpdate(project)
Map -> Map: Re-render with new data
Map --> User: Карточка перемещена
@enduml
```

---

## Быстрое изменение статуса истории

```plantuml
@startuml
actor User
participant "StoryCard (UI)" as Card
participant "API Client" as Api
participant "Backend API" as BE
database "PostgreSQL" as DB

User -> Card: Click status button
Card -> Api: PATCH /story/{id}/status\nnext_status()
Api -> BE: HTTP + JWT
BE -> DB: UPDATE user_stories\nSET status = next
DB --> BE: Updated
BE --> Api: 200 OK {status}
Api --> Card: Update UI (badge/progress)

note right of Card
  Цикл статусов:
  todo → in_progress → done → blocked → todo
end note
@enduml
```

---

## Rate Limiting и Безопасность

```plantuml
@startuml
participant "Client" as Client
participant "Rate Limiter" as RL
participant "Auth Middleware" as Auth
participant "API Endpoint" as API
database "Redis" as Cache
database "PostgreSQL" as DB

Client -> RL: HTTP Request
RL -> Cache: Проверяет количество запросов\n(по IP адресу)

alt Превышен лимит
  Cache --> RL: Rate limit exceeded
  RL --> Client: 429 Too Many Requests
else Лимит не превышен
  Cache --> RL: OK
  RL -> Cache: Инкрементирует счетчик
  RL -> Auth: Проверяет JWT токен
  
  alt Токен невалиден
    Auth --> Client: 401 Unauthorized
  else Токен валиден
    Auth -> Auth: Декодирует user_id из JWT
    Auth -> API: Передает request + current_user
    API -> DB: Выполняет операцию\n(только для данных пользователя)
    
    alt Пользователь не владелец
      DB --> API: Forbidden
      API --> Client: 403 Forbidden
    else Пользователь владелец
      DB --> API: Data
      API --> Client: 200 OK + data
    end
  end
end

note right of RL
  Лимиты (пример):
  - /register: 5 req/hour
  - /token: 10 req/hour
  - /enhance-requirements: 30 req/hour
  - /generate-map: 5 req/min
  - Остальные: 100 req/min
end note

note right of Auth
  JWT содержит:
  - user_id (sub)
  - exp (время истечения)
  Проверяется на каждом запросе
end note

note right of API
  Изоляция данных:
  - Проекты фильтруются по user_id
  - Stories доступны только через проекты пользователя
  - Refresh токены привязаны к user_id
end note
@enduml
```

---

## Deployment Architecture (Render + Supabase)

```plantuml
@startuml
!define RECTANGLE class

cloud "Internet" {
  actor User
}

package "Render.com" {
  node "Frontend\n(Static Site)" as FE {
    component "React App\n(dist/)" as React
  }
  
  node "Backend\n(Web Service)" as BE {
    component "FastAPI\n(Docker)" as FastAPI
  }
}

cloud "Supabase" {
  database "PostgreSQL\n(Managed)" as DB
}

cloud "External Services" {
  component "AI Providers\n(Gemini/Groq/OpenAI)" as AI
}

User --> FE : HTTPS
FE --> BE : HTTPS + JWT
BE --> DB : PostgreSQL Protocol\n(Connection Pooling)
BE --> AI : HTTPS + API Key

note right of FE
  Environment Variables:
  - VITE_API_URL
end note

note right of BE
  Environment Variables (основные):
  - DATABASE_URL
  - GEMINI_API_KEY / GROQ_API_KEY / OPENAI_API_KEY
  - AI_PROVIDER_PRIORITY (default: gemini,groq,openai)
  - GEMINI_*_MODEL / GROQ_*_MODEL / PERPLEXITY_*_MODEL / OPENAI_*_MODEL / ENHANCEMENT_MODEL
  - JWT_SECRET_KEY
  - ALLOWED_ORIGINS
  - JWT_ALGORITHM
  - JWT_ACCESS_TOKEN_EXPIRE_MINUTES
  - JWT_REFRESH_TOKEN_EXPIRE_DAYS
end note

note right of DB
  Connection String:
  postgresql://postgres.xxx:password@
  aws-1-eu-north-1.pooler.supabase.com:
  5432/postgres
end note
@enduml
```

---

## Ключевые архитектурные решения

### 1. Аутентификация
- **JWT** для stateless аутентификации
- **Refresh Tokens** для продления сессии без повторного логина
- **Token Rotation** для повышения безопасности
- **Axios Interceptors** для автоматического обновления токенов

### 2. Изоляция данных
- Все проекты привязаны к `user_id`
- Фильтрация на уровне SQL запросов
- Проверка владельца перед операциями

### 3. Rate Limiting
- Защита от DDoS и злоупотреблений
- Разные лимиты для разных эндпоинтов
- Хранение счетчиков в Redis (если доступен)

### 4. Статусы историй и прогресс
- Поле `status` в `UserStory`: `todo` → `in_progress` → `done` → `blocked` → `todo`
- Быстрое переключение статуса с карточки; визуальные индикаторы и прогресс по релизу

### 5. Кеширование
- Redis для кеширования AI ответов (TTL: 1 час)
- Уменьшение нагрузки на AI API
- Экономия на API запросах

### 6. Миграции БД
- Alembic для версионирования схемы
- Автоматический запуск миграций при деплое
- Поддержка rollback

### 7. Обработка ошибок
- Централизованная обработка на frontend (api.js)
- Детальные сообщения об ошибках
- Логирование через Sentry (опционально)

### 8. Производительность
- Connection Pooling для PostgreSQL
- Lazy loading для больших проектов
- Оптимизация SQL запросов (joinedload)
- **Композитные индексы** (v2.0.0):
  - `idx_activity_project_position` - быстрая сортировка активностей
  - `idx_task_activity_position` - быстрая сортировка задач
  - `idx_story_task_release` - быстрый поиск историй по ячейке
  - `idx_story_position` - оптимизация drag & drop операций

---

## Безопасность

### Реализованные меры:
1. **CORS** — ограничение доменов через `ALLOWED_ORIGINS`
2. **Rate Limiting** — защита от брутфорса и DDoS
3. **JWT** — безопасная аутентификация
4. **Password Hashing** — bcrypt для хранения паролей
5. **SQL Injection Protection** — SQLAlchemy ORM
6. **XSS Protection** — React автоматически экранирует
7. **HTTPS** — обязательно в production (Render)

### Рекомендации для production:
- Использовать сильный `JWT_SECRET_KEY` (минимум 32 символа)
- Настроить `ALLOWED_ORIGINS` на конкретные домены
- Включить Sentry для мониторинга ошибок
- Регулярно обновлять зависимости
- Настроить backup базы данных

---

## Масштабирование

### Текущая архитектура поддерживает:
- Горизонтальное масштабирование backend (stateless)
- Вертикальное масштабирование БД (Supabase)
- CDN для frontend (Render)

### Для дальнейшего масштабирования:
- Load Balancer перед backend
- Read Replicas для PostgreSQL
- Distributed Redis Cluster
- Message Queue для асинхронных задач
- Microservices для AI генерации

---

## Мониторинг и логирование

### Текущая реализация:
- Python logging (INFO level)
- Sentry для error tracking (опционально)
- Render встроенные логи

### Рекомендации:
- Prometheus + Grafana для метрик
- ELK Stack для централизованного логирования
- Uptime monitoring (Pingdom, UptimeRobot)
- Performance monitoring (New Relic, DataDog)

---

## Анализ схожести и валидация (v2.3.0)

### Поток анализа схожести

```plantuml
@startuml
actor User
participant "Frontend" as FE
participant "AnalysisPanel" as Panel
participant "Backend API" as BE
participant "similarity_service" as SIM

User -> FE: Нажимает "📊 Анализ карты"
FE -> Panel: Открывает модальное окно
User -> Panel: Выбирает "🔍 Схожесть"

Panel -> BE: GET /project/{id}/analyze/similarity
BE -> BE: Загружает все истории проекта
BE -> SIM: analyze_similarity(project)

SIM -> SIM: Собирает тексты историй\n(title + description + acceptance_criteria)
SIM -> SIM: Предобработка текста\n(lowercase, remove punctuation)
SIM -> SIM: TF-IDF векторизация
SIM -> SIM: Cosine Similarity матрица
SIM -> SIM: Union-Find группировка\n(threshold >= 0.7)
SIM -> SIM: Классификация:\n- duplicate (>=0.9)\n- similar (>=0.7)

SIM --> BE: SimilarityResult
BE --> Panel: JSON response
Panel -> Panel: Отображает группы\nс рекомендациями
Panel --> User: Результат анализа
@enduml
```

### Поток валидации карты

```plantuml
@startuml
actor User
participant "Frontend" as FE
participant "AnalysisPanel" as Panel
participant "Backend API" as BE
participant "validation_service" as VAL

User -> Panel: Выбирает "✅ Валидация"

Panel -> BE: GET /project/{id}/validate
BE -> BE: Загружает проект с eager loading
BE -> VAL: validate_project_map(project)

VAL -> VAL: Проверка Activities
VAL -> VAL: Проверка Tasks
VAL -> VAL: Проверка Stories:\n- description\n- acceptance_criteria\n- title length
VAL -> VAL: Проверка дубликатов названий
VAL -> VAL: Проверка баланса релизов
VAL -> VAL: Расчет оценки (0-100)
VAL -> VAL: Генерация рекомендаций

VAL --> BE: ValidationResult
BE --> Panel: JSON response
Panel -> Panel: Группировка по severity:\n- error (красный)\n- warning (желтый)\n- info (синий)
Panel --> User: Результат валидации
@enduml
```

### Алгоритм TF-IDF + Cosine Similarity

```
1. Preprocessing:
   - Приведение к нижнему регистру
   - Удаление пунктуации
   - Токенизация
   - Удаление стоп-слов (русские + специфичные для User Stories)

2. TF-IDF Vectorization:
   - Term Frequency: TF(t,d) = count(t in d) / total_words(d)
   - Inverse Document Frequency: IDF(t) = log(N / df(t))
   - TF-IDF(t,d) = TF(t,d) × IDF(t)

3. Cosine Similarity:
   - similarity(A,B) = (A · B) / (||A|| × ||B||)
   - Результат: матрица NxN со значениями 0.0 - 1.0

4. Grouping (Union-Find):
   - Для каждой пары с similarity >= threshold: union(i, j)
   - Группировка компонент связности
   - Классификация: duplicate (>=0.9) или similar (>=0.7)
```

### Формула расчета качества карты

```
score = 100 - penalties + bonuses

Penalties:
- ERROR: -20 баллов (критические проблемы)
- WARNING: -5 баллов (предупреждения)
- INFO: -1 балл (информация)
- Duplicate in similarity: -10 баллов (макс. -30)

Bonuses:
- % историй с описанием × 5 (макс. +5)
- % историй с AC × 5 (макс. +5)

score = max(0, min(100, score))
```
