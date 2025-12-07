# 🔄 Migration: OpenAI → Gemini/Groq/Perplexity

## Изменения

### ✅ Что изменилось

1. **Config.py обновлен:**
   - ✅ Добавлен `GEMINI_API_KEY`
   - ✅ Приоритет изменен: `gemini → groq → perplexity` (вместо `groq → perplexity → openai`)
   - ✅ Удалена зависимость от `OPENAI_API_KEY`

2. **Wireframe Worker переписан:**
   - ✅ Новый файл: `backend/workers/wireframe_worker_text.py`
   - ✅ Генерирует **text-based wireframes** (ASCII + Markdown)
   - ✅ Работает с Gemini/Groq/Perplexity (без OpenAI/DALL-E)

3. **Убраны зависимости:**
   - ❌ OpenAI client
   - ❌ DALL-E 3 image generation
   - ❌ Cloudinary (для хранения изображений)

### 📊 Сравнение подходов

| Параметр | OpenAI + DALL-E (старое) | Text-Based (новое) |
|----------|--------------------------|-------------------|
| **Провайдер** | OpenAI (GPT-4 + DALL-E 3) | Gemini/Groq/Perplexity |
| **Стоимость** | ~$0.045 per wireframe | $0 (бесплатно) |
| **Время генерации** | ~20-30 сек | ~5-10 сек |
| **Формат output** | PNG изображение | ASCII + Markdown |
| **Редактируемость** | Нужно перегенерировать | Легко редактировать текст |
| **Version control** | Binary файлы | Text файлы (git-friendly) |
| **API ограничения** | Rate limits + $ | Free tier достаточен |

### 🎨 Пример output (Text-Based Wireframe)

```ascii
┌─────────────────────────────────────────┐
│  Logo      User Story Mapper    [Login] │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Create Account                   │ │
│  │                                   │ │
│  │  Email:    [___________________]  │ │
│  │  Password: [___________________]  │ │
│  │  Confirm:  [___________________]  │ │
│  │                                   │ │
│  │         [Create Account]          │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

+ Детальное описание Layout
+ Список всех UI элементов
+ Навигация
+ UX заметки

---

## 🚀 Как использовать

### 1. Environment Variables

Обновите `.env`:

```bash
# ✅ NEW - Добавьте Gemini
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
PERPLEXITY_API_KEY=pplx-...

# Приоритет (gemini первый)
AI_PROVIDER_PRIORITY=gemini,groq,perplexity

# ❌ REMOVE - Больше не нужны
# OPENAI_API_KEY=...
# WIREFRAME_DALLE_MODEL=...
# CLOUDINARY_CLOUD_NAME=...
# CLOUDINARY_API_KEY=...
# CLOUDINARY_API_SECRET=...
```

### 2. Dependencies

Обновите `requirements.txt`:

```bash
# ❌ REMOVE
# openai>=1.0.0
# cloudinary>=1.36.0

# ✅ Уже используется для map generation
# (Gemini/Groq работают через существующий ai_service.py)
```

### 3. Запуск Worker

```bash
# Новый text-based worker
cd backend
python workers/wireframe_worker_text.py
```

### 4. Frontend (опционально)

Wireframe component теперь показывает markdown вместо изображения:

```jsx
// Вместо <img src={wireframe.image_url} />
<div className="wireframe-text">
  <pre>{wireframe.ascii_wireframe}</pre>
  <div dangerouslySetInnerHTML={{
    __html: marked(wireframe.layout_description)
  }} />
</div>
```

---

## 📝 Что нужно обновить в документации

### RABBITMQ_IMPLEMENTATION_PLAN.md

**Section 3.2:** Заменить "DALL-E Wireframe Worker" на "Text-Based Wireframe Worker"

**Ключевые изменения:**
- Строки 569-1086: Полная замена wireframe worker кода
- Строки 1088-1168: Удалить секцию "Конфигурация DALL-E стоимости"
- Строки 3509-3540: Обновить .env template (убрать OpenAI, добавить Gemini)

### RABBITMQ_COMPLETE_GUIDE.md

**Phase 2: Backend Infrastructure**

Обновить упоминания AI провайдеров:
- "OpenAI" → "Gemini/Groq/Perplexity"
- Удалить секции про Cloudinary setup

---

## ✅ Checklist миграции

- [x] Config.py обновлен (Gemini добавлен)
- [x] Wireframe Worker переписан (text-based)
- [ ] Environment variables обновлены в `.env`
- [ ] Dependencies обновлены (`requirements.txt`)
- [ ] Worker запущен и протестирован
- [ ] Frontend обновлен (если нужно)
- [ ] Документация обновлена

---

## 🔮 Будущие улучшения (опционально)

1. **HTML Preview:** Конвертировать ASCII wireframe в HTML preview
2. **Image Generation:** Добавить опциональную генерацию изображений через:
   - Stability AI (Stable Diffusion) - бесплатный tier
   - Hugging Face Inference API - бесплатно
3. **Figma Export:** Экспорт text-based wireframe в Figma через API
4. **Interactive Preview:** Интерактивный preview wireframe в браузере

---

**Status:** ✅ Migration Ready

Все основные компоненты обновлены. Следуйте checklist выше для завершения миграции.
