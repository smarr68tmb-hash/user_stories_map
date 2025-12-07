# Backend - AI User Story Mapper

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваши AI ключи
```

Или установите переменные окружения:
```bash
# Приоритет по умолчанию: gemini → groq → perplexity → openai
export GEMINI_API_KEY=your-gemini-key-here       # приоритетный
export GROQ_API_KEY=gsk-your-key-here            # fallback 1
export PERPLEXITY_API_KEY=pplx-your-key-here     # fallback 2
export OPENAI_API_KEY=sk-your-key-here           # fallback 3

# Явная настройка приоритета (опционально)
# export AI_PROVIDER_PRIORITY="gemini,groq,perplexity,openai"
```

**Поддерживаются четыре провайдера с автоматическим fallback:**
- **Gemini** (приоритет по умолчанию) — быстрый и дешёвый
- **Groq** — fallback 1
- **Perplexity** — fallback 2
- **OpenAI** — fallback 3

Система автоматически переключается между провайдерами при ошибках или исчерпании лимитов.

4. Запустите сервер:
```bash
python main.py
```

Сервер будет доступен на http://127.0.0.1:8000

API документация: http://127.0.0.1:8000/docs

## Тестирование

Запустите тесты:
```bash
pytest test_main.py -v
```

## Переменные окружения

### API Ключи (хотя бы один обязателен)
- `GEMINI_API_KEY` - ключ Gemini (приоритет по умолчанию)
- `GROQ_API_KEY` - ключ Groq (fallback 1)
- `PERPLEXITY_API_KEY` - ключ Perplexity (fallback 2)
- `OPENAI_API_KEY` - ключ OpenAI (fallback 3)

### Настройки провайдеров
- `AI_PROVIDER_PRIORITY` - Порядок приоритета (по умолчанию: `gemini,groq,perplexity,openai`)
- `API_PROVIDER` - Явное указание основного провайдера (опционально, для обратной совместимости)

### Модели (опционально, есть умолчания)
- `GEMINI_MODEL` / `GEMINI_ENHANCEMENT_MODEL`
- `GROQ_MODEL` / `GROQ_ENHANCEMENT_MODEL`
- `PERPLEXITY_MODEL` / `PERPLEXITY_ENHANCEMENT_MODEL`
- `OPENAI_MODEL` / `OPENAI_ENHANCEMENT_MODEL`
- `ENHANCEMENT_MODEL` - общая модель для Stage 1
- `API_MODEL` - общая модель для Stage 2
- `API_TEMPERATURE` - Температура для генерации (по умолчанию: 0.7)
- `DATABASE_URL` - URL базы данных (по умолчанию: sqlite:///./usm.db)
- `ALLOWED_ORIGINS` - Разрешенные домены для CORS (через запятую)
- `LOG_LEVEL` - Уровень логирования (по умолчанию: INFO)

## Безопасность

⚠️ **Важно для production:**
- Настройте `ALLOWED_ORIGINS` на конкретные домены
- Не храните `.env` файлы в репозитории
- Используйте PostgreSQL вместо SQLite для production
- Настройте HTTPS
