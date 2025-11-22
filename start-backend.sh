#!/bin/bash

set -e  # Остановка при ошибках

cd "$(dirname "$0")/backend"

echo "🔧 Настройка backend окружения..."

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+"
    exit 1
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создаю виртуальное окружение..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔌 Активирую виртуальное окружение..."
source venv/bin/activate

# Обновление pip
echo "⬆️  Обновляю pip..."
pip install --quiet --upgrade pip

# Установка зависимостей
echo "📚 Устанавливаю зависимости..."
pip install --quiet -r requirements.txt

# Загрузка .env файла, если он существует
if [ -f ".env" ]; then
    echo "📝 Загружаю переменные из .env файла..."
    set -a  # Автоматически экспортировать все переменные
    source .env
    set +a
fi

# Проверка API ключа
if [ -z "$OPENAI_API_KEY" ] && [ -z "$PERPLEXITY_API_KEY" ]; then
    echo ""
    echo "⚠️  ВНИМАНИЕ: API ключ не найден!"
    echo ""
    echo "Установите переменную окружения:"
    echo "  export OPENAI_API_KEY=sk-your-key-here  # для OpenAI"
    echo "  export OPENAI_API_KEY=pplx-your-key-here  # для Perplexity"
    echo ""
    echo "Или создайте файл .env в папке backend:"
    echo "  OPENAI_API_KEY=pplx-your-key-here"
    echo ""
    read -p "Продолжить без API ключа? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    echo "⚠️  Сервер запустится, но AI функции будут недоступны"
else
    # Определяем провайдера
    if [[ "$OPENAI_API_KEY" == pplx-* ]] || [[ "$PERPLEXITY_API_KEY" == pplx-* ]]; then
        echo "✅ Perplexity API ключ найден"
    elif [[ "$OPENAI_API_KEY" == sk-* ]]; then
        echo "✅ OpenAI API ключ найден"
    else
        echo "✅ API ключ найден (формат: ${OPENAI_API_KEY:0:10}...)"
    fi
fi

# Запуск сервера
echo ""
echo "🚀 Запускаю backend сервер на http://127.0.0.1:8000"
echo "📖 API документация: http://127.0.0.1:8000/docs"
echo ""
python main.py

