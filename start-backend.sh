#!/bin/bash

cd "$(dirname "$0")/backend"

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создаю виртуальное окружение..."
    python3 -m venv venv
fi

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
echo "Устанавливаю зависимости..."
pip install -r requirements.txt

# Проверка API ключа
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  ВНИМАНИЕ: OPENAI_API_KEY не установлен!"
    echo "Установите переменную окружения:"
    echo "export OPENAI_API_KEY=sk-your-key-here"
    echo ""
    echo "Запускаю сервер без API ключа (для тестирования структуры)..."
fi

# Запуск сервера
echo "Запускаю backend сервер на http://127.0.0.1:8000"
python main.py

