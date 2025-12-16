# 🎯 Следующие шаги согласно фазам реализации

**Дата анализа:** Декабрь 2025  
**Текущая версия:** v2.4

---

## ✅ Что уже завершено

### Фаза 0: Demo-режим ✅
- ✅ Demo без регистрации (3 запроса/час)
- ✅ Кликабельные примеры
- ✅ Контекстный прогресс

### Фаза 1: Production Ready ✅
- ✅ PostgreSQL + миграции
- ✅ JWT аутентификация + Refresh Tokens
- ✅ Rate Limiting
- ✅ Health checks
- ✅ Redis кеширование
- ✅ Базовое тестирование

### Фаза 1: Streaming + Visibility ✅
- ✅ SSE streaming генерации
- ✅ Auto-показ анализа результатов
- ✅ AI Assistant sidebar

### Фаза 2.3: Story Analysis & Validation ✅
- ✅ Анализ схожести историй (TF-IDF)
- ✅ Валидация структуры карты
- ✅ AnalysisPanel компонент

---

## 🚀 Следующая фаза: Фаза 2 — Epic Breakdown + Share

**Приоритет:** ВЫСОКИЙ ⭐  
**Срок:** 2 недели  
**Цель:** Подготовка карты к передаче аналитику

### Зачем это нужно?
Сейчас истории представлены в плоском виде (Activity → Task → Story). Аналитику сложно работать с таким форматом. Нужно:
1. **AI-группировка** историй в логические эпики (3-7 эпиков)
2. **Epic Breakdown View** — второй режим просмотра карты
3. **Share Link** — публичная ссылка для просмотра без авторизации

---

## 📋 План реализации Фазы 2

### Неделя 1: Backend + AI группировка ✅ ЗАВЕРШЕНО

#### День 1-2: Модель данных для Epic ✅ ЗАВЕРШЕНО
**Файлы для создания/изменения:**
- ✅ `backend/models/epic.py` (новая модель)
- ✅ `backend/alembic/versions/6870130f1b69_add_epics_table.py` (миграция)
- ✅ `backend/schemas/epic.py` (Pydantic схемы)

**Задачи:**
- ✅ Создана модель `Epic` с полями:
  - id, project_id, title, description
  - confidence_score (0.0-1.0)
  - position, created_at, updated_at
  - relationship с Project и UserStory
- ✅ Добавлено поле `epic_id` в модель `UserStory`
- ✅ Создана миграция Alembic (6870130f1b69)
- ✅ Добавлены схемы: `EpicCreate`, `EpicResponse`, `EpicUpdate`, `EpicWithStoriesResponse`, `EpicGenerateRequest`, `EpicGenerateResponse`
- ✅ Обновлен `alembic/env.py` для импорта Epic
- ✅ Обновлены `models/__init__.py` и `schemas/__init__.py`

**Оценка:** 4-6 часов → **Выполнено**

---

#### День 3-4: AI-сервис группировки ✅ ЗАВЕРШЕНО
**Файлы:**
- ✅ `backend/services/epic_service.py` (новый сервис)

**Задачи:**
- ✅ Создана функция `group_stories_into_epics()`:
  - Принимает список историй, проект, min/max эпиков
  - Использует AI для группировки (3-7 эпиков)
  - Возвращает список эпиков с confidence_score
  - Поддерживает кеширование через Redis
- ✅ Промпт для AI:
  - Анализирует все истории проекта
  - Группирует по функциональности/сценариям/доменам
  - Возвращает JSON: `[{title, description, story_ids, confidence}]`
- ✅ Интеграция с `ai_service.py` через `_make_request_with_fallback()`
- ✅ Fallback логика:
  - Группировка по Activity (если доступно)
  - Один эпик "Все истории" (если Activity нет)
  - Автоматический fallback при ошибках AI
- ✅ Функция `create_epics_from_grouping()` для создания в БД
- ✅ Обработка транзакций с rollback
- ✅ Валидация и обработка дубликатов

**Оценка:** 6-8 часов → **Выполнено**

---

#### День 5: API эндпоинты ✅ ЗАВЕРШЕНО
**Файлы:**
- ✅ `backend/api/epics.py` (новый файл)
- ✅ `backend/main.py` (роутер подключен)

**Задачи:**
- ✅ `POST /api/project/{project_id}/epics/generate`
  - Генерирует эпики для проекта через AI
  - Присваивает `epic_id` историям
  - Возвращает `EpicGenerateResponse` с созданными эпиками
  - Rate limit: 10 запросов в час
  - Валидация min/max эпиков
