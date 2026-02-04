# AI Assistant - Быстрый старт 🚀

## Что нового?

На каждой карточке User Story появилась кнопка **"✨ AI"**, которая открывает AI помощника для улучшения истории.

## Как использовать?

### 1. Откройте любой проект

```bash
# Запустите backend (если ещё не запущен)
cd backend
source venv/bin/activate
python main.py

# Запустите frontend (в другом терминале)
cd frontend
npm run dev
```

### 2. Нажмите кнопку "✨ AI" на карточке

Откроется модальное окно с 4 быстрыми действиями:

- **📝 Добавить детали** - расширяет описание
- **✅ Улучшить критерии** - улучшает acceptance criteria  
- **✂️ Разделить** - разделяет историю на несколько
- **⚠️ Edge cases** - добавляет граничные случаи

### 3. Или введите свой запрос

Примеры:
- "Добавь больше деталей про оплату и обработку ошибок"
- "Улучши acceptance criteria для мобильного приложения"
- "Добавь edge cases для offline режима"
- "Раздели эту историю на backend и frontend части"

### 4. Нажмите "Улучшить историю"

AI обработает запрос и:
- **Обновит историю** автоматически (для improve actions)
- **Покажет предпросмотр** новых историй (для split action)

## Примеры запросов

### Быстрые действия

```
📝 Добавить детали
→ AI расширяет описание, добавляет контекст использования

✅ Улучшить критерии
→ AI делает AC более конкретными и измеримыми

✂️ Разделить
→ AI предлагает 2-3 более мелкие истории

⚠️ Edge cases
→ AI добавляет граничные случаи и обработку ошибок
```

### Свободные запросы

```
"Добавь информацию про безопасность и шифрование"
→ AI добавит детали про HTTPS, токены, хеширование паролей

"Улучши AC для мобильного приложения"
→ AI добавит критерии для iOS/Android, жесты, адаптивность

"Добавь кейсы для медленного интернета"
→ AI добавит loading states, retry logic, offline режим

"Раздели на MVP и Later фичи"
→ AI разделит на базовую версию и дополнения
```

## Лимиты

- ⏰ **20 запросов в час** на карточку
- 📦 **10 запросов в час** для массового улучшения
- 🚀 **До 10 карточек** за раз для bulk improve

## Массовое улучшение (Bulk)

API эндпоинт для массового улучшения:

```bash
curl -X POST http://localhost:8000/stories/ai-bulk-improve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "story_ids": [123, 124, 125],
    "prompt": "Улучши acceptance criteria",
    "action": "criteria"
  }'
```

## Проверка работы

### 1. Проверьте API ключ

```bash
echo $OPENAI_API_KEY
# Должен быть установлен и начинаться с sk-
```

### 2. Проверьте Redis (опционально)

```bash
redis-cli ping
# Должно вернуть: PONG
```

Если Redis недоступен - не страшно, кеширование просто не будет работать.

### 3. Проверьте backend логи

```bash
cd backend
tail -f server.log
```

При работе AI Assistant вы должны видеть:
```
INFO - Improving story with prompt length: 45 chars, action: details
INFO - Successfully received AI improvement response
INFO - Improvement result cached in Redis
```

## Troubleshooting

### Ошибка: "AI API key not configured"

```bash
# Установите API ключ
export OPENAI_API_KEY=sk-your-api-key-here
```

### Ошибка: "Rate limit exceeded"

Подождите час или измените лимит в коде:

```python
# backend/api/stories.py
@router.post("/story/{story_id}/ai-improve")
@limiter.limit("50/hour")  # Увеличьте с 20 до 50
```

### AI возвращает не то, что ожидалось

1. Попробуйте переформулировать запрос более конкретно
2. Используйте quick actions вместо свободного ввода
3. Разбейте сложный запрос на несколько простых

### История улучшений не сохраняется

Это нормально - история хранится только в памяти компонента.  
При закрытии модального окна она очищается.  
В будущих версиях будет сохранение в БД.

## API Reference

### Single Improve
```
POST /story/{id}/ai-improve
```

**Body:**
```json
{
  "prompt": "Ваш запрос",
  "action": "details|criteria|split|edge_cases"  // опционально
}
```

### Bulk Improve
```
POST /stories/ai-bulk-improve
```

**Body:**
```json
{
  "story_ids": [1, 2, 3],
  "prompt": "Ваш запрос",
  "action": "details|criteria|edge_cases"  // split не поддерживается
}
```

## Дополнительная информация

- 📖 Полная документация: `FEATURE_AI_ASSISTANT.md`
- 🗺️ Roadmap проекта: `ROADMAP.md`
- 📝 Changelog: `CHANGELOG.md`

## Feedback

Если есть идеи по улучшению AI Assistant, создайте issue в GitHub или напишите разработчикам! 💡

