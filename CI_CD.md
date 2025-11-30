# CI/CD Pipeline Documentation

## Обзор

Проект использует GitHub Actions для автоматической проверки кода при каждом push и Pull Request.

## Структура CI/CD

### 1. Backend Tests (`test-backend`)

**Что делает:**
- Запускает все тесты из `backend/test_main.py`
- Проверяет работу на Python 3.9, 3.10, 3.11
- Проверяет импорты модулей

**Когда запускается:** При каждом push/PR

**Время выполнения:** ~2-3 минуты

**Что проверяется:**
- ✅ Все unit тесты проходят
- ✅ Нет ошибок импорта
- ✅ Совместимость с разными версиями Python

### 2. Backend Linting (`lint-backend`)

**Что делает:**
- Проверяет форматирование кода с Black
- Проверяет стиль кода с flake8
- Не блокирует merge (только предупреждения)

**Когда запускается:** При каждом push/PR

**Время выполнения:** ~1 минута

**Что проверяется:**
- ✅ Форматирование кода соответствует стандартам
- ✅ Нет критичных ошибок стиля
- ✅ Сложность функций в пределах нормы

### 3. Frontend Build (`build-frontend`)

**Что делает:**
- Устанавливает зависимости (npm ci)
- Собирает production версию (npm run build)
- Проверяет что сборка успешна

**Когда запускается:** При каждом push/PR

**Время выполнения:** ~2-3 минуты

**Что проверяется:**
- ✅ Frontend компилируется без ошибок
- ✅ Создается директория `dist/`
- ✅ Нет ошибок TypeScript/JavaScript

### 4. Database Migrations Check (`check-migrations`)

**Что делает:**
- Проверяет валидность Alembic миграций
- Убеждается что миграции синтаксически корректны

**Когда запускается:** При каждом push/PR

**Время выполнения:** ~30 секунд

**Что проверяется:**
- ✅ Миграции валидны
- ✅ Нет синтаксических ошибок в миграциях

### 5. Security Check (`security-check`)

**Что делает:**
- Проверяет Python зависимости на уязвимости (safety)
- Проверяет Node.js зависимости на уязвимости (npm audit)
- Не блокирует merge (только предупреждения)

**Когда запускается:** При каждом push/PR

**Время выполнения:** ~1-2 минуты

**Что проверяется:**
- ✅ Нет критичных уязвимостей в зависимостях
- ✅ Предупреждения о потенциальных проблемах

## Как использовать

### Локальный запуск проверок

Перед созданием PR рекомендуется запустить проверки локально:

```bash
# Backend тесты
cd backend
pytest test_main.py -v

# Проверка импортов
python -c "from main import app"

# Линтинг (если установлен)
pip install black flake8
black --check .
flake8 .

# Frontend сборка
cd frontend
npm ci
npm run build
```

### Просмотр результатов CI/CD

1. Перейдите на вкладку **Actions** в GitHub репозитории
2. Выберите нужный workflow run
3. Просмотрите результаты каждого job

### Если CI/CD упал

**Backend тесты упали:**
1. Запустите тесты локально: `pytest test_main.py -v`
2. Исправьте ошибки
3. Запушите изменения

**Frontend сборка упала:**
1. Проверьте локально: `cd frontend && npm run build`
2. Исправьте ошибки компиляции
3. Запушите изменения

**Линтинг упал:**
1. Установите Black: `pip install black`
2. Отформатируйте код: `black .`
3. Запушите изменения

## Настройка

### Переменные окружения для тестов

CI/CD использует тестовые переменные окружения:
- `DATABASE_URL`: `sqlite:///:memory:` (тестовая БД в памяти)
- `JWT_SECRET_KEY`: тестовый ключ
- `ALLOWED_ORIGINS`: `http://localhost:5173`

### Исключение файлов из линтинга

Файлы исключаются через `.flake8`:
- `venv/`, `.venv/` - виртуальные окружения
- `__pycache__/` - кеш Python
- `alembic/versions/*.py` - миграции (автогенерируемые)

## Расширение CI/CD

### Добавление новых проверок

1. Добавьте новый job в `.github/workflows/ci.yml`:

```yaml
new-check:
  name: New Check
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run check
      run: echo "Your check here"
```

2. Commit и push изменения
3. GitHub Actions автоматически запустит новый job

### Добавление тестов

1. Добавьте тесты в `backend/test_main.py` или создайте новый файл `test_*.py`
2. CI/CD автоматически запустит их

### Добавление проверок frontend

1. Добавьте скрипты в `frontend/package.json`:
```json
{
  "scripts": {
    "test": "vitest",
    "lint": "eslint src/"
  }
}
```

2. Добавьте job в CI/CD для запуска этих скриптов

## Troubleshooting

### CI/CD не запускается

**Проблема:** Workflow не запускается при push

**Решение:**
1. Проверьте что файл `.github/workflows/ci.yml` существует
2. Проверьте синтаксис YAML файла
3. Убедитесь что ветка указана в `on.push.branches`

### Тесты падают в CI, но работают локально

**Проблема:** Тесты проходят локально, но падают в CI

**Возможные причины:**
1. Разные версии Python (проверьте `python-version` в CI)
2. Отсутствующие зависимости (проверьте `requirements.txt`)
3. Разные переменные окружения

**Решение:**
1. Запустите тесты в Docker контейнере для изоляции
2. Проверьте логи CI для деталей ошибки

### Медленный CI/CD

**Проблема:** CI/CD выполняется слишком долго

**Оптимизация:**
1. Используйте кеширование зависимостей (уже настроено)
2. Запускайте jobs параллельно (уже настроено)
3. Используйте `continue-on-error: true` для не-критичных проверок

## Статус бейдж

Добавьте бейдж статуса в README.md:

```markdown
[![CI](https://github.com/USERNAME/USM-SERVICE/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/USM-SERVICE/actions/workflows/ci.yml)
```

Замените:
- `USERNAME` - ваш GitHub username
- `USM-SERVICE` - название репозитория

## Полезные ссылки

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)