- ✅ `GET /api/project/{project_id}/epics`
  - Получить все эпики проекта с историями
  - Возвращает `List[EpicWithStoriesResponse]`
- ✅ `PUT /api/epic/{epic_id}`
  - Редактировать эпик (title, description, position)
  - Принимает `EpicUpdate`
- ✅ `POST /api/epic/{epic_id}/stories/{story_id}`
  - Добавить историю в эпик
  - Проверка на дубликаты
- ✅ `DELETE /api/epic/{epic_id}/stories/{story_id}`
  - Убрать историю из эпика
- ✅ `POST /api/epic/{epic_id}/accept`
  - Принять группировку (логирование)
- ✅ `POST /api/epic/{epic_id}/reject`
  - Отклонить эпик (удаляет эпик, отвязывает истории)
- ✅ Helper функции для проверки доступа:
  - `get_project_for_user()`
  - `get_epic_for_user()`
  - `get_story_for_user()`

**Оценка:** 4-6 часов → **Выполнено**

---

#### День 5 (дополнительно): Code Review и Тестирование ✅ ЗАВЕРШЕНО
**Файлы:**
- ✅ `backend/tests/test_epic_service.py` (15+ тестов)
- ✅ `backend/tests/test_epic_api.py` (8+ тестов)

**Задачи:**
- ✅ Code review с исправлением 5 критичных проблем:
  1. Транзакции с rollback
  2. Валидация min/max эпиков
  3. Сортировка историй перед группировкой
  4. Проверка на пустые эпики
  5. Проверка на дубликаты при добавлении историй
- ✅ Unit тесты для `epic_service.py`:
  - Подготовка данных для AI
  - Fallback группировка
  - AI группировка (успех, ошибки, edge cases)
  - Создание эпиков в БД (транзакции, дубликаты)
- ✅ Unit тесты для `api/epics.py`:
  - Helper функции (проверка доступа)
  - Валидация схем

**Оценка:** 4-6 часов → **Выполнено**

---

### Неделя 2: Frontend + Share Link

#### День 6-7: Epic Breakdown View
**Файлы:**
- `frontend/src/components/story-map/EpicBreakdownView.jsx` (новый)
- `frontend/src/StoryMap.jsx` (добавить toggle view)

**Задачи:**
- [ ] Создать компонент `EpicBreakdownView`:
  ```
  ┌─────────────────────────────────────┐
  │ [Story Map View] [Epic View] ← Toggle
  ├─────────────────────────────────────┤
  │ ┌─────────────────────────────────┐ │
  │ │ Epic: Checkout Flow            │ │
  │ │ Stories: 5 | Progress: 40%     │ │
  │ │ Confidence: 85%                │ │
  │ │                                │ │
  │ │ [✓] Story 1: Add to cart      │ │
  │ │ [✓] Story 2: Payment          │ │
  │ │ [ ] Story 3: Order review     │ │
  │ │ [ ] Story 4: Confirmation      │ │
  │ │ [ ] Story 5: Email notification│ │
  │ └─────────────────────────────────┘ │
  │ ┌─────────────────────────────────┐ │
  │ │ Epic: User Authentication      │ │
  │ │ Stories: 3 | Progress: 100%    │ │
  │ └─────────────────────────────────┘ │
  └─────────────────────────────────────┘
  ```
- [ ] Toggle между Story Map View и Epic View
- [ ] Показывать прогресс эпика (сколько историй done)
- [ ] Показывать confidence score (если <70%, предупреждение)
- [ ] Drag & Drop историй между эпиками
- [ ] Кнопки Accept/Reject/Edit для каждого эпика

**Оценка:** 8-10 часов

---

#### День 8-9: Share Link (публичный доступ)
**Backend файлы:**
- `backend/models/project.py` (добавить поле `share_token`)
- `backend/api/projects.py` (добавить эндпоинты)

**Frontend файлы:**
- `frontend/src/components/ShareDialog.jsx` (новый)

**Задачи:**
- [ ] Добавить `share_token: str | None` в модель `Project`
  - Генерировать UUID при создании share link
- [ ] `POST /api/project/{project_id}/share`
  - Создать/обновить share token
  - Возвращает публичную ссылку: `https://app.com/share/{token}`
