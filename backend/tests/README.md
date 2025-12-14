# Backend Tests - USM Service

## 🎯 Quick Start

```bash
# Быстрый запуск всех критичных тестов (standalone)
python3 tests/run_tests_standalone.py

# Полный запуск через pytest (если conftest настроен)
pytest tests/test_ai_service.py -v
pytest tests/test_auth_service.py -v
pytest tests/test_validation_service.py -v
pytest tests/test_similarity_service.py -v
pytest tests/test_streaming.py -v
```

## 📦 Тестовые файлы

### 🔴 Критичные сервисы (ВЫСОКИЙ ПРИОРИТЕТ)

#### 1. `test_ai_service.py` - 40+ тестов
**Покрывает:** `services/ai_service.py`

Тестирует:
- ✅ **RateLimitTracker** - Отслеживание и проактивное переключение при приближении к лимитам
- ✅ **Fallback mechanism** - Автоматическое переключение между провайдерами (Gemini → Groq → Perplexity → OpenAI)
- ✅ **JSON parsing** - Парсинг ответов от AI с очисткой markdown (```json ... ```)
- ✅ **Error handling** - RateLimitError, APIConnectionError, APITimeoutError, APIError
- ✅ **Redis caching** - Cache hit/miss, TTL, cache key generation
- ✅ **Model selection** - Разные модели для enhancement, generation, assistant
- ✅ **Gemini API** - Специфика Gemini (safety settings, content blocking)

**Ключевые тесты:**
```python
def test_fallback_gemini_to_groq()  # Fallback при rate limit
def test_parse_json_with_markdown()  # Парсинг ```json ... ```
def test_cache_hit_skips_ai_request()  # Redis caching
def test_should_skip_provider_approaching_limit()  # Проактивный rate limit
```

#### 2. `test_auth_service.py` - 30+ тестов
**Покрывает:** `services/auth_service.py`

Тестирует:
- ✅ **Password hashing** - bcrypt с автоматической солью
- ✅ **JWT tokens** - Creation, validation, expiration
- ✅ **Refresh tokens** - Generation, storage в БД, TTL
- ✅ **Security** - Timing attack resistance, password complexity, invalid token rejection
- ✅ **Edge cases** - Unicode в паролях, пустые поля, длинные email

**Ключевые тесты:**
```python
def test_password_hash_not_reversible()  # Bcrypt необратимость
def test_decode_expired_token()  # JWT expiration
def test_timing_attack_resistance()  # Constant-time comparison
def test_same_password_different_hashes()  # Bcrypt salt
```

#### 3. `test_validation_service.py` - 30+ тестов
**Покрывает:** `services/validation_service.py`

Тестирует:
- ✅ **Score calculation** - Формула расчета overall_score (0-100)
- ✅ **Issue detection** - EMPTY_ACTIVITY, EMPTY_TASK, MISSING_DESCRIPTION, MISSING_CRITERIA
- ✅ **Severity penalties** - ERROR (-20), WARNING (-5), INFO (-1)
- ✅ **Quality checks** - Описания, acceptance criteria, короткие названия
- ✅ **Duplicate detection** - Case-insensitive поиск дубликатов
- ✅ **Release balance** - Неравномерное распределение по релизам
- ✅ **Recommendations** - Генерация рекомендаций на основе проблем

**Ключевые тесты:**
```python
def test_perfect_score_no_issues()  # Score = 100 без проблем
def test_error_deducts_20_points()  # ERROR penalty
def test_duplicate_titles_warning()  # Дубликаты
def test_recommendations_for_large_mvp()  # MVP > 15 историй
```

#### 4. `test_similarity_service.py` - 30+ тестов
**Покрывает:** `services/similarity_service.py`

Тестирует:
- ✅ **TF-IDF vectorization** - С русскими стоп-словами
- ✅ **Cosine similarity** - Расчет матрицы схожести
- ✅ **Jaccard fallback** - Алгоритм без sklearn
- ✅ **Text preprocessing** - Lowercase, удаление спецсимволов, множественных пробелов
- ✅ **Group finding** - Группировка duplicates (>0.9) vs similar (0.7-0.9)
- ✅ **Russian stop words** - Игнорирование стоп-слов
- ✅ **Edge cases** - Пустые тексты, только стоп-слова, unicode/emoji

