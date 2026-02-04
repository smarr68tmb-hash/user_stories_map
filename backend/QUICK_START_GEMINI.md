# 🚀 Быстрый старт с Gemini API

## За 3 шага

### 1️⃣ Получите API ключ

Перейдите на https://makersuite.google.com/app/apikey и создайте ключ

### 2️⃣ Добавьте в .env

```bash
# Добавьте в backend/.env
GEMINI_API_KEY=AIzaYourKeyHere
```

### 3️⃣ Запустите

```bash
cd backend
source venv/bin/activate

# Проверьте интеграцию (опционально)
python test_gemini_integration.py

# Запустите сервер
uvicorn main:app --reload
```

**Готово!** 🎉 Теперь Gemini используется автоматически для всех AI запросов.

---

## 🎯 Оптимальная конфигурация

Для максимальной эффективности добавьте в `.env`:

```bash
# Приоритет: сначала бесплатный Gemini
AI_PROVIDER_PRIORITY=gemini,groq,openai

# Модели (используйте Flash для экономии лимитов)
GEMINI_ENHANCEMENT_MODEL=gemini-2.0-flash-exp    # 250 запросов/день
GEMINI_GENERATION_MODEL=gemini-2.0-flash-exp     # Или gemini-2.5-pro для лучшего качества (50/день)
GEMINI_ASSISTANT_MODEL=gemini-2.0-flash-exp      # 250 запросов/день

# Проактивные лимиты (переключение до исчерпания)
GEMINI_PRO_LIMIT=45       # Из 50
GEMINI_FLASH_LIMIT=230    # Из 250
```

---

## 📊 Что происходит автоматически

1. **Выбор оптимальной модели** для каждой задачи:
   - Enhancement (Stage 1) → Flash (быстро)
   - Generation (Stage 2) → Pro или Flash (качество)
   - AI Assistant → Flash (скорость + качество)

2. **Проактивное переключение** при приближении к лимиту:
   - При 45/50 запросов Pro → переключение на Groq
   - При 230/250 запросов Flash → переключение на Groq

3. **Автоматический fallback** при ошибках:
   - Gemini → Groq → OpenAI

---

## ✅ Проверка работы

### В логах сервера увидите:

```
✅ Initialized Gemini API client
✅ Настроены AI провайдеры (в порядке приоритета): gemini, groq, openai
Trying GEMINI with model gemini-2.0-flash-exp
✅ Successfully got response from GEMINI
```

### Если лимит исчерпан:

```
⏩ Skipping GEMINI - approaching rate limit
Trying GROQ with model llama-3.3-70b-versatile
✅ Successfully got response from GROQ
```

---

## 💡 Зачем это нужно?

| Без Gemini | С Gemini |
|------------|----------|
| ❌ Платные API (OpenAI) | ✅ **Бесплатно** 250-300 запросов/день |
| ⚠️ Риск исчерпания квоты | ✅ Автоматический **fallback** на другие провайдеры |
| 🐌 Одна модель для всех задач | ✅ **Оптимальная модель** для каждой задачи |
| 😰 Внезапные ошибки при лимите | ✅ **Проактивное** переключение до лимита |

---

## 🆘 Помощь

**Проблемы с ключом?**
- Убедитесь, что ключ начинается с `AIza`
- Проверьте `.env` файл в папке `backend/`

**Тесты не проходят?**
```bash
# Проверьте установку библиотеки
pip install google-generativeai==0.8.5

# Запустите тесты
python test_gemini_integration.py
```

**Нужна детальная документация?**
Читайте [GEMINI_INTEGRATION.md](GEMINI_INTEGRATION.md)

---

**Всё! Начинайте использовать 🚀**
