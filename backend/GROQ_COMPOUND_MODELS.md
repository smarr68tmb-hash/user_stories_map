# Groq Compound Models - Документация

## Обзор

Добавлена поддержка новых моделей Groq Compound и Compound Mini в проект.

## Доступные модели

### `groq/compound`
- **Скорость**: 450 токенов/сек
- **Context window**: 131,072 токенов
- **Max completion**: 8,192 токенов
- **Rate limits**: 200K TPM, 200 RPM (Developer Plan)
- **Архитектура**: Система, объединяющая несколько моделей (GPT-OSS 120B, Llama 3.3 70B) с инструментами
- **Особенности**: Поддержка веб-поиска и выполнения кода

### `groq/compound-mini`
- **Скорость**: 450 токенов/сек
- **Context window**: 131,072 токенов
- **Max completion**: 8,192 токенов
- **Rate limits**: 200K TPM, 200 RPM (Developer Plan)
- **Архитектура**: Облегченная версия Compound системы
- **Особенности**: Быстрая обработка с поддержкой инструментов

## Использование

### Через переменные окружения

```bash
# Использовать Compound для generation (основная генерация карт)
export GROQ_MODEL="groq/compound"

# Использовать Compound Mini для enhancement (улучшение требований)
export GROQ_ENHANCEMENT_MODEL="groq/compound-mini"

# Или использовать оба
export GROQ_MODEL="groq/compound"
export GROQ_ENHANCEMENT_MODEL="groq/compound-mini"
```

### Сравнение с текущими моделями

**Текущие модели по умолчанию:**
- Generation: `llama-3.3-70b-versatile`
- Enhancement: `llama-3.1-8b-instant`

**Преимущества Compound моделей:**
- ✅ Высокая скорость (450 T/SEC vs ~330 T/SEC для Llama 3.3 70B)
- ✅ Большой context window (131K vs 8K-32K для Llama)
- ✅ Интеграция с инструментами (веб-поиск, выполнение кода)
- ✅ Хорошие rate limits (200K TPM, 200 RPM)

**Когда использовать:**
- Для задач, требующих актуальной информации (веб-поиск)
- Для задач с большим контекстом (>32K токенов)
- Когда важна скорость ответа
- Для задач, требующих вычислений или работы с кодом

## Примеры конфигурации

### Вариант 1: Только Compound для generation
```bash
export GROQ_API_KEY="gsk-your-key-here"
export GROQ_MODEL="groq/compound"
# Enhancement будет использовать llama-3.1-8b-instant (по умолчанию)
```

### Вариант 2: Compound для всех задач
```bash
export GROQ_API_KEY="gsk-your-key-here"
export GROQ_MODEL="groq/compound"
export GROQ_ENHANCEMENT_MODEL="groq/compound-mini"
```

### Вариант 3: Compound Mini для быстрого enhancement
```bash
export GROQ_API_KEY="gsk-your-key-here"
export GROQ_ENHANCEMENT_MODEL="groq/compound-mini"
# Generation будет использовать llama-3.3-70b-versatile (по умолчанию)
```

## Тестирование

После настройки переменных окружения, перезапустите backend:

```bash
cd backend
python main.py
```

Модели будут автоматически использоваться через fallback механизм, если Groq находится в приоритете провайдеров.

## Примечания

- Compound модели требуют тот же API ключ Groq (`GROQ_API_KEY`)
- Модели используют тот же endpoint: `https://api.groq.com/openai/v1`
- Fallback механизм работает автоматически - если Compound недоступен, система переключится на другие провайдеры
- Рекомендуется протестировать качество ответов на ваших конкретных задачах перед полным переходом

## Сравнение качества

**Llama 3.3 70B Versatile** (текущая модель по умолчанию):
- MMLU: 86.0%
- HumanEval: 88.4% pass@1
- MATH: 77.0%

**Groq Compound:**
- Использует Llama 3.3 70B как компонент системы
- Дополнительные возможности через инструменты
- Прямых бенчмарков пока нет - рекомендуется тестирование на ваших задачах

