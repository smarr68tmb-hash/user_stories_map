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

Или установите переменную окружения:
```bash
# Для OpenAI
export OPENAI_API_KEY=sk-your-key-here

# Или для Perplexity
export OPENAI_API_KEY=pplx-your-key-here
# или
export PERPLEXITY_API_KEY=pplx-your-key-here
```

**Поддерживаются два провайдера:**
- **OpenAI** - ключ вида `sk-...`
- **Perplexity** - ключ вида `pplx-...` (автоопределяется)

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

- `OPENAI_API_KEY` - API ключ (обязательно, поддерживает OpenAI и Perplexity)
  - OpenAI: ключ вида `sk-...`
  - Perplexity: ключ вида `pplx-...` (автоопределяется)
- `PERPLEXITY_API_KEY` - Альтернативный способ указать Perplexity ключ
- `API_PROVIDER` - Явное указание провайдера: `"openai"` или `"perplexity"` (опционально)
- `API_MODEL` - Модель для использования:
  - OpenAI: `gpt-4o` (по умолчанию)
  - Perplexity: `llama-3.1-sonar-large-128k-online` (рекомендуется)
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
