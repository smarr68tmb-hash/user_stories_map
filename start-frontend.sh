#!/bin/bash

set -e  # Остановка при ошибках

cd "$(dirname "$0")/frontend"

echo "🔧 Настройка frontend окружения..."

# Проверка Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не найден. Установите Node.js 18+"
    echo "   macOS: brew install node"
    echo "   или скачайте с https://nodejs.org"
    exit 1
fi

# Проверка npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm не найден. Установите npm"
    exit 1
fi

# Проверка версии Node.js
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Рекомендуется Node.js 18+. Текущая версия: $(node -v)"
fi

# Проверка node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Устанавливаю зависимости (это может занять несколько минут)..."
    npm install
else
    echo "✅ Зависимости уже установлены"
fi

# Запуск dev сервера
echo ""
echo "🚀 Запускаю frontend на http://localhost:5173"
echo ""
npm run dev

