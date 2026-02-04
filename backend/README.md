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
# Приоритет по умолчанию: gemini → groq → openai
export GEMINI_API_KEY=your-gemini-key-here       # приоритетный
export GROQ_API_KEY=gsk-your-key-here            # fallback 1
export OPENAI_API_KEY=sk-your-key-here           # fallback 2

# Явная настройка приоритета (опционально)
# export AI_PROVIDER_PRIORITY="gemini,groq,openai"

# Использование новых Groq Compound моделей (опционально)
# export GROQ_MODEL="groq/compound"              # для generation (450 T/SEC, 131K context)
# export GROQ_ENHANCEMENT_MODEL="groq/compound-mini"  # для enhancement
```

**Поддерживаются провайдеры с автоматическим fallback:**
- **Gemini** (приоритет по умолчанию) — быстрый и дешёвый
- **Groq** — fallback 1
- **OpenAI** — fallback 2

Система автоматически переключается между провайдерами при ошибках или исчерпании лимитов.

4. Запустите сервер:
```bash
python main.py
```

Сервер будет доступен на http://127.0.0.1:8000

API документация: http://127.0.0.1:8000/docs

## Тестирование

### Unit тесты
Запустите тесты:
```bash
pytest test_main.py -v
```

### Тестирование Groq моделей
Для быстрого тестирования Groq моделей (включая новые Compound модели):
```bash
# Тест с текущими моделями
python test_groq_compound.py

# Сравнение всех моделей
python test_groq_compound.py --compare
```

Подробнее см. [GROQ_COMPOUND_MODELS.md](GROQ_COMPOUND_MODELS.md)

## Переменные окружения

### API Ключи (хотя бы один обязателен)
- `GEMINI_API_KEY` - ключ Gemini (приоритет по умолчанию)
- `GROQ_API_KEY` - ключ Groq (fallback 1)
- `OPENAI_API_KEY` - ключ OpenAI (fallback 2)

### Настройки провайдеров
- `AI_PROVIDER_PRIORITY` - Порядок приоритета (по умолчанию: `gemini,groq,openai`)
- `API_PROVIDER` - Явное указание основного провайдера (опционально, для обратной совместимости)

### Модели (опционально, есть умолчания)
- `GEMINI_MODEL` / `GEMINI_ENHANCEMENT_MODEL`
- `GROQ_MODEL` / `GROQ_ENHANCEMENT_MODEL`
  - По умолчанию: `llama-3.3-70b-versatile` (generation), `llama-3.1-8b-instant` (enhancement)
  - Новые модели Compound: `groq/compound` или `groq/compound-mini` (450 T/SEC, 131K context)
- `OPENAI_MODEL` / `OPENAI_ENHANCEMENT_MODEL`
- `ENHANCEMENT_MODEL` - общая модель для Stage 1
- `API_MODEL` - общая модель для Stage 2
- `API_TEMPERATURE` - Температура для генерации (по умолчанию: 0.7)
- `DATABASE_URL` - URL базы данных (по умолчанию: sqlite:///./usm.db)
- `ALLOWED_ORIGINS` - Разрешенные домены для CORS (через запятую)
- `LOG_LEVEL` - Уровень логирования (по умолчанию: INFO)

## Архитектура AI провайдеров

Система использует паттерн Strategy для работы с различными AI провайдерами:

- **Базовый класс `AIProvider`** — абстрактный интерфейс для всех провайдеров
- **Конкретные реализации:**
  - `GeminiProvider`, `GeminiProProvider`, `GeminiFlashProvider` — для Google Gemini
  - `GroqProvider`, `OpenAIProvider` — для OpenAI-совместимых API
- **`ProviderRegistry`** — централизованный реестр всех доступных провайдеров
- **Автоматический fallback** — система автоматически переключается между провайдерами при ошибках

Преимущества:
- Легко добавлять новые провайдеры (достаточно создать новый класс)
- Единая обработка ошибок для всех провайдеров
- Упрощенная поддержка и тестирование

## Безопасность

⚠️ **Важно для production:**
- Настройте `ALLOWED_ORIGINS` на конкретные домены
- Не храните `.env` файлы в репозитории
- Используйте PostgreSQL вместо SQLite для production
- Настройте HTTPS
