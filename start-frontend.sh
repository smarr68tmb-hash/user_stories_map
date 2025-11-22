#!/bin/bash

cd "$(dirname "$0")/frontend"

# Проверка node_modules
if [ ! -d "node_modules" ]; then
    echo "Устанавливаю зависимости..."
    npm install
fi

# Запуск dev сервера
echo "Запускаю frontend на http://localhost:5173"
npm run dev

