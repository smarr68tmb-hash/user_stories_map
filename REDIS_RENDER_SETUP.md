# Настройка Redis на Render.com

## Проблема

Если вы видите в логах:
```
Redis unavailable (detail: Redis unavailable. Wireframe generation will fall back to synchronous mode.)
```

Это означает, что Redis недоступен для очереди задач (wireframe generation). Система автоматически переключается на синхронную генерацию, но это работает медленнее.

## Решение: Настройка Redis на Render

### Вариант 1: Создать Redis сервис на Render (рекомендуется)

1. **В Render Dashboard:**
   - Перейдите в **Dashboard** → **New +** → **Redis**
   - Выберите план (для начала подойдет **Free**)
   - Укажите имя (например: `usm-redis`)
   - Нажмите **Create Redis**

2. **После создания Redis:**
   - Render автоматически создаст переменную окружения `REDIS_URL`
   - Скопируйте значение `REDIS_URL` из настроек Redis сервиса
   - Оно будет выглядеть примерно так: `rediss://default:password@redis-host:6379`

3. **Настройте переменную окружения в Web Service:**
   - Перейдите в ваш **Web Service** (backend)
   - Откройте **Environment** → **Environment Variables**
   - Добавьте или обновите переменную:
     - **Key:** `REDIS_URL`
     - **Value:** скопируйте из Redis сервиса (или используйте формат: `rediss://default:password@host:6379`)
   - Нажмите **Save Changes**

4. **Перезапустите Web Service:**
   - После сохранения переменных окружения Render автоматически перезапустит сервис
   - Или нажмите **Manual Deploy** → **Deploy latest commit**

### Вариант 2: Использовать внешний Redis (Upstash, Redis Cloud и т.д.)

Если у вас уже есть Redis на другом сервисе:

1. **Получите Redis URL** от вашего провайдера
   - Для Upstash: формат `rediss://default:password@host:6379`
   - Для Redis Cloud: формат `redis://default:password@host:port`

2. **Добавьте в переменные окружения Web Service:**
   - **Key:** `REDIS_URL`
   - **Value:** ваш Redis URL
   - Нажмите **Save Changes**

3. **Перезапустите Web Service**

## Проверка работы Redis

### 1. Проверьте логи на Render

После перезапуска проверьте логи Web Service:

**Успешное подключение:**
```
🔌 QueueAdapter: connecting to Redis at ...
✅ QueueAdapter initialized with Redis RQ (TLS: True, queue: wireframes)
```

**Если Redis недоступен:**
```
⚠️ QueueAdapter: Redis unavailable for queue operations
```

### 2. Проверьте переменные окружения

В Render Dashboard:
- **Web Service** → **Environment** → **Environment Variables**
- Убедитесь, что `REDIS_URL` установлен и правильный

### 3. Проверьте health endpoint

Откройте в браузере:
```
https://your-app.onrender.com/ready
```

Должно вернуть:
```json
{
  "status": "ready",
  "database": "ok",
  "redis": "ok",  // ← должно быть "ok", а не "unavailable"
  "timestamp": "..."
}
```

## Важные моменты для Render

### TLS/SSL подключение

- Render Redis использует **TLS** (rediss://)
- Убедитесь, что `REDIS_URL` начинается с `rediss://` (с двумя 's')
- Код автоматически определяет TLS по префиксу URL

### Формат REDIS_URL

**Правильный формат:**
```
rediss://default:password@host:6379
```

**Неправильный формат:**
```
redis://localhost:6379  ← не работает на Render (локальный адрес)
```

### Если Redis все еще недоступен

1. **Проверьте логи Web Service:**
   - Render Dashboard → **Web Service** → **Logs**
   - Ищите сообщения с `Redis`, `QueueAdapter`, `connection`

2. **Проверьте, что Redis сервис запущен:**
   - Render Dashboard → **Redis Service** → **Status**
   - Должно быть **Available**

3. **Проверьте сетевую доступность:**
   - Убедитесь, что Redis и Web Service в одном регионе (если возможно)
   - Проверьте, что нет firewall блокировок

4. **Проверьте таймауты:**
   - Код использует таймаут 5 секунд для подключения
   - Если Redis медленно отвечает, увеличьте таймаут в коде (но это редко нужно)

## Что делать, если Redis недоступен

**Система продолжит работать!** Просто:

- ✅ Кеширование AI-ответов будет отключено (но AI все равно работает)
- ✅ Wireframe generation будет работать синхронно (медленнее, но работает)
- ⚠️ Очередь задач (RQ) не будет использоваться

**Рекомендация:** Настройте Redis для лучшей производительности, но это не критично для работы приложения.

## Диагностика через логи

После настройки Redis, в логах вы должны видеть:

**При успешном подключении:**
```
🔌 QueueAdapter: connecting to Redis at redis-host:6379
✅ QueueAdapter initialized with Redis RQ (TLS: True, queue: wireframes)
✅ QueueAdapter initialized successfully (driver: redis)
```

**При использовании кеша:**
```
✅ Cache HIT for AI map: ai_map:abc123...
✅ AI map result cached in Redis: ai_map:abc123... (TTL: 86400s, size: 1234 bytes)
```

**При недоступности Redis:**
```
⚠️ QueueAdapter: Redis unavailable for queue operations (driver: redis): Redis connection failed: ...
⚠️ Redis unavailable for wireframe queue. Wireframe generation will fall back to synchronous mode.
🔄 Generating wireframe synchronously for project 123
✅ Wireframe generated synchronously for project 123
```

## Дополнительная информация

- Redis используется для:
  1. **Кеширования AI-ответов** (опционально, но рекомендуется)
  2. **Очереди задач для wireframe generation** (опционально, fallback на синхронный режим)
  
- Если Redis недоступен, система работает в **graceful degradation** режиме:
  - Все функции работают
  - Просто медленнее (нет кеша, синхронная генерация wireframe)