- [ ] `GET /api/share/{token}`
  - Получить проект по share token (без авторизации)
  - Только чтение (view-only)
- [ ] `DELETE /api/project/{project_id}/share`
  - Отключить share link
- [ ] Frontend: кнопка "Share" в StoryMap
- [ ] Модальное окно с:
  - Публичной ссылкой (копировать)
  - QR-кодом для мобильных
  - Настройками (expire date, password protection — опционально)

**Оценка:** 6-8 часов

---

#### День 10: Сводка для аналитика
**Файлы:**
- `backend/api/projects.py` (новый эндпоинт)
- `frontend/src/components/AnalystSummary.jsx` (новый)

**Задачи:**
- [ ] `GET /api/project/{project_id}/summary`
  - Генерирует Markdown сводку:
    ```markdown
    # Project: E-commerce Platform
    
    ## Epics (5)
    
    ### 1. Checkout Flow (5 stories, 40% done)
    - [x] Add to cart
    - [x] Payment processing
    - [ ] Order review
    ...
    
    ## Statistics
    - Total stories: 23
    - MVP stories: 8
    - Release 1: 10
    - Later: 5
    ```
- [ ] Frontend: кнопка "📄 Export Summary"
- [ ] Скачивание как `.md` файл

**Оценка:** 3-4 часа

---

## 📊 Метрики успеха Фазы 2

- ✅ 70% пользователей используют Epic View перед передачей аналитику
- ✅ 50+ share links создано в первую неделю
- ✅ AI группировка работает с confidence >70% для 80% проектов

---

## 🔧 Технический долг (можно делать параллельно)

### Приоритет: ВЫСОКИЙ
- [ ] **Async AI запросы** (из Фазы 1, частично)
  - Переписать `ai_service.py` на async/await
  - Использовать `asyncio` для параллельных запросов
  - Оценка: 4-6 часов

### Приоритет: СРЕДНИЙ
- [ ] **E2E тесты** (Playwright)
  - Тест полного flow: генерация → Epic View → Share
  - Оценка: 6-8 часов

### Приоритет: НИЗКИЙ
- [ ] **TypeScript для frontend**
  - Постепенная миграция `.jsx` → `.tsx`
  - Начать с новых компонентов

---

## 🎯 После Фазы 2: Фаза 3 — FigJam Export

**Срок:** 2-3 недели после Фазы 2

**Задачи:**
- Генерация `.fig` файла (FigJam формат)
- Экспорт эпиков как Sections, историй как Sticky notes
- Connectors между зависимыми историями
- Превью перед экспортом

**Почему важно:** Команды уже работают в FigJam на discovery-фазе. Это снизит барьер использования.

---

## 📝 Рекомендации по реализации

### 1. Начните с Backend
Сначала реализуйте модели и API, потом frontend. Это позволит тестировать через Postman/Swagger.

### 2. Итеративный подход
- День 1-2: Модель Epic + миграция
- День 3: Простой AI промпт (группировка по ключевым словам)
- День 4: Улучшение AI промпта на основе тестов
- День 5: API эндпоинты

### 3. Тестирование
После каждого дня:
- Unit тесты для новых функций
- Ручное тестирование через API
- Проверка миграций на тестовой БД

### 4. Документация
Обновляйте:
- `CHANGELOG.md` — новые фичи
- `API.md` — новые эндпоинты
- `README.md` — скриншоты Epic View

---

## 🚨 Потенциальные проблемы

### Проблема 1: AI не может сгруппировать истории
**Решение:** 
- Fallback на простую группировку по Activity
- Или создавать 1 эпик "All Stories"
- Позволить пользователю вручную создавать эпики

### Проблема 2: Share token безопасность
**Решение:**
- Токены должны быть длинными (UUID v4)
- Опционально: expire date
- Опционально: password protection
- Rate limiting для `/share/{token}` эндпоинта

### Проблема 3: Производительность Epic View
**Решение:**
- Кешировать сгруппированные эпики в Redis
- Обновлять кеш только при изменении историй
- Lazy loading для больших проектов

---

## 📞 Вопросы для уточнения

1. **Epic confidence score:** Что делать если <50%? Показывать предупреждение или автоматически отклонять?
2. **Share link permissions:** Только view или можно комментировать?
3. **Epic редактирование:** Можно ли объединять эпики? Разделять на несколько?

---

*Последнее обновление: Декабрь 2025*  
*Следующий пересмотр: После завершения Фазы 2*

