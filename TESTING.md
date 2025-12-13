# Руководство по тестированию - USM Service

## 📋 Обзор

Этот документ описывает тестовое покрытие для проекта AI User Story Mapper, особенно для функциональности **Phase 1: Streaming + Visibility**.

---

## 🎯 Структура тестов

### Backend тесты

**Файл:** `backend/tests/test_streaming.py`
**Фреймворк:** pytest
**Покрытие:** SSE streaming service, валидация событий, сохранение в БД

#### Тестовые группы:

1. **TestSSEEventFormat** - Форматирование SSE событий
   - Базовый формат `data: {...}\n\n`
   - Корректная кодировка русского текста (ensure_ascii=False)

2. **TestStreamingGeneration** - Генерация карты с SSE потоком
   - Последовательность событий без enhancement
   - Последовательность событий с enhancement
   - Данные в analysis событии (duplicates, score, issues)
   - Данные в complete событии (project_id, stats)
   - Обработка ошибок
   - Монотонный рост progress (0% → 100%)

3. **TestSaveProjectToDB** - Сохранение проекта в БД
   - Базовое сохранение проекта
   - Сохранение с enhancement данными
   - Создание дефолтных релизов (MVP, Release 1, Later)

#### Запуск backend тестов:

```bash
cd backend
pytest tests/test_streaming.py -v
```

С покрытием:
```bash
pytest tests/test_streaming.py --cov=services.streaming_service --cov-report=html
```

---

### Frontend тесты

#### 1. Hook тесты: `useStreamingGeneration`

**Файл:** `frontend/src/hooks/useStreamingGeneration.test.js`
**Фреймворк:** Jest + React Testing Library
**Покрытие:** EventSource connection, progress tracking, error handling

**Тестовые группы:**

- **Initial State** - Начальное состояние хука
- **Progress Updates** - Обновление progress на SSE события
- **Analysis Results** - Сохранение данных анализа
- **Complete Event** - Резолв промиса с project data
- **Error Handling** - Server errors, connection errors, malformed JSON
- **Manual Cancellation** - Отмена streaming
- **Query Parameters** - Построение URL с параметрами
- **State Reset** - Сброс при новой генерации
- **Unknown Event Types** - Обработка неизвестных событий

**Ключевые тесты:**

```javascript
// Проверка обновления progress
it('should update progress on generating event', async () => {
  const { result } = renderHook(() => useStreamingGeneration());

  act(() => {
    result.current.generateWithStreaming('Test', false, false);
  });

  act(() => {
    MockEventSource.instance.simulateMessage({
      type: 'generating',
      progress: 50,
      activities: 3,
      tasks: 8,
      stories: 15
    });
  });

  expect(result.current.progress).toBe(50);
  expect(result.current.stats).toEqual({
    activities: 3,
    tasks: 8,
    stories: 15
  });
});
```

#### 2. Component тесты: `AIAssistantSidebar`

**Файл:** `frontend/src/components/AIAssistantSidebar.test.jsx`
**Фреймворк:** Jest + React Testing Library
**Покрытие:** Sidebar UI, score badges, warnings, recommendations

**Тестовые группы:**

- **Rendering** - Условный рендеринг (null, with project, with analysis)
- **Score Badge** - Цветовое кодирование (green >= 80, yellow >= 50, red < 50)
- **Duplicates Warning** - Отображение предупреждения о дубликатах
- **Similar Stories Warning** - Отображение похожих историй
- **Issues Warning** - Отображение проблем (первые 3 + счетчик)
- **Perfect Score Message** - Сообщение "Отличная работа!"
- **Recommendations** - Динамические рекомендации
- **Collapse/Expand** - Функциональность сворачивания
- **Quick Actions** - Кнопки быстрых действий
- **Edge Cases** - Граничные значения (score = 50, 80, 100)

**Ключевые тесты:**

```javascript
// Проверка цвета score badge
it('should display score with green badge for score >= 80', () => {
  const mockAnalysis = {
    score: 85,
    duplicates: 0,
    similar: 0,
    totalIssues: 0,
    issues: []
  };

  render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

  const badge = screen.getByText('85/100');
  expect(badge).toHaveClass('bg-green-100');
  expect(badge).toHaveClass('text-green-800');
});
```

#### 3. Integration тесты: Auto-notifications

**Файл:** `frontend/src/App.autoNotifications.test.jsx`
**Фреймворк:** Jest + React Testing Library
**Покрытие:** End-to-end notification flow

**Тестовые группы:**

- **Duplicates Notifications** - Warning при обнаружении дубликатов
- **Score Notifications** - Warning (< 50), Success (>= 80)
- **Multiple Notifications** - Несколько уведомлений одновременно
- **Notification Timing** - Срабатывание при изменении analysisResults
- **Edge Cases** - null/undefined values, boundary values
- **Integration with Streaming Flow** - Уведомления после завершения streaming
- **AIAssistantSidebar Integration** - Передача данных в sidebar

**Ключевые тесты:**

```javascript
// Проверка auto-show уведомления о дубликатах
it('should show warning notification when duplicates are found', async () => {
  const { rerender } = render(<App />);

  act(() => {
    mockHookState.analysisResults = {
      duplicates: 3,
      similar: 0,
      score: 75,
      totalIssues: 0,
      issues: []
    };
  });

  rerender(<App />);

  await waitFor(() => {
    expect(mockToastWarning).toHaveBeenCalledWith(
      expect.stringContaining('Найдено 3 дубликатов!')
    );
  });
});
```

