# Как проверить запросы к AgentRouter

## Проблема
На дашборде не показываются запросы к agentrouter, как будто запросы не уходят туда.

## Способы проверки

### 1. Проверка статуса AgentRouter

Откройте в браузере или через curl:
```bash
curl http://localhost:8000/debug/ai-providers
```

Или:
```bash
curl http://localhost:8000/debug/agentrouter-requests
```

Это покажет:
- Инициализирован ли клиент AgentRouter
- Настроен ли API ключ
- Используется ли agentrouter для generation
- Приоритет agentrouter в списке провайдеров
- Количество запросов сегодня

### 2. Тестовый запрос к AgentRouter

Отправьте тестовый запрос:
```bash
curl -X POST http://localhost:8000/debug/test-agentrouter
```

Это принудительно отправит запрос к agentrouter и покажет результат.

### 3. Проверка логов

Теперь в логах бэкенда вы увидите детальную информацию о запросах к agentrouter:

**При отправке запроса:**
```
🚀 Sending request to AGENTROUTER:
   Model: claude-sonnet-4-5-20250514
   Base URL: https://agentrouter.ai/api/v1
   Messages: 2
   Prompt preview: ...
   Temperature: 0.7
   Timeout: 60.0s
```

**При успешном ответе:**
```
✅ AGENTROUTER response received:
   Response length: 1234 chars
   Model used: claude-sonnet-4-5-20250514
   Provider: agentrouter
```

**При ошибке:**
```
❌ AGENTROUTER failed (APIError): ...
   Error details: ...
   Trying next provider...
```

**Когда agentrouter пропускается:**
```
⏩ Skipping AGENTROUTER - approaching rate limit (count: 45)
```

### 4. Почему запросы могут не доходить до agentrouter?

1. **AgentRouter не в списке generation**
   - Проверьте: `GET /debug/agentrouter-requests`
   - Должно быть: `"is_used_for_generation": true`
   - AgentRouter используется только для `generation` и `assistant`, НЕ для `enhancement`

2. **API ключ не настроен**
   - Проверьте переменную окружения `AGENTROUTER_API_KEY`
   - Должно быть: `"has_api_key": true`

3. **Клиент не инициализирован**
   - Проверьте логи при старте приложения
   - Должно быть: `✅ Initialized AgentRouter API client (Claude Sonnet 4.5)`

4. **Fallback переключается на другой провайдер**
   - Если agentrouter возвращает ошибку, система автоматически переключается на следующий провайдер
   - Проверьте логи на наличие ошибок от agentrouter

5. **Rate limit**
   - Если достигнут лимит, agentrouter пропускается
   - Проверьте: `GET /debug/agentrouter-requests` → `usage.requests_today`

### 5. Как принудительно использовать agentrouter?

Для тестирования можно временно отключить другие провайдеры в `.env`:
```env
# Оставьте только agentrouter
AGENTROUTER_API_KEY=sk-your-key
# Закомментируйте остальные
# GEMINI_API_KEY=...
# GROQ_API_KEY=...
```

### 6. Мониторинг в реальном времени

Для мониторинга запросов в реальном времени:

```bash
# Следите за логами бэкенда
tail -f backend.log | grep -i agentrouter

# Или если логи выводятся в консоль
# Запустите бэкенд и смотрите вывод
```

### 7. Проверка через создание проекта

1. Создайте новый проект через UI
2. Введите требования и нажмите "Сгенерировать карту"
3. Проверьте логи - должны появиться строки с `🚀 Sending request to AGENTROUTER`

## Endpoints для отладки

- `GET /debug/ai-providers` - статус всех провайдеров
- `GET /debug/agentrouter-requests` - детальная информация о agentrouter
- `POST /debug/test-agentrouter` - тестовый запрос к agentrouter

## Что искать в логах

Ищите следующие строки:
- `🚀 Sending request to AGENTROUTER` - запрос отправляется
- `✅ AGENTROUTER response received` - успешный ответ
- `❌ AGENTROUTER failed` - ошибка
- `⏩ Skipping AGENTROUTER` - пропущен (лимит или не инициализирован)
- `🔄 Attempting to use AGENTROUTER` - попытка использования