**Ключевые тесты:**
```python
def test_tfidf_identical_texts()  # Similarity = 1.0
def test_fallback_removes_stop_words()  # Русские стоп-слова
def test_analyze_finds_duplicates()  # Обнаружение дубликатов
def test_find_groups_sorts_duplicates_first()  # Сортировка групп
```

### 🟢 Phase 1 - Streaming

#### 5. `test_streaming.py` - 14 тестов
**Покрывает:** `services/streaming_service.py`

Тестирует:
- ✅ SSE event format
- ✅ Event sequence validation
- ✅ Progress tracking (0% → 100%)
- ✅ Analysis event data
- ✅ Complete event data
- ✅ Error handling
- ✅ Saving to DB

## 📊 Статистика

| Сервис | Тесты | Приоритет | Статус |
|--------|-------|-----------|--------|
| ai_service.py | 40+ | 🔴 КРИТИЧНО | ✅ ПОКРЫТ |
| auth_service.py | 30+ | 🔴 КРИТИЧНО | ✅ ПОКРЫТ |
| validation_service.py | 30+ | 🟡 ВАЖНО | ✅ ПОКРЫТ |
| similarity_service.py | 30+ | 🟡 ВАЖНО | ✅ ПОКРЫТ |
| streaming_service.py | 14 | 🟢 СРЕДНЕ | ✅ ПОКРЫТ |

**Всего:** **140+ backend тестов**

## 🚀 Запуск тестов

### Standalone runner (рекомендуется)
```bash
python3 tests/run_tests_standalone.py
```

Вывод:
```
======================================================================
🧪 STANDALONE TEST RUNNER - Critical Services
======================================================================

📦 Testing Auth Service...
  ✅ Password hashing (bcrypt)
  ✅ Password salt randomization
  ✅ JWT token creation
  ✅ JWT token decode
  ✅ Invalid token rejection
🎉 Auth Service: 5/5 tests PASSED

📦 Testing Validation Service...
  ✅ Perfect score (100)
  ✅ ERROR penalty (-20 points)
  ✅ WARNING penalty (-5 points)
  ✅ INFO penalty (-1 point)
  ✅ Score bounds (>= 0)
🎉 Validation Service: 5/5 tests PASSED

...

🎯 Total: 20/20 tests PASSED
```

### Pytest (полный набор)
```bash
# Все тесты
pytest tests/ -v

# Конкретный файл
pytest tests/test_ai_service.py -v

# С coverage
pytest tests/test_ai_service.py --cov=services.ai_service --cov-report=html
```

## 🔧 Troubleshooting

### ImportError из-за Python 3.9
**Проблема:** `TypeError: unsupported operand type(s) for |: 'DeclarativeMeta' and 'NoneType'`

**Решение:** Используйте standalone runner:
```bash
python3 tests/run_tests_standalone.py
```

Или обновите Python до 3.10+:
```bash
brew install python@3.10
```

### Pytest conftest errors
**Проблема:** conftest.py импортирует main.py, который имеет проблемы с типами в Python 3.9

**Решение:** Временно используйте standalone runner или исправьте `dependencies.py:81` на:
```python
from typing import Optional
def get_current_user_optional(...) -> Optional[User]:
```

## 📝 Добавление новых тестов

### 1. Создайте тестовый файл
```bash
touch tests/test_new_service.py
```

### 2. Импортируйте необходимые модули
```python
import pytest
from unittest.mock import Mock, patch
from services.new_service import my_function
```

### 3. Напишите тесты
```python
def test_my_function_success():
    """Тест успешного выполнения"""
    result = my_function("input")
    assert result == "expected"

def test_my_function_error():
    """Тест обработки ошибок"""
    with pytest.raises(ValueError):
        my_function(None)
```

### 4. Запустите тесты
```bash
pytest tests/test_new_service.py -v
```

## 🎯 Best Practices

1. **Mock external dependencies** - Redis, AI API, Database
2. **Test edge cases** - Empty input, None, unicode, очень длинные строки
3. **Test error handling** - Все except блоки должны быть протестированы
4. **Test security** - Password strength, timing attacks, token validation
5. **Use fixtures** - Для переиспользования mock объектов
6. **Clear test names** - `test_what_when_expected()`
7. **One assertion per test** - Или логически связанные assertions

## 📚 Ресурсы

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)

---

**Последнее обновление:** 2025-12-14
**Создано:** AI Assistant (Claude Code)