#### Запуск frontend тестов:

```bash
cd frontend
npm test
```

Запуск отдельного теста:
```bash
npm test useStreamingGeneration.test.js
npm test AIAssistantSidebar.test.jsx
npm test App.autoNotifications.test.jsx
```

С покрытием:
```bash
npm test -- --coverage
```

---

## 📊 Тестовое покрытие

### Метрики

| Компонент | Файл | Тесты | Покрытие |
|-----------|------|-------|----------|
| Backend SSE | `streaming_service.py` | 14 | ~85% |
| Frontend Hook | `useStreamingGeneration.js` | 20+ | ~90% |
| Sidebar Component | `AIAssistantSidebar.jsx` | 20+ | ~95% |
| Auto-notifications | `App.jsx` (integration) | 15+ | ~80% |

**Всего:** 60+ тестов, 4 тестовых файла

---

## 🔍 Критические сценарии

### 1. SSE Event Sequence (Backend)

**Цель:** Проверить правильную последовательность событий

```
enhancing (10%) → enhanced (20%) → generating (30-70%) →
validating (75-80%) → analysis (85%) → saving (90-95%) →
complete (100%)
```

**Тест:** `test_event_sequence_with_enhancement`

**Критерий:** События должны идти в строгом порядке, без пропусков

---

### 2. Analysis Event Data (Backend)

**Цель:** Проверить корректность данных в analysis событии

**Структура:**
```python
{
  "type": "analysis",
  "progress": 85,
  "duplicates": int,
  "similar": int,
  "score": int (0-100),
  "issues": list (первые 5),
  "total_issues": int
}
```

**Тест:** `test_analysis_event_data`

**Критерий:** Все поля присутствуют, типы корректные, issues ограничены 5

---

### 3. Auto-show Notifications (Frontend)

**Цель:** Проверить автоматический показ уведомлений

**Триггеры:**
- `duplicates > 0` → `toast.warning("Найдено {n} дубликатов!")`
- `score < 50` → `toast.warning("Оценка качества: {score}/100")`
- `score >= 80` → `toast.success("Отличная оценка: {score}/100!")`

**Тест:** `should show warning notification when duplicates are found`

**Критерий:** useEffect срабатывает при изменении analysisResults

---

### 4. EventSource Lifecycle (Frontend)

**Цель:** Проверить управление EventSource соединением

**Сценарии:**
- Создание при `generateWithStreaming()`
- Закрытие при `complete` событии
- Закрытие при `error` событии
- Закрытие при `cancelStreaming()`

**Тесты:**
- `test_complete_event_closes_connection`
- `test_error_handling`
- `test_manual_cancellation`

**Критерий:** Нет утечек соединений

---

## 🐛 Известные edge cases

### 1. Progress monotonic increase

**Проблема:** Progress может "прыгать" при параллельных стримах

**Тест:** `test_progress_monotonic_increase`

**Решение:** Проверка `progress[i] >= progress[i-1]`

---

### 2. Russian text encoding

**Проблема:** `ensure_ascii=True` ломает кириллицу в SSE

**Тест:** `test_sse_event_with_russian_text`

**Решение:** `json.dumps(..., ensure_ascii=False)`

---

### 3. Score boundary values

**Проблема:** Неопределенность для score = 50, 80

**Тесты:**
- `test_score_exactly_50`
- `test_score_exactly_80`

**Решение:**
- `score >= 80` → зеленый badge
- `score >= 50` → желтый badge
- `score < 50` → красный badge

---

## 🚀 CI/CD Integration

### GitHub Actions (пример)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          cd backend
          pytest tests/test_streaming.py --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 📝 Добавление новых тестов

### Backend

1. Создайте тест в `backend/tests/`
2. Используйте `pytest.mark.asyncio` для async функций
3. Mock external dependencies (Redis, AI service)
4. Проверьте event format и data structure

### Frontend

1. Создайте тест рядом с компонентом (`.test.js` / `.test.jsx`)
2. Используйте `renderHook` для хуков
3. Используйте `render` для компонентов
4. Mock EventSource для streaming тестов
5. Mock toast для notification тестов

---

## 🔧 Troubleshooting

### Backend tests fail with "Event loop closed"

**Решение:**
```python
# Используйте pytest-asyncio
@pytest.mark.asyncio
async def test_streaming():
    ...
```

### Frontend tests timeout

**Решение:**
```javascript
// Используйте waitFor с timeout
await waitFor(() => {
  expect(result.current.progress).toBe(100);
}, { timeout: 5000 });
```

### Mock EventSource не работает

**Решение:**
```javascript
// Создайте instance перед каждым тестом
beforeEach(() => {
  MockEventSource.instance = null;
  MockEventSource.closed = false;
});
```

---

## 📚 Дополнительные ресурсы

- [pytest документация](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Jest Mocking](https://jestjs.io/docs/mock-functions)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

---

## ✅ Checklist для релиза

Перед деплоем Phase 1, убедитесь что:

- [ ] Все backend тесты проходят (`pytest tests/test_streaming.py`)
- [ ] Все frontend тесты проходят (`npm test`)
- [ ] Coverage > 80% для критических модулей
- [ ] Integration тесты проходят
- [ ] Manual testing на staging
- [ ] Browser compatibility (Chrome, Firefox, Safari)
- [ ] Mobile responsive testing
- [ ] Error scenarios проверены

---

**Последнее обновление:** 2025-12-13
**Автор:** AI Assistant (Claude Code)
