# Интеграция Gemini API

## 🎉 Что добавлено

Добавлена поддержка Google Gemini API с умным управлением лимитами и оптимальным выбором моделей для разных задач.

## 🚀 Настройка

### 1. Получение API ключа

1. Перейдите на https://makersuite.google.com/app/apikey
2. Создайте API ключ
3. Добавьте в `.env` файл:

```bash
GEMINI_API_KEY=AIzaYourKeyHere
```

### 2. Конфигурация моделей

В `.env` файле можно настроить модели для разных задач:

```bash
# Приоритет провайдеров (первый - приоритетный)
AI_PROVIDER_PRIORITY=gemini,groq,openai

# Модели Gemini для разных задач
GEMINI_ENHANCEMENT_MODEL=gemini-2.0-flash-exp    # Stage 1: Enhancement (250 RPD)
GEMINI_GENERATION_MODEL=gemini-2.0-flash-exp     # Stage 2: Generation (50 RPD для Pro)
GEMINI_ASSISTANT_MODEL=gemini-2.0-flash-exp      # AI Assistant (250 RPD)

# Проактивные лимиты (переключение ДО исчерпания)
GEMINI_PRO_LIMIT=45       # Из 50 RPD
GEMINI_FLASH_LIMIT=230    # Из 250 RPD
```

## 📊 Оптимальная стратегия использования

### Рекомендуемая конфигурация

```bash
# Stage 1 (Enhancement): быстрая модель
GEMINI_ENHANCEMENT_MODEL=gemini-2.0-flash-exp  # 250 RPD, быстро

# Stage 2 (Generation): мощная модель
GEMINI_GENERATION_MODEL=gemini-2.0-flash-exp   # Можно использовать Pro: gemini-2.5-pro
                                                # Pro: 50 RPD, высокое качество

# AI Assistant: баланс скорости и качества
GEMINI_ASSISTANT_MODEL=gemini-2.0-flash-exp    # 250 RPD, достаточно для улучшений
```

### Доступные модели Gemini

| Модель | RPD (бесплатно) | Применение | Особенности |
|--------|-----------------|------------|-------------|
| `gemini-2.0-flash-exp` | 250 | Enhancement, Assistant | Быстрая, хорошее качество |
| `gemini-2.5-flash` | 250 | Enhancement, Assistant | Стабильная версия Flash |
| `gemini-2.5-pro` | 50 | Generation (карты) | Мощная, лучшее качество |
| `gemini-2.0-flash-thinking-exp` | ? | Экспериментальная | Улучшенное "мышление" |

## 🔄 Система Fallback

### Приоритеты провайдеров

По умолчанию:
```
Gemini → Groq → OpenAI
```

### Как работает fallback

1. **Проактивное переключение**: При приближении к лимиту (45/50 для Pro, 230/250 для Flash) система автоматически переключается на следующий провайдер
2. **Обработка ошибок**: При 429 (rate limit) или 503 (unavailable) переключение на следующий провайдер
3. **Умный выбор моделей**: Каждый провайдер использует оптимальную модель для конкретной задачи

### Пример работы

```
1. Enhancement (Stage 1):
   → Gemini Flash (230/250) → доступен
   ✅ Использует Gemini Flash

2. Generation (Stage 2):
   → Gemini Pro (48/50) → близко к лимиту, пропускаем
   → Groq llama-3.3-70b → доступен
   ✅ Использует Groq

3. AI Assistant:
   → Gemini Flash (231/250) → доступен
   ✅ Использует Gemini Flash
```

## 📈 Rate Limiting

### Автоматическое отслеживание

Система автоматически отслеживает использование API:

- Счетчик обновляется при каждом успешном запросе
- Лимиты сбрасываются в 00:00 UTC
- Старые записи (>2 дней) автоматически удаляются

### Проактивные лимиты

Вместо ожидания 429 ошибки, система переключается заранее:

```python
GEMINI_PRO_LIMIT=45      # Переключимся при 45/50 запросов
GEMINI_FLASH_LIMIT=230   # Переключимся при 230/250 запросов
```

## 🧪 Тестирование

### Запуск тестов

```bash
cd backend
source venv/bin/activate
python test_gemini_integration.py
```

### Пример успешного вывода

```
============================================================
ТЕСТИРОВАНИЕ GEMINI API ИНТЕГРАЦИИ
============================================================

1. Проверка конфигурации
   ✓ GEMINI_API_KEY: Установлен
   ✓ Available providers: ['gemini', 'groq', 'openai']
   ...

2. Проверка инициализации Gemini клиента
   ✓ Gemini client initialized successfully

3. Проверка Rate Limiter
   ✓ Rate limiter test: Count = 1
   ✓ Should skip provider: False

4. Проверка выбора моделей
   ✓ Enhancement model: gemini-2.0-flash-exp
   ✓ Generation model: gemini-2.0-flash-exp
   ✓ Assistant model: gemini-2.0-flash-exp

5. Тестовый запрос к Gemini API
   → Отправляю запрос к модели gemini-2.0-flash-exp...
   ✓ Получен ответ от Gemini API

============================================================
РЕЗУЛЬТАТЫ ТЕСТОВ
============================================================
Client Init          ✅ PASSED
Rate Limiter         ✅ PASSED
Model Selection      ✅ PASSED
API Call             ✅ PASSED
============================================================
🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!
============================================================
```

## 💡 Преимущества интеграции

1. **Бесплатные лимиты**: 250 RPD для Flash, 50 RPD для Pro
2. **Высокое качество**: Особенно Pro модели для сложных задач
3. **Автоматический fallback**: Бесшовное переключение при исчерпании лимитов
4. **Проактивное управление**: Переключение ДО достижения лимита
5. **Гибкая конфигурация**: Разные модели для разных задач

## 🔧 Troubleshooting

### Gemini client not initialized

**Проблема**: Клиент не инициализирован

**Решение**:
1. Проверьте наличие `GEMINI_API_KEY` в `.env`
2. Убедитесь, что ключ начинается с `AIza`
3. Проверьте, что библиотека установлена: `pip install google-generativeai`

### Rate limit errors (429)

**Проблема**: Достигнут лимит запросов

**Решение**:
1. Уменьшите проактивные лимиты в `.env`:
   ```bash
   GEMINI_PRO_LIMIT=40
   GEMINI_FLASH_LIMIT=220
   ```
2. Убедитесь, что настроены fallback провайдеры (Groq, OpenAI)

### Content blocked

**Проблема**: Gemini блокирует контент

**Решение**:
- Настройки безопасности установлены на `BLOCK_NONE`
- Если проблема сохраняется, система автоматически переключится на fallback провайдера

## 📝 Логирование

Система логирует все важные события:

```
✅ Initialized Gemini API client
Trying GEMINI with model gemini-2.0-flash-exp
✅ Successfully got response from GEMINI
⏩ Skipping GEMINI - approaching rate limit
```

## 🎯 Использование в коде

Изменения прозрачны - существующий код работает без изменений:

```python
# Автоматически использует Gemini (если доступен)
result = enhance_requirements(raw_text, redis_client)

# Автоматически использует Gemini (если доступен)
map_data = generate_ai_map(requirements_text, redis_client)

# Автоматически использует Gemini (если доступен)
improved = ai_improve_story_content(story_data, user_prompt, action)
```

## 📚 Дополнительная информация

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Get API Key](https://makersuite.google.com/app/apikey)
- [Rate Limits](https://ai.google.dev/pricing)
