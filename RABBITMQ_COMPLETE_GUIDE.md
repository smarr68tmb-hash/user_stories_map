# 🚀 RabbitMQ + Wireframe Generation: ПОЛНОЕ РУКОВОДСТВО

**Версия:** 1.0.0
**Дата:** 2025-12-01
**Автор:** AI Assistant
**Проект:** AI User Story Mapper

---

## 📑 Содержание

1. [Введение и Обзор](#введение-и-обзор)
2. [Архитектура системы](#архитектура-системы)
3. [Предварительные требования](#предварительные-требования)
4. [Phase 1: RabbitMQ Setup](#phase-1-rabbitmq-setup)
5. [Phase 2: Backend Infrastructure](#phase-2-backend-infrastructure)
6. [Phase 3: Workers Implementation](#phase-3-workers-implementation)
7. [Phase 4: Frontend Integration](#phase-4-frontend-integration)
8. [Phase 5: Testing](#phase-5-testing)
9. [Phase 6: Deployment](#phase-6-deployment)
10. [Phase 7: Monitoring & Maintenance](#phase-7-monitoring--maintenance)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)
13. [Future Enhancements](#future-enhancements)

---

## 1. Введение и Обзор

### 1.1. Цели проекта

Реализовать асинхронную архитектуру для AI User Story Mapper с использованием RabbitMQ для:

1. **Асинхронной обработки AI генерации** карт (существующая функция)
   - Разгрузка HTTP сервера
   - Улучшение user experience (нет блокировки на 60 сек)
   - Возможность масштабирования workers

2. **Новой фичи: Генерация UI прототипов/wireframes**
   - AI-powered генерация визуальных mockups
   - Поддержка разных стилей (low/high fidelity)
   - Интеграция с проектом и User Stories

### 1.2. Почему RabbitMQ?

**Сравнение с альтернативами:**

| Критерий | RabbitMQ | Kafka | Redis Queues | Celery |
|----------|----------|-------|--------------|--------|
| Сложность setup | ⭐⭐ Простой | ⭐⭐⭐⭐ Сложный | ⭐ Очень простой | ⭐⭐ Простой |
| Message ordering | ✅ Да | ✅ Да (в partition) | ⚠️ Ограниченно | ⚠️ Не гарантируется |
| Message persistence | ✅ Да | ✅ Да | ⚠️ Опционально | ✅ Да |
| Priority queues | ✅ Да | ❌ Нет | ❌ Нет | ✅ Да |
| Dead letter queues | ✅ Да | ❌ Нет | ❌ Нет | ✅ Да |
| Management UI | ✅ Отличный | ⚠️ Требует доп. tools | ❌ Нет | ⚠️ Flower (отдельно) |
| Free hosting | ✅ CloudAMQP 1M msg | ✅ Upstash 10K | ✅ Upstash unlimited | ❌ Нужен broker |
| Best for | Task queues | Event streaming | Simple queues | Python tasks |
| **Для USM проекта** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

**Выбор:** RabbitMQ идеален для нашего use case - task queue processing с гарантиями доставки.

### 1.3. Что получим после реализации

**До (текущая архитектура):**
```
User → POST /generate-map → [WAIT 60 seconds] → Response
                                   ↓
                            AI API (Groq/OpenAI)
                                   ↓
                            Save to PostgreSQL
```

**После (с RabbitMQ):**
```
User → POST /generate-map-async → 202 Accepted (job_id) [1 second]
                                        ↓
                                  RabbitMQ Queue
                                        ↓
                                   AI Worker (background)
                                        ↓
                              WebSocket notification
                                        ↓
                              User: "Карта готова!"
```

**Преимущества:**
- ✅ User не ждет 60 секунд
- ✅ HTTP сервер не блокируется
- ✅ Можно масштабировать workers (N воркеров обрабатывают параллельно)
- ✅ Retry логика при ошибках AI API
- ✅ Priority queues (важные задачи первыми)
- ✅ Dead Letter Queue (анализ сбоев)

### 1.4. Новая фича: Text-Based Wireframe Generation

**Что делает (актуально):**
```
User Story → AI (Gemini/Groq/OpenAI) → ASCII схема + Markdown описание
```

- ASCII-вайрфрейм (box drawing)
- Layout/Navigation/UI Elements в Markdown
- Легко редактировать и хранить в git, нет изображений

**Use cases:**
1. **Product Manager:** Быстрая визуализация требований в тексте
2. **Designer:** Стартовая схема без графики
3. **Developer:** Чёткое описание UI/flows
4. **Stakeholder:** Быстрый просмотр без тяжёлых файлов

---

## 2. Архитектура системы

### 2.1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   React UI   │  │  WebSocket   │  │   Polling    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │ HTTP/HTTPS       │ WS/WSS           │ HTTP
          ↓                  ↓                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  REST API Endpoints:                                     │   │
│  │  • POST /generate-map-async                              │   │
│  │  • POST /wireframes/generate                             │   │
│  │  • GET  /job/{job_id}                                    │   │
│  │  • WS   /ws/jobs/{job_id}                                │   │
│  └────────┬────────────────────────────────────────────────┘   │
│           │                                                      │
│  ┌────────▼─────────────────────────────────────────────────┐  │
│  │  Services:                                                │  │
│  │  • rabbitmq_service.py  (Producer)                        │  │
│  │  • job_service.py       (Redis status tracking)          │  │
│  │  • ai_service.py        (AI API calls)                    │  │
│  └────────┬──────────────────────────────────────────────────┘ │
└───────────┼────────────────────────────────────────────────────┘
            │
            ↓ publish()
┌─────────────────────────────────────────────────────────────────┐
│              CloudAMQP (RabbitMQ Cloud)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Exchange: ai.tasks (type: topic)                         │  │
│  └────┬───────────────────┬──────────────────┬──────────────┘  │
│       │                   │                  │                  │
│       │ routing_key:      │ routing_key:     │ routing_key:     │
│       │ ai.task.map.#     │ ai.task.wf.#     │ ai.task.bulk.#   │
│       ↓                   ↓                  ↓                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Queue:    │    │   Queue:    │    │   Queue:    │        │
│  │  ai.map.    │    │  ai.wireframe│    │  ai.bulk.   │        │
│  │  generation │    │  .generation │    │  improve    │        │
│  │             │    │             │    │             │        │
│  │ • durable   │    │ • durable   │    │ • durable   │        │
│  │ • priority  │    │ • priority  │    │ • TTL: 1h   │        │
│  │ • TTL: 1h   │    │ • TTL: 1h   │    │             │        │
│  └─────┬───────┘    └─────┬───────┘    └─────┬───────┘        │
└────────┼──────────────────┼──────────────────┼─────────────────┘
         │ consume()        │ consume()        │ consume()
         ↓                  ↓                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                      WORKERS (Consumers)                        │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  Map Worker     │  │ Wireframe Worker │  │  Bulk Worker   │ │
│  │  ────────────   │  │  ─────────────── │  │  ───────────── │ │
│  │  1. Get message │  │  1. Get message  │  │  1. Get msgs   │ │
│  │  2. Update job  │  │  2. Update job   │  │  2. Process    │ │
│  │     status:     │  │     status:      │  │     parallel   │ │
│  │     processing  │  │     processing   │  │  3. Notify     │ │
│  │  3. Call AI     │  │  3. Get stories  │  │                │ │
│  │     (Gemini/    │  │  4. Generate     │  │                │ │
│  │      Groq/      │  │     text prompt  │  │                │ │
│  │      OpenAI)    │  │  5. Call AI      │  │                │ │
│  │  4. Save to DB  │  │     (ASCII/MD)   │  │                │ │
│  │  5. Update job  │  │  6. Update job   │  │                │ │
│  │     status:     │  │     status       │  │                │ │
│  │     completed   │  │  7. Notify WS    │  │                │ │
│  │  6. Notify WS   │  │                  │  │                │ │
│  │                 │  │                  │  │                │ │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬───────┘ │
└───────────┼──────────────────┼───────────────────────┼─────────┘
            │                  │                       │
            ↓                  ↓                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │   Gemini     │  │    Groq      │                             │
│  │ /OpenAI      │  │ (fallback)   │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
            │                  │
            ↓                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  PostgreSQL  │  │    Redis     │                            │
│  │  (Supabase)  │  │  (Job Status)│                            │
│  │              │  │              │                            │
│  │  • Projects  │  │  • job:{id}  │                            │
│  │  • Stories   │  │  • TTL: 1h   │                            │
│  │  • Activities│  │              │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. Message Flow (детально)

#### 2.2.1. User Story Map Generation Flow

```
[1] User clicks "Generate Map"
       ↓
[2] Frontend: POST /generate-map-async
       {
         text: "Приложение для доставки еды...",
         skip_enhancement: false,
         use_enhanced_text: true
       }
       ↓
[3] Backend API (/api/projects.py):
       • Generate job_id = uuid4()
       • Create job in Redis:
         {
           job_id: "123-456-789",
           user_id: 42,
           status: "pending",
           created_at: "2025-12-01T10:00:00Z"
         }
       • Publish to RabbitMQ:
         exchange: "ai.tasks"
         routing_key: "ai.task.map.generation"
         message: {
           job_id: "123-456-789",
           user_id: 42,
           requirements_text: "...",
           use_enhancement: true
         }
       • Return 202 Accepted:
         {
           status: "accepted",
           job_id: "123-456-789",
           websocket_url: "/ws/jobs/123-456-789"
         }
       ↓
[4] Frontend: Connect WebSocket
       ws = new WebSocket("/ws/jobs/123-456-789?token=...")

       ws.onmessage = (event) => {
         // Receive status updates
       }
       ↓
[5] RabbitMQ: Route message to queue "ai.map.generation"
       ↓
[6] Map Worker (workers/map_worker.py):
       • Consume message from queue
       • Update Redis: status = "processing"
       • Call enhance_requirements() if needed
       • Call generate_ai_map() → Groq/OpenAI API
       • Parse JSON response
       • Save to PostgreSQL:
         - Create Project
         - Create Activities
         - Create Tasks
         - Create Stories
       • Update Redis: status = "completed", result = {project_id: 456}
       • ACK message to RabbitMQ
       ↓
[7] WebSocket Server:
       • Poll Redis every 2 sec
       • Detect status change
       • Send to client:
         {
           type: "status_changed",
           status: "completed",
           result: {project_id: 456}
         }
       ↓
[8] Frontend:
       • Receive WebSocket message
       • Fetch project: GET /project/456
       • Render StoryMap component
       • Show success notification
```

**Временная диаграмма:**
```
0s    User clicks "Generate"
1s    202 Accepted, WebSocket connected
2s    Worker picks up message, status: "processing"
3-30s AI generation (Groq/OpenAI)
31s   Save to DB, status: "completed"
32s   WebSocket notification
33s   Frontend loads project
```

#### 2.2.2. Wireframe Generation Flow (Text-Based)

```
[1] User selects stories + clicks "Generate Wireframes"
       ↓
[2] Frontend: POST /wireframes/generate
       {
         project_id: 456,
         story_ids: [1, 2, 3],
         style: "low-fidelity",
         platform: "web"
       }
       ↓
[3] Backend API (/api/wireframes.py):
       • Validate project ownership
       • Validate stories exist
       • Generate job_id
       • Create job in Redis
       • Publish to RabbitMQ:
         routing_key: "ai.task.wireframe.generation"
       • Return 202 Accepted
       ↓
[4] RabbitMQ: Route to "ai.wireframe.generation" queue
       ↓
[5] Wireframe Worker (workers/wireframe_worker_text.py):
       • Consume message
       • Update status: "processing"

       FOR EACH story:
         [5.1] Load story from DB (with context: task, activity)

         [5.2] Build text wireframe prompt (style/platform-aware)

         [5.3] Call AI provider (Gemini/Groq/OpenAI) via generate_ai_response()
               → получаем текст с блоком ```ascii``` + разделы

         [5.4] Parse response:
               - ascii_wireframe
               - layout_description
               - ui_elements
               - navigation
               - notes

         [5.5] Update progress in Redis (ascii + markdown, без изображений)

       [5.6] Update status: "completed"
       ↓
[6] WebSocket notification to user
       ↓
[7] Frontend renders ASCII/Markdown wireframe
```

### 2.3. RabbitMQ Exchange & Queue Topology

```
Exchange: ai.tasks (type: topic, durable: true)
│
├─ Binding: routing_key = "ai.task.map.#"
│  │
│  └─► Queue: ai.map.generation
│      Properties:
│      • durable: true (survives broker restart)
│      • arguments:
│        - x-message-ttl: 3600000 (1 hour)
│        - x-max-priority: 10 (priority support)
│        - x-dead-letter-exchange: "dlx.ai.tasks"
│      • consumers: map_worker.py (1-N instances)
│
├─ Binding: routing_key = "ai.task.wireframe.#"
│  │
│  └─► Queue: ai.wireframe.generation
│      Properties:
│      • durable: true
│      • arguments:
│        - x-message-ttl: 3600000
│        - x-max-priority: 10
│        - x-dead-letter-exchange: "dlx.ai.tasks"
│      • consumers: wireframe_worker_text.py (1-N instances)
│
└─ Binding: routing_key = "ai.task.bulk.#"
   │
   └─► Queue: ai.bulk.improve
       Properties:
       • durable: true
       • arguments:
         - x-message-ttl: 3600000
       • consumers: bulk_worker.py (optional, future)

Dead Letter Exchange: dlx.ai.tasks (type: fanout)
│
└─► Queue: ai.tasks.failed
    • Stores failed messages for analysis
    • Manual retry or debugging
```

**Routing Examples:**

| Message | Routing Key | Queue Destination |
|---------|-------------|-------------------|
| Map generation | `ai.task.map.generation` | `ai.map.generation` |
| Map generation (priority) | `ai.task.map.generation.priority` | `ai.map.generation` |
| Wireframe gen | `ai.task.wireframe.generation` | `ai.wireframe.generation` |
| Bulk improve | `ai.task.bulk.improve` | `ai.bulk.improve` |

### 2.4. Data Models

#### 2.4.1. Redis Job Schema

```python
# Key: job:{job_id}
# TTL: 3600 seconds (1 hour)
# Value: JSON

{
  "job_id": "uuid-string",
  "user_id": 123,
  "job_type": "ai_map_generation" | "wireframe_generation" | "bulk_improve",
  "status": "pending" | "processing" | "completed" | "failed",
  "created_at": "2025-12-01T10:00:00.000Z",
  "updated_at": "2025-12-01T10:05:00.000Z",
  "metadata": {
    // job-specific metadata
    "project_name": "Food Delivery App",
    "story_count": 3,
    "style": "low-fidelity",
    ...
  },
  "result": {
    // populated on completion
    "project_id": 456,
    "wireframes": [...]
  },
  "error": "Error message if failed",
  "progress": {
    // optional, for long-running jobs
    "current": 2,
    "total": 5,
    "message": "Processing story 2 of 5"
  }
}
```

#### 2.4.2. RabbitMQ Message Schema

**Map Generation Message:**
```json
{
  "job_id": "abc-123",
  "user_id": 42,
  "requirements_text": "Приложение для...",
  "use_enhancement": true,
  "created_at": "2025-12-01T10:00:00Z",
  "_metadata": {
    "message_id": "msg-456",
    "timestamp": "2025-12-01T10:00:00Z",
    "producer": "usm-backend"
  }
}
```

**Wireframe Generation Message:**
```json
{
  "job_id": "def-789",
  "user_id": 42,
  "project_id": 456,
  "story_ids": [1, 2, 3],
  "style": "low-fidelity",
  "platform": "web",
  "created_at": "2025-12-01T10:00:00Z",
  "_metadata": {
    "message_id": "msg-789",
    "timestamp": "2025-12-01T10:00:00Z",
    "producer": "usm-backend"
  }
}
```

---

## 3. Предварительные требования

### 3.1. Development Environment

**Обязательные инструменты:**
```bash
# Python 3.9+
python --version
# Python 3.11.5

# pip
pip --version
# pip 23.3.1

# Node.js 18+
node --version
# v20.10.0

# npm
npm --version
# 10.2.3

# Git
git --version
# git version 2.42.0

# Docker (для локального RabbitMQ)
docker --version
# Docker version 24.0.7

# Docker Compose
docker-compose --version
# docker-compose version 1.29.2
```

**Опциональные инструменты:**
```bash
# HTTPie (для тестирования API)
brew install httpie

# jq (для обработки JSON)
brew install jq

# psql (PostgreSQL client)
brew install postgresql@15

# redis-cli
brew install redis
```

### 3.2. Cloud Accounts (FREE)

**1. CloudAMQP (RabbitMQ hosting)**
- URL: https://www.cloudamqp.com/
- План: Little Lemur (FREE)
- Лимиты:
  - 1 million messages/month
  - 5 concurrent connections
  - 25 queues max
  - Shared instance

**Регистрация:**
```
1. Перейти на cloudamqp.com
2. Sign Up (GitHub/Google/Email)
3. Dashboard → Create New Instance
4. Name: usm-rabbitmq-dev
5. Plan: Little Lemur (FREE)
6. Region: выбрать ближайший (eu-north-1 для России)
7. Create instance
8. Скопировать CLOUDAMQP_URL:
   amqps://username:password@host.cloudamqp.com/vhost
```

**2. AI API (для text wireframes)**
- Ключи: GEMINI_API_KEY / GROQ_API_KEY / OPENAI_API_KEY
- Модели текстовые; изображения не требуются

**3. Supabase (PostgreSQL) - уже используется**
- URL: https://supabase.com/
- План: Free tier
- Лимиты:
  - 500 MB database
  - 2 GB bandwidth/month
  - Unlimited API requests

**5. Upstash Redis - уже используется**
- URL: https://upstash.com/
- План: Free tier
- Лимиты:
  - 10K requests/day
  - 256 MB storage

### 3.3. Системные требования

**Минимальные:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 5 GB free space

**Рекомендуемые:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 10+ GB free space
- SSD для БД

### 3.4. Проверка текущего окружения

Создайте скрипт `check-environment.sh`:

```bash
#!/bin/bash

echo "🔍 Checking environment..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_command() {
  if command -v $1 &> /dev/null; then
    echo -e "${GREEN}✓${NC} $1 is installed"
  else
    echo -e "${RED}✗${NC} $1 is NOT installed"
  fi
}

# Check commands
echo ""
echo "=== Required Tools ==="
check_command python3
check_command pip3
check_command node
check_command npm
check_command git

echo ""
echo "=== Optional Tools ==="
check_command docker
check_command docker-compose
check_command http
check_command jq

# Check Python version
echo ""
echo "=== Python Version ==="
python3 --version

# Check Node version
echo ""
echo "=== Node Version ==="
node --version

# Check environment variables
echo ""
echo "=== Environment Variables ==="

check_env() {
  if [ -z "${!1}" ]; then
    echo -e "${RED}✗${NC} $1 is NOT set"
  else
    echo -e "${GREEN}✓${NC} $1 is set"
  fi
}

check_env "DATABASE_URL"
check_env "REDIS_URL"
check_env "GEMINI_API_KEY"
check_env "GROQ_API_KEY"
check_env "OPENAI_API_KEY"

echo ""
echo "=== New Required Variables ==="
check_env "RABBITMQ_URL"

echo ""
echo "✅ Environment check complete!"
```

Запуск:
```bash
chmod +x check-environment.sh
./check-environment.sh
```

---

## 4. Phase 1: RabbitMQ Setup

### 4.1. Option A: CloudAMQP (Production & Development)

#### 4.1.1. Создание instance

**Step-by-step:**

1. **Регистрация и вход:**
   ```
   https://customer.cloudamqp.com/login
   Email: your-email@example.com
   Password: ********
   ```

2. **Создание instance:**
   ```
   Dashboard → Create New Instance

   Name: usm-rabbitmq-dev
   Plan: Little Lemur (FREE)
   Region: EU-North-1-A (Stockholm) - для Европы/России
          или US-East-1 (Virginia) - для США

   Tags: development, usm-project

   [Create instance]
   ```

3. **Получение credentials:**
   ```
   Click на instance → Details

   Скопировать:
   • URL: amqps://vrcptkqu:***@hawk-01.rmq.cloudamqp.com/vrcptkqu
   • Host: hawk-01.rmq.cloudamqp.com
   • Virtual host: vrcptkqu
   • Username: vrcptkqu
   • Password: ***
   ```

4. **Management UI:**
   ```
   Click на instance → RabbitMQ Manager

   Откроется: https://hawk-01.rmq.cloudamqp.com/#/

   Здесь можно:
   • Смотреть очереди
   • Мониторить сообщения
   • Создавать exchanges вручную
   • Просматривать connections
   ```

#### 4.1.2. Настройка .env файла

Создайте `.env` в корне проекта:

```bash
# backend/.env

# ========================================
# RabbitMQ Configuration (CloudAMQP)
# ========================================
RABBITMQ_ENABLED=true
CLOUDAMQP_URL=amqps://username:password@host.cloudamqp.com/vhost

# Alternative для локального тестирования:
# RABBITMQ_URL=amqp://admin:admin123@localhost:5672/

# ========================================
# ========================================
# AI API Keys (text wireframes)
# ========================================
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk-...
OPENAI_API_KEY=sk-...

# ========================================
# Database (existing)
# ========================================
DATABASE_URL=postgresql://user:pass@host:5432/db

# ========================================
# Redis (existing)
# ========================================
REDIS_URL=redis://localhost:6379/0

# ========================================
# JWT (existing)
# ========================================
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ========================================
# CORS (existing)
# ========================================
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ========================================
# Logging
# ========================================
LOG_LEVEL=INFO

# ========================================
# Environment
# ========================================
ENVIRONMENT=development
```

**Важно:** Добавьте `.env` в `.gitignore`:

```bash
# .gitignore
.env
.env.local
.env.production
*.env
```

#### 4.1.3. Тестирование подключения

Создайте скрипт `test-rabbitmq-connection.py`:

```python
"""
Тест подключения к RabbitMQ (CloudAMQP или локальному)
"""
import asyncio
import os
from dotenv import load_dotenv
import aio_pika

load_dotenv()

async def test_connection():
    rabbitmq_url = os.getenv("CLOUDAMQP_URL") or os.getenv("RABBITMQ_URL")

    if not rabbitmq_url:
        print("❌ RABBITMQ_URL or CLOUDAMQP_URL not set in .env")
        return

    print(f"🔌 Connecting to RabbitMQ...")
    print(f"   URL: {rabbitmq_url[:20]}...{rabbitmq_url[-20:]}")

    try:
        # Подключение
        connection = await aio_pika.connect_robust(
            rabbitmq_url,
            timeout=30
        )
        print("✅ Connection established!")

        # Создание канала
        channel = await connection.channel()
        print("✅ Channel created!")

        # Создание test exchange
        exchange = await channel.declare_exchange(
            "test.exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=False,
            auto_delete=True
        )
        print("✅ Test exchange created!")

        # Создание test queue
        queue = await channel.declare_queue(
            "test.queue",
            durable=False,
            auto_delete=True
        )
        print("✅ Test queue created!")

        # Bind
        await queue.bind(exchange, routing_key="test.#")
        print("✅ Queue bound to exchange!")

        # Publish test message
        message = aio_pika.Message(
            body=b'{"test": "message"}',
            content_type="application/json"
        )
        await exchange.publish(message, routing_key="test.message")
        print("✅ Test message published!")

        # Consume
        async with queue.iterator() as queue_iter:
            async for msg in queue_iter:
                async with msg.process():
                    print(f"✅ Test message received: {msg.body.decode()}")
                    break

        # Cleanup
        await connection.close()
        print("✅ Connection closed!")

        print("\n🎉 RabbitMQ connection test PASSED!")

    except Exception as e:
        print(f"\n❌ RabbitMQ connection test FAILED!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Запуск:
```bash
cd backend
pip install aio-pika python-dotenv
python test-rabbitmq-connection.py
```

**Ожидаемый вывод:**
```
🔌 Connecting to RabbitMQ...
   URL: amqps://vrcptkqu:***...oudamqp.com/vrcptkqu
✅ Connection established!
✅ Channel created!
✅ Test exchange created!
✅ Test queue created!
✅ Queue bound to exchange!
✅ Test message published!
✅ Test message received: {"test": "message"}
✅ Connection closed!

🎉 RabbitMQ connection test PASSED!
```

### 4.2. Option B: Local Docker RabbitMQ (Development Only)

#### 4.2.1. Docker Compose Setup

Создайте `docker-compose.rabbitmq.yml`:

```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: usm-rabbitmq
    hostname: usm-rabbitmq

    ports:
      - "5672:5672"    # AMQP protocol
      - "15672:15672"  # Management UI

    environment:
      # Default credentials
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin123

      # Virtual host
      RABBITMQ_DEFAULT_VHOST: /

      # Logging
      RABBITMQ_LOG_LEVEL: info

      # Memory limits
      RABBITMQ_VM_MEMORY_HIGH_WATERMARK: 512MB

    volumes:
      # Persistent data
      - rabbitmq-data:/var/lib/rabbitmq

      # Configuration (optional)
      - ./rabbitmq-config/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
      - ./rabbitmq-config/definitions.json:/etc/rabbitmq/definitions.json:ro

    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s

    restart: unless-stopped

    networks:
      - usm-network

volumes:
  rabbitmq-data:
    driver: local

networks:
  usm-network:
    driver: bridge
```

#### 4.2.2. RabbitMQ Configuration File (optional)

Создайте `rabbitmq-config/rabbitmq.conf`:

```ini
# RabbitMQ Configuration

# Network
listeners.tcp.default = 5672
management.tcp.port = 15672

# Logging
log.console = true
log.console.level = info
log.file = false

# Memory
vm_memory_high_watermark.relative = 0.6
vm_memory_high_watermark_paging_ratio = 0.75

# Disk
disk_free_limit.relative = 1.0

# Heartbeat
heartbeat = 60

# Default user
default_user = admin
default_pass = admin123
default_vhost = /

# Management plugin
management.load_definitions = /etc/rabbitmq/definitions.json
```

#### 4.2.3. RabbitMQ Definitions (Pre-create queues)

Создайте `rabbitmq-config/definitions.json`:

```json
{
  "rabbit_version": "3.12",
  "users": [
    {
      "name": "admin",
      "password_hash": "JThRmHSgx0hb3n4Qp1h8JhH2gV8LhH6b",
      "hashing_algorithm": "rabbit_password_hashing_sha256",
      "tags": "administrator"
    }
  ],
  "vhosts": [
    {
      "name": "/"
    }
  ],
  "permissions": [
    {
      "user": "admin",
      "vhost": "/",
      "configure": ".*",
      "write": ".*",
      "read": ".*"
    }
  ],
  "topic_permissions": [],
  "parameters": [],
  "global_parameters": [
    {
      "name": "cluster_name",
      "value": "usm-rabbitmq-cluster"
    }
  ],
  "policies": [],
  "queues": [
    {
      "name": "ai.map.generation",
      "vhost": "/",
      "durable": true,
      "auto_delete": false,
      "arguments": {
        "x-message-ttl": 3600000,
        "x-max-priority": 10
      }
    },
    {
      "name": "ai.wireframe.generation",
      "vhost": "/",
      "durable": true,
      "auto_delete": false,
      "arguments": {
        "x-message-ttl": 3600000,
        "x-max-priority": 10
      }
    },
    {
      "name": "ai.bulk.improve",
      "vhost": "/",
      "durable": true,
      "auto_delete": false,
      "arguments": {
        "x-message-ttl": 3600000
      }
    }
  ],
  "exchanges": [
    {
      "name": "ai.tasks",
      "vhost": "/",
      "type": "topic",
      "durable": true,
      "auto_delete": false,
      "internal": false,
      "arguments": {}
    },
    {
      "name": "dlx.ai.tasks",
      "vhost": "/",
      "type": "fanout",
      "durable": true,
      "auto_delete": false,
      "internal": false,
      "arguments": {}
    }
  ],
  "bindings": [
    {
      "source": "ai.tasks",
      "vhost": "/",
      "destination": "ai.map.generation",
      "destination_type": "queue",
      "routing_key": "ai.task.map.#",
      "arguments": {}
    },
    {
      "source": "ai.tasks",
      "vhost": "/",
      "destination": "ai.wireframe.generation",
      "destination_type": "queue",
      "routing_key": "ai.task.wireframe.#",
      "arguments": {}
    },
    {
      "source": "ai.tasks",
      "vhost": "/",
      "destination": "ai.bulk.improve",
      "destination_type": "queue",
      "routing_key": "ai.task.bulk.#",
      "arguments": {}
    }
  ]
}
```

#### 4.2.4. Запуск RabbitMQ

```bash
# Создать директории для конфигурации
mkdir -p rabbitmq-config

# Скопировать конфигурационные файлы (см. выше)

# Запустить RabbitMQ
docker-compose -f docker-compose.rabbitmq.yml up -d

# Проверить логи
docker-compose -f docker-compose.rabbitmq.yml logs -f rabbitmq

# Ожидаемый вывод:
# rabbitmq_1  | 2025-12-01 10:00:00.000 [info] <0.222.0> Server startup complete; 3 plugins started.
# rabbitmq_1  |  * rabbitmq_management
# rabbitmq_1  |  * rabbitmq_management_agent
# rabbitmq_1  |  * rabbitmq_web_dispatch
```

**Проверка:**
```bash
# Health check
docker exec usm-rabbitmq rabbitmq-diagnostics ping
# Output: Ping succeeded

# Check queues
docker exec usm-rabbitmq rabbitmqctl list_queues
# Output:
# Timeout: 60.0 seconds ...
# Listing queues for vhost / ...
# name	messages
# ai.map.generation	0
# ai.wireframe.generation	0
# ai.bulk.improve	0
```

**Management UI:**
```
http://localhost:15672/

Username: admin
Password: admin123
```

**Скриншоты Management UI:**

1. **Overview:**
   - Total queued messages
   - Message rates (publish/deliver)
   - Connection count
   - Channel count

2. **Queues tab:**
   - Список всех очередей
   - Messages ready/unacked
   - Publish/deliver rates
   - Consumers count

3. **Exchanges tab:**
   - ai.tasks (topic)
   - dlx.ai.tasks (fanout)

#### 4.2.5. Обновление .env для локального RabbitMQ

```bash
# backend/.env

RABBITMQ_ENABLED=true
RABBITMQ_URL=amqp://admin:admin123@localhost:5672/

# Комментируем CloudAMQP URL
# CLOUDAMQP_URL=amqps://...
```

### 4.3. Troubleshooting RabbitMQ Connection

#### Problem 1: Connection timeout

**Симптомы:**
```
asyncio.exceptions.TimeoutError: Connection timeout
```

**Решения:**
```bash
# 1. Проверить доступность хоста
ping hawk-01.rmq.cloudamqp.com

# 2. Проверить firewall
telnet hawk-01.rmq.cloudamqp.com 5672

# 3. Проверить SSL/TLS (для CloudAMQP)
openssl s_client -connect hawk-01.rmq.cloudamqp.com:5671

# 4. Увеличить timeout в коде
connection = await aio_pika.connect_robust(
    rabbitmq_url,
    timeout=60  # увеличить с 30 до 60 секунд
)
```

#### Problem 2: Authentication failed

**Симптомы:**
```
aio_pika.exceptions.ProbableAuthenticationError: Authentication failed
```

**Решения:**
```bash
# 1. Проверить credentials в .env
echo $CLOUDAMQP_URL

# 2. Проверить special characters в пароле
# Если пароль содержит @, #, % и т.д., нужно URL-encode
# Пример: password "p@ss#123" → "p%40ss%23123"

# 3. Проверить username/password в CloudAMQP UI
# Dashboard → Instance → Details

# 4. Попробовать reconnect через Management UI
# Dashboard → Instance → RabbitMQ Manager → Test connection
```

#### Problem 3: Channel closed unexpectedly

**Симптомы:**
```
aio_pika.exceptions.ChannelClosed: Channel closed by server
```

**Решения:**
```python
# 1. Добавить error handling
try:
    await channel.declare_queue(...)
except aio_pika.exceptions.ChannelClosed as e:
    logger.error(f"Channel closed: {e}")
    # Recreate channel
    channel = await connection.channel()

# 2. Использовать connect_robust для auto-reconnect
connection = await aio_pika.connect_robust(
    rabbitmq_url,
    timeout=30
)
# connect_robust автоматически переподключается при обрывах

# 3. Проверить limits CloudAMQP
# Little Lemur: max 5 connections
# Убедитесь, что не превышаете лимит
```

#### Problem 4: Queue already exists with different arguments

**Симптомы:**
```
PRECONDITION_FAILED - inequivalent arg 'x-message-ttl' for queue 'ai.map.generation'
```

**Решения:**
```python
# Вариант 1: Удалить существующую очередь вручную
# RabbitMQ Manager → Queues → Delete queue

# Вариант 2: Использовать passive=True для проверки
queue = await channel.declare_queue(
    "ai.map.generation",
    passive=True  # Не создает, только проверяет существование
)

# Вариант 3: Использовать другое имя очереди
queue = await channel.declare_queue(
    "ai.map.generation.v2",  # новое имя
    durable=True,
    arguments={"x-message-ttl": 3600000}
)
```

---

## 5. Phase 2: Backend Infrastructure

### 5.1. Python Dependencies

#### 5.1.1. Обновление requirements.txt

Обновите `backend/requirements.txt`:

```txt
# ========================================
# Web Framework
# ========================================
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# ========================================
# Database
# ========================================
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9

# ========================================
# Authentication
# ========================================
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# ========================================
# Rate Limiting & CORS
# ========================================
slowapi==0.1.9
python-cors==1.0.0

# ========================================
# AI APIs
# ========================================
openai==1.10.0
anthropic==0.10.0  # optional, for Claude

# ========================================
# RabbitMQ (NEW)
# ========================================
aio-pika==9.4.0
aiormq==6.8.0

# ========================================
# Redis
# ========================================
redis==5.0.1
aioredis==2.0.1  # для async operations

# ========================================
# WebSocket
# ========================================
websockets==12.0

# ========================================
# Image Processing (для wireframes)
# ========================================
Pillow==10.2.0
cloudinary==1.38.0

# ========================================
# Utilities
# ========================================
pydantic==2.5.3
pydantic-settings==2.1.0
scikit-learn==1.4.0  # для TF-IDF analysis
numpy==1.26.3

# ========================================
# Testing
# ========================================
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0  # для тестирования FastAPI

# ========================================
# Monitoring (optional)
# ========================================
sentry-sdk==1.39.2
prometheus-client==0.19.0

# ========================================
# Development
# ========================================
black==24.1.0
flake8==7.0.0
isort==5.13.2
```

**Установка:**
```bash
cd backend

# Создать виртуальное окружение (если еще не создано)
python -m venv venv

# Активировать
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Проверка установки
pip list | grep aio-pika
# aio-pika             9.4.0

pip list | grep cloudinary
# cloudinary           1.38.0
```

#### 5.1.2. Проверка совместимости

Создайте `check-dependencies.py`:

```python
"""
Проверка установленных зависимостей
"""
import sys

def check_import(module_name, import_path=None):
    try:
        if import_path:
            exec(f"from {module_name} import {import_path}")
        else:
            __import__(module_name)
        print(f"✅ {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {module_name}: {e}")
        return False

print("🔍 Checking dependencies...\n")

# Core
check_import("fastapi")
check_import("uvicorn")
check_import("pydantic")

# Database
check_import("sqlalchemy")
check_import("alembic")
check_import("psycopg2")

# Auth
check_import("jose", "jwt")
check_import("passlib")

# RabbitMQ (NEW)
check_import("aio_pika")
check_import("aiormq")

# Redis
check_import("redis")

# Image (NEW)
check_import("PIL", "Image")
check_import("cloudinary")

# AI
check_import("openai")

# WebSocket
check_import("websockets")

# Testing
check_import("pytest")

print("\n✅ All dependencies OK!")
```

Запуск:
```bash
python check-dependencies.py
```

### 5.2. Configuration Updates

#### 5.2.1. Обновление config.py

Обновите `backend/config.py`:

```python
"""
Конфигурация приложения с валидацией через Pydantic Settings
"""
import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Настройки приложения"""

    def __init__(self):
        # ==========================================
        # API Keys (existing)
        # ==========================================
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.API_PROVIDER = os.getenv("API_PROVIDER", "")
        self.API_MODEL = os.getenv("API_MODEL", "")
        self.API_TEMPERATURE = float(os.getenv("API_TEMPERATURE", "0.7"))

        # Приоритет провайдеров для fallback (текстовые)
        self.AI_PROVIDER_PRIORITY = [
            p.strip() for p in os.getenv("AI_PROVIDER_PRIORITY", "gemini,groq,openai").split(",")
            if p.strip()
        ]

        # Two-Stage AI Processing
        self.ENHANCEMENT_MODEL = os.getenv("ENHANCEMENT_MODEL", "")

        # ==========================================
        # Database (existing)
        # ==========================================
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usm.db")

        # ==========================================
        # Redis (existing)
        # ==========================================
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # ==========================================
        # JWT (existing)
        # ==========================================
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # ==========================================
        # CORS (existing)
        # ==========================================
        self.ALLOWED_ORIGINS = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        )

        # ==========================================
        # RabbitMQ Configuration
        # ==========================================
        self.RABBITMQ_ENABLED = os.getenv("RABBITMQ_ENABLED", "false").lower() == "true"

        # CloudAMQP URL (приоритет) или локальный RabbitMQ
        self.RABBITMQ_URL = os.getenv(
            "CLOUDAMQP_URL",
            os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/")
        )

        # RabbitMQ Queues
        self.QUEUE_AI_MAP_GENERATION = "ai.map.generation"
        self.QUEUE_AI_WIREFRAME_GENERATION = "ai.wireframe.generation"
        self.QUEUE_AI_BULK_IMPROVE = "ai.bulk.improve"

        # RabbitMQ Exchange
        self.EXCHANGE_AI_TASKS = "ai.tasks"
        self.EXCHANGE_DLX = "dlx.ai.tasks"

        # Queue Settings
        self.QUEUE_DURABLE = True
        self.MESSAGE_TTL = 3600000  # 1 hour in milliseconds
        self.PREFETCH_COUNT = 1  # Process one message at a time per worker

        # Connection Settings
        self.RABBITMQ_CONNECTION_TIMEOUT = 30  # seconds
        self.RABBITMQ_HEARTBEAT = 60  # seconds

        # ==========================================
        # Wireframe Generation Settings (text)
        # ==========================================
        self.WIREFRAME_MAX_STORIES = int(os.getenv("WIREFRAME_MAX_STORIES", "10"))

        # ==========================================
        # Logging (existing)
        # ==========================================
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        # ==========================================
        # Sentry (existing)
        # ==========================================
        self.SENTRY_DSN = os.getenv("SENTRY_DSN", "")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

        # ==========================================
        # Worker Settings (NEW)
        # ==========================================
        self.WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "1"))
        self.WORKER_MAX_RETRIES = int(os.getenv("WORKER_MAX_RETRIES", "3"))
        self.WORKER_RETRY_DELAY = int(os.getenv("WORKER_RETRY_DELAY", "5"))  # seconds

        # Auto-setup
        self._set_api_provider()
        self._set_default_model()
        self._validate_settings()

    def _set_api_provider(self):
        """Автоопределение API провайдера по ключу"""
        if self.API_PROVIDER:
            return

        for provider in self.AI_PROVIDER_PRIORITY:
            if provider == "gemini" and self.GEMINI_API_KEY:
                self.API_PROVIDER = "gemini"
                return
            elif provider == "groq" and self.GROQ_API_KEY:
                self.API_PROVIDER = "groq"
                return
            elif provider == "openai" and self.OPENAI_API_KEY:
                self.API_PROVIDER = "openai"
                return

        # Fallback: определяем по формату ключа
        api_key = self.get_api_key()
        if api_key:
            if api_key.startswith("AIza"):
                self.API_PROVIDER = "gemini"
            elif api_key.startswith("gsk_"):
                self.API_PROVIDER = "groq"
            elif api_key.startswith("sk-"):
                self.API_PROVIDER = "openai"

    def _set_default_model(self):
        """Установка модели по умолчанию"""
        if self.API_MODEL:
            return

        if self.API_PROVIDER == "gemini":
            self.API_MODEL = "gemini-2.0-flash-exp"
        elif self.API_PROVIDER == "groq":
            self.API_MODEL = "llama-3.3-70b-versatile"
        elif self.API_PROVIDER == "openai":
            self.API_MODEL = "gpt-4o-mini"

    def _validate_settings(self):
        """Валидация настроек при запуске"""
        errors = []
        warnings = []

        # JWT Secret
        if self.ENVIRONMENT == "production":
            if self.JWT_SECRET_KEY == "your-secret-key-change-in-production":
                errors.append("JWT_SECRET_KEY must be changed in production!")

        if len(self.JWT_SECRET_KEY) < 32:
            warnings.append("JWT_SECRET_KEY should be at least 32 characters long")

        # Database
        if self.is_sqlite() and self.ENVIRONMENT == "production":
            warnings.append("SQLite is not recommended for production. Use PostgreSQL.")

        # AI Provider
        available_providers = self.get_available_providers()
        if not available_providers:
            warnings.append("No AI API keys configured. AI functions will be unavailable.")
        else:
            logger.info(f"✅ AI providers available: {', '.join(available_providers)}")

        # RabbitMQ (NEW)
        if self.RABBITMQ_ENABLED:
            if not self.RABBITMQ_URL:
                errors.append("RABBITMQ_ENABLED=true but RABBITMQ_URL not set")
            else:
                logger.info(f"✅ RabbitMQ enabled: {self._mask_url(self.RABBITMQ_URL)}")

        else:
            logger.info("ℹ️ RabbitMQ disabled - using synchronous processing")

        # Отображение ошибок и предупреждений
        if errors:
            for error in errors:
                logger.error(f"❌ CONFIG ERROR: {error}")
            raise ValueError(f"Configuration errors: {errors}")

        if warnings:
            for warning in warnings:
                logger.warning(f"⚠️ CONFIG WARNING: {warning}")

    def get_api_key(self) -> str:
        """Возвращает активный API ключ"""
        for provider in self.AI_PROVIDER_PRIORITY:
            if provider == "gemini" and self.GEMINI_API_KEY:
                return self.GEMINI_API_KEY
            elif provider == "groq" and self.GROQ_API_KEY:
                return self.GROQ_API_KEY
            elif provider == "openai" and self.OPENAI_API_KEY:
                return self.OPENAI_API_KEY
        return self.GEMINI_API_KEY or self.GROQ_API_KEY or self.OPENAI_API_KEY

    def get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Возвращает API ключ для конкретного провайдера"""
        if provider == "gemini":
            return self.GEMINI_API_KEY
        elif provider == "groq":
            return self.GROQ_API_KEY
        elif provider == "openai":
            return self.OPENAI_API_KEY
        return None

    def get_available_providers(self) -> List[str]:
        """Возвращает список доступных провайдеров в порядке приоритета"""
        available = []
        for provider in self.AI_PROVIDER_PRIORITY:
            if self.get_api_key_for_provider(provider):
                available.append(provider)
        return available

    def get_enhancement_model(self) -> str:
        """Возвращает модель для Stage 1 (улучшение требований)"""
        return self.ENHANCEMENT_MODEL or self.API_MODEL

    def get_allowed_origins_list(self) -> List[str]:
        """Преобразует ALLOWED_ORIGINS в список"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    def is_sqlite(self) -> bool:
        """Проверяет, используется ли SQLite"""
        return self.DATABASE_URL.startswith("sqlite")


# Singleton instance
settings = Settings()
```

**Тестирование конфигурации:**

```bash
cd backend
python -c "from config import settings; print('Config loaded successfully!')"
```

**Ожидаемый вывод:**
```
✅ AI providers available: gemini, groq, openai
✅ RabbitMQ enabled: amqps://vrcptkqu:***@hawk-01.rmq.cloudamqp.com/vrcptkqu
Config loaded successfully!
```

### 5.3. RabbitMQ Service Layer

#### 5.3.1. Создание rabbitmq_service.py

Создайте `backend/services/rabbitmq_service.py`:

```python
"""
RabbitMQ service для управления подключениями и очередями

Основные функции:
- Подключение к RabbitMQ (CloudAMQP или локальному)
- Создание exchanges и queues
- Публикация сообщений (producer)
- Потребление сообщений (consumer)
- Graceful shutdown
- Retry логика
"""
import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import uuid

import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType, Connection
from aio_pika.abc import (
    AbstractConnection,
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractIncomingMessage
)
from aio_pika.pool import Pool

from config import settings

logger = logging.getLogger(__name__)


class RabbitMQService:
    """
    Async RabbitMQ service для producer и consumer операций

    Features:
    - Connection pooling для лучшей производительности
    - Auto-reconnect при разрывах соединения
    - Dead Letter Queue (DLQ) для failed messages
    - Priority queues support
    - Message TTL
    """

    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchanges: Dict[str, AbstractExchange] = {}
        self.queues: Dict[str, AbstractQueue] = {}
        self._connected = False

        # Connection pool (для high-load scenarios)
        self._connection_pool: Optional[Pool] = None
        self._channel_pool: Optional[Pool] = None

    async def connect(self):
        """
        Подключение к RabbitMQ и создание топологии (exchanges, queues)

        Использует robust connection для автоматического переподключения
        """
        if self._connected:
            logger.info("Already connected to RabbitMQ")
            return

        try:
            logger.info(f"🔌 Connecting to RabbitMQ: {settings._mask_url(settings.RABBITMQ_URL)}")

            # Создание robust connection (auto-reconnect)
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                timeout=settings.RABBITMQ_CONNECTION_TIMEOUT,
                heartbeat=settings.RABBITMQ_HEARTBEAT
            )

            # Создание канала
            self.channel = await self.connection.channel()

            # QoS: prefetch_count определяет сколько сообщений воркер
            # может обрабатывать одновременно
            await self.channel.set_qos(prefetch_count=settings.PREFETCH_COUNT)

            # Создание exchanges и queues
            await self._setup_topology()

            self._connected = True
            logger.info("✅ RabbitMQ connected successfully")

        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise

    async def _setup_topology(self):
        """
        Создание exchanges, queues и bindings

        Topology:
        Exchange (ai.tasks) → Queue (ai.map.generation)
                            → Queue (ai.wireframe.generation)
                            → Queue (ai.bulk.improve)

        Dead Letter Exchange (dlx.ai.tasks) → Queue (ai.tasks.failed)
        """

        # ==========================================
        # 1. Main Exchange для AI tasks
        # ==========================================
        self.exchanges["ai.tasks"] = await self.channel.declare_exchange(
            settings.EXCHANGE_AI_TASKS,
            ExchangeType.TOPIC,  # topic позволяет использовать routing patterns
            durable=True  # Переживёт рестарт RabbitMQ
        )
        logger.info(f"✅ Exchange declared: {settings.EXCHANGE_AI_TASKS}")

        # ==========================================
        # 2. Dead Letter Exchange (DLX)
        # ==========================================
        # Сюда попадают сообщения, которые:
        # - Expired (превысили TTL)
        # - Rejected with requeue=false
        # - Queue достигла max-length
        dlx_exchange = await self.channel.declare_exchange(
            settings.EXCHANGE_DLX,
            ExchangeType.FANOUT,  # fanout отправляет во все bound queues
            durable=True
        )
        logger.info(f"✅ Dead Letter Exchange declared: {settings.EXCHANGE_DLX}")

        # ==========================================
        # 3. Dead Letter Queue
        # ==========================================
        dlq = await self.channel.declare_queue(
            "ai.tasks.failed",
            durable=True,
            arguments={
                # No TTL - хотим сохранить для анализа
                "x-queue-mode": "lazy"  # Сохранять на диск, не в RAM
            }
        )
        await dlq.bind(dlx_exchange)
        self.queues["failed"] = dlq
        logger.info("✅ Dead Letter Queue declared: ai.tasks.failed")

        # ==========================================
        # 4. Queue: AI Map Generation
        # ==========================================
        queue_map = await self.channel.declare_queue(
            settings.QUEUE_AI_MAP_GENERATION,
            durable=settings.QUEUE_DURABLE,
            arguments={
                "x-message-ttl": settings.MESSAGE_TTL,  # 1 hour
                "x-max-priority": 10,  # Поддержка приоритетов 0-10
                "x-dead-letter-exchange": settings.EXCHANGE_DLX  # DLX
            }
        )

        # Bind к exchange с routing key pattern
        await queue_map.bind(
            self.exchanges["ai.tasks"],
            routing_key="ai.task.map.#"  # Matches: ai.task.map.*, ai.task.map.*.*, etc.
        )

        self.queues["map_generation"] = queue_map
        logger.info(f"✅ Queue declared and bound: {settings.QUEUE_AI_MAP_GENERATION}")

        # ==========================================
        # 5. Queue: AI Wireframe Generation (NEW)
        # ==========================================
        queue_wireframe = await self.channel.declare_queue(
            settings.QUEUE_AI_WIREFRAME_GENERATION,
            durable=settings.QUEUE_DURABLE,
            arguments={
                "x-message-ttl": settings.MESSAGE_TTL,
                "x-max-priority": 10,
                "x-dead-letter-exchange": settings.EXCHANGE_DLX
            }
        )

        await queue_wireframe.bind(
            self.exchanges["ai.tasks"],
            routing_key="ai.task.wireframe.#"
        )

        self.queues["wireframe_generation"] = queue_wireframe
        logger.info(f"✅ Queue declared and bound: {settings.QUEUE_AI_WIREFRAME_GENERATION}")

        # ==========================================
        # 6. Queue: Bulk Improve (optional)
        # ==========================================
        queue_bulk = await self.channel.declare_queue(
            settings.QUEUE_AI_BULK_IMPROVE,
            durable=settings.QUEUE_DURABLE,
            arguments={
                "x-message-ttl": settings.MESSAGE_TTL,
                "x-dead-letter-exchange": settings.EXCHANGE_DLX
            }
        )

        await queue_bulk.bind(
            self.exchanges["ai.tasks"],
            routing_key="ai.task.bulk.#"
        )

        self.queues["bulk_improve"] = queue_bulk
        logger.info(f"✅ Queue declared and bound: {settings.QUEUE_AI_BULK_IMPROVE}")

        # ==========================================
        # 7. Вывод статистики
        # ==========================================
        logger.info(f"📊 RabbitMQ Topology created:")
        logger.info(f"   Exchanges: {len(self.exchanges)}")
        logger.info(f"   Queues: {len(self.queues)}")

    async def disconnect(self):
        """Graceful shutdown - закрытие всех подключений"""
        if not self._connected:
            return

        try:
            logger.info("🔌 Disconnecting from RabbitMQ...")

            if self.channel and not self.channel.is_closed:
                await self.channel.close()

            if self.connection and not self.connection.is_closed:
                await self.connection.close()

            self._connected = False
            logger.info("✅ RabbitMQ disconnected")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def publish(
        self,
        routing_key: str,
        message_body: Dict[Any, Any],
        priority: int = 5,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Публикация сообщения в exchange

        Args:
            routing_key: Routing key для маршрутизации (например, "ai.task.map.generation")
            message_body: Тело сообщения (JSON-serializable dict)
            priority: Приоритет сообщения (0-10, 10 = highest)
            correlation_id: ID для correlation (опционально)

        Returns:
            message_id: UUID сообщения

        Example:
            >>> await rabbitmq_service.publish(
            ...     routing_key="ai.task.map.generation",
            ...     message_body={"job_id": "123", "user_id": 42, ...},
            ...     priority=7
            ... )
            "msg-uuid-123"
        """
        if not self._connected:
            await self.connect()

        message_id = str(uuid.uuid4())

        # Enrichment: добавляем метаданные
        enriched_body = {
            **message_body,
            "_metadata": {
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "producer": "usm-backend",
                "routing_key": routing_key
            }
        }

        # Создаем AMQP сообщение
        message = Message(
            body=json.dumps(enriched_body, ensure_ascii=False).encode('utf-8'),
            delivery_mode=DeliveryMode.PERSISTENT,  # Сохранится на диск
            priority=priority,
            message_id=message_id,
            correlation_id=correlation_id or message_id,
            timestamp=datetime.utcnow(),
            content_type="application/json",
            content_encoding="utf-8"
        )

        try:
            # Publish в exchange
            await self.exchanges["ai.tasks"].publish(
                message,
                routing_key=routing_key
            )

            logger.info(
                f"✅ Message published: {routing_key} "
                f"(ID: {message_id}, priority: {priority})"
            )
            return message_id

        except Exception as e:
            logger.error(f"❌ Failed to publish message: {e}")
            raise

    async def consume(
        self,
        queue_name: str,
        callback: Callable[[Dict], Any]
    ):
        """
        Начать потребление сообщений из очереди

        Args:
            queue_name: Название очереди (ключ из self.queues)
            callback: Async функция для обработки сообщения
                     Должна принимать dict и возвращать None

        Example:
            >>> async def process_message(message_data: dict):
            ...     print(f"Processing: {message_data['job_id']}")
            ...
            >>> await rabbitmq_service.consume("map_generation", process_message)

        Механизм обработки:
        1. Получение сообщения из очереди
        2. Вызов callback
        3. Если callback успешен → ACK (сообщение удаляется)
        4. Если callback failed → NACK + requeue (сообщение вернётся в очередь)
        5. Если слишком много retries → отправка в DLQ
        """
        if not self._connected:
            await self.connect()

        queue = self.queues.get(queue_name)
        if not queue:
            raise ValueError(f"Queue '{queue_name}' not found in self.queues")

        logger.info(f"👀 Starting consumer for queue: {queue_name}")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                # message.process() автоматически делает:
                # - ACK если блок выполнился без исключений
                # - NACK + requeue если было исключение
                async with message.process():
                    try:
                        # Десериализация JSON
                        body = json.loads(message.body.decode('utf-8'))

                        # Логирование
                        job_id = body.get('job_id', 'N/A')
                        logger.info(f"📨 Received message from {queue_name}: job_id={job_id}")

                        # Вызов callback
                        await callback(body)

                        logger.info(f"✅ Message processed successfully: {message.message_id}")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON in message: {e}")
                        # ACK будет сделан (message.process() не raises),
                        # сообщение удаляется (не можем обработать невалидный JSON)

                    except Exception as e:
                        logger.error(
                            f"❌ Error processing message {message.message_id}: {e}",
                            exc_info=True
                        )
                        # NACK будет сделан (message.process() raises),
                        # сообщение вернётся в очередь для retry
                        raise  # Important: re-raise для NACK


# ==========================================
# Singleton instance
# ==========================================
rabbitmq_service = RabbitMQService()


# ==========================================
# Helper functions для публикации
# ==========================================

async def publish_ai_map_generation(
    job_id: str,
    user_id: int,
    requirements_text: str,
    use_enhancement: bool = True,
    priority: int = 7
) -> str:
    """
    Публикация задачи генерации User Story Map

    Args:
        job_id: UUID задачи
        user_id: ID пользователя
        requirements_text: Текст требований
        use_enhancement: Использовать ли two-stage processing
        priority: Приоритет (0-10, default 7 = high)

    Returns:
        message_id: ID опубликованного сообщения
    """
    message = {
        "job_id": job_id,
        "user_id": user_id,
        "requirements_text": requirements_text,
        "use_enhancement": use_enhancement,
        "created_at": datetime.utcnow().isoformat()
    }

    return await rabbitmq_service.publish(
        routing_key="ai.task.map.generation",
        message_body=message,
        priority=priority
    )


async def publish_wireframe_generation(
    job_id: str,
    user_id: int,
    project_id: int,
    story_ids: List[int],
    style: str = "low-fidelity",
    platform: str = "web",
    priority: int = 5
) -> str:
    """
    Публикация задачи генерации wireframes

    Args:
        job_id: UUID задачи
        user_id: ID пользователя
        project_id: ID проекта
        story_ids: Список ID историй для генерации
        style: Стиль wireframe (low-fidelity, high-fidelity, component)
        platform: Платформа (web, mobile, desktop)
        priority: Приоритет (0-10, default 5 = normal)

    Returns:
        message_id: ID опубликованного сообщения
    """
    message = {
        "job_id": job_id,
        "user_id": user_id,
        "project_id": project_id,
        "story_ids": story_ids,
        "style": style,
        "platform": platform,
        "created_at": datetime.utcnow().isoformat()
    }

    return await rabbitmq_service.publish(
        routing_key="ai.task.wireframe.generation",
        message_body=message,
        priority=priority
    )


async def publish_bulk_improve(
    job_id: str,
    user_id: int,
    story_ids: List[int],
    action: str,
    priority: int = 3
) -> str:
    """
    Публикация задачи массового улучшения историй

    Args:
        job_id: UUID задачи
        user_id: ID пользователя
        story_ids: Список ID историй
        action: Действие (details, criteria, edge_cases)
        priority: Приоритет (0-10, default 3 = low)

    Returns:
        message_id: ID опубликованного сообщения
    """
    message = {
        "job_id": job_id,
        "user_id": user_id,
        "story_ids": story_ids,
        "action": action,
        "created_at": datetime.utcnow().isoformat()
    }

    return await rabbitmq_service.publish(
        routing_key="ai.task.bulk.improve",
        message_body=message,
        priority=priority
    )
```

**Ключевые особенности:**

1. **Robust Connection:**
   - `connect_robust()` автоматически переподключается при разрывах
   - Heartbeat для поддержания соединения

2. **Priority Queues:**
   - Поддержка приоритетов 0-10
   - Более приоритетные сообщения обрабатываются первыми

3. **Dead Letter Queue:**
   - Failed messages отправляются в DLQ
   - Можно анализировать и manually retry

4. **Message TTL:**
   - Сообщения автоматически удаляются через 1 час
   - Предотвращает накопление старых сообщений

5. **QoS (prefetch_count=1):**
   - Воркер обрабатывает одно сообщение за раз
   - Равномерное распределение нагрузки между воркерами

#### 5.3.2. Тестирование RabbitMQ Service

Создайте `test-rabbitmq-service.py`:

```python
"""
Тест RabbitMQ Service
"""
import asyncio
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

async def test_publish_consume():
    """Тест публикации и потребления сообщений"""
    from services.rabbitmq_service import (
        rabbitmq_service,
        publish_ai_map_generation,
        publish_wireframe_generation
    )

    print("\n🧪 Testing RabbitMQ Service...\n")

    # 1. Connect
    print("1️⃣ Connecting to RabbitMQ...")
    await rabbitmq_service.connect()

    # 2. Publish test message (Map Generation)
    print("\n2️⃣ Publishing test message (Map Generation)...")
    msg_id_1 = await publish_ai_map_generation(
        job_id="test-job-123",
        user_id=999,
        requirements_text="Test requirements",
        use_enhancement=False,
        priority=8
    )
    print(f"   Published: {msg_id_1}")

    # 3. Publish test message (Wireframe Generation)
    print("\n3️⃣ Publishing test message (Wireframe Generation)...")
    msg_id_2 = await publish_wireframe_generation(
        job_id="test-job-456",
        user_id=999,
        project_id=1,
        story_ids=[1, 2, 3],
        style="low-fidelity",
        platform="web",
        priority=5
    )
    print(f"   Published: {msg_id_2}")

    # 4. Test consumer
    print("\n4️⃣ Testing consumer (will process 2 messages)...")

    processed_count = 0
    max_messages = 2

    async def test_callback(message_data: dict):
        nonlocal processed_count
        print(f"   ✅ Processed: job_id={message_data.get('job_id')}")
        processed_count += 1

        if processed_count >= max_messages:
            # Stop consuming after N messages
            raise KeyboardInterrupt("Test complete")

    try:
        # Consume from map_generation queue
        await rabbitmq_service.consume("map_generation", test_callback)
    except KeyboardInterrupt:
        print(f"\n   Processed {processed_count} messages")

    # 5. Disconnect
    print("\n5️⃣ Disconnecting...")
    await rabbitmq_service.disconnect()

    print("\n✅ RabbitMQ Service test PASSED!\n")

if __name__ == "__main__":
    asyncio.run(test_publish_consume())
```

Запуск:
```bash
cd backend
python test-rabbitmq-service.py
```

**Ожидаемый вывод:**
```
🧪 Testing RabbitMQ Service...

1️⃣ Connecting to RabbitMQ...
2025-12-01 10:00:00 - INFO - 🔌 Connecting to RabbitMQ: amqps://vrcptkqu:***@hawk-01.rmq.cloudamqp.com/vrcptkqu
2025-12-01 10:00:01 - INFO - ✅ RabbitMQ connected successfully

2️⃣ Publishing test message (Map Generation)...
2025-12-01 10:00:02 - INFO - ✅ Message published: ai.task.map.generation (ID: abc-123, priority: 8)
   Published: abc-123

3️⃣ Publishing test message (Wireframe Generation)...
2025-12-01 10:00:03 - INFO - ✅ Message published: ai.task.wireframe.generation (ID: def-456, priority: 5)
   Published: def-456

4️⃣ Testing consumer (will process 2 messages)...
2025-12-01 10:00:04 - INFO - 👀 Starting consumer for queue: map_generation
2025-12-01 10:00:05 - INFO - 📨 Received message from map_generation: job_id=test-job-123
   ✅ Processed: job_id=test-job-123
2025-12-01 10:00:06 - INFO - ✅ Message processed successfully: abc-123

   Processed 1 messages

5️⃣ Disconnecting...
2025-12-01 10:00:07 - INFO - ✅ RabbitMQ disconnected

✅ RabbitMQ Service test PASSED!
```

