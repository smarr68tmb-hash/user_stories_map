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
# Отредактируйте .env и добавьте ваш API ключ
```

Или установите переменные окружения:
```bash
# Для Groq (рекомендуется - бесплатный и быстрый)
export GROQ_API_KEY=gsk-your-key-here

# Для Perplexity (резервный)
export PERPLEXITY_API_KEY=pplx-your-key-here

# Для OpenAI (резервный)
export OPENAI_API_KEY=sk-your-key-here
```

**Поддерживаются три провайдера с автоматическим fallback:**
- **Groq** (приоритет 1) - ключ вида `gsk_...` - бесплатный, быстрый
- **Perplexity** (приоритет 2) - ключ вида `pplx-...` - резервный
- **OpenAI** (приоритет 3) - ключ вида `sk-...` - резервный

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
- `GROQ_API_KEY` - API ключ Groq (формат: `gsk_...`) - **рекомендуется для начала**
- `PERPLEXITY_API_KEY` - API ключ Perplexity (формат: `pplx-...`)
- `OPENAI_API_KEY` - API ключ OpenAI (формат: `sk-...`)

### Настройки провайдеров
- `AI_PROVIDER_PRIORITY` - Порядок приоритета провайдеров (по умолчанию: `groq,perplexity,openai`)
- `API_PROVIDER` - Явное указание основного провайдера (опционально, для обратной совместимости)

### Модели (опционально, есть умолчания)
- `GROQ_MODEL` - Модель Groq для генерации (по умолчанию: `llama-3.3-70b-versatile`)
- `GROQ_ENHANCEMENT_MODEL` - Модель Groq для предобработки (по умолчанию: `llama-3.1-8b-instant`)
- `PERPLEXITY_MODEL` - Модель Perplexity (по умолчанию: `llama-3.1-sonar-large-128k-online`)
- `PERPLEXITY_ENHANCEMENT_MODEL` - Модель Perplexity для предобработки
- `OPENAI_MODEL` - Модель OpenAI (по умолчанию: `gpt-4o`)
- `OPENAI_ENHANCEMENT_MODEL` - Модель OpenAI для предобработки
- `API_MODEL` - Общая модель (используется если не указана модель для провайдера)
- `ENHANCEMENT_MODEL` - Общая модель для предобработки
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
