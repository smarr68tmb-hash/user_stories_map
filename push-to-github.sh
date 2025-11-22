#!/bin/bash

# Скрипт для загрузки проекта в GitHub

set -e  # Остановка при ошибках

echo "🚀 Загрузка проекта в GitHub"
echo ""

# Проверка незакоммиченных изменений
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Обнаружены незакоммиченные изменения!"
    git status --short
    echo ""
    read -p "Закоммитить их сейчас? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        read -p "Сообщение коммита (Enter для 'Auto commit before push'): " MSG
        if [ -z "$MSG" ]; then
            MSG="Auto commit before push"
        fi
        git commit -m "$MSG"
        echo "✅ Изменения закоммичены"
    else
        echo "❌ Отменено. Закоммитьте изменения вручную перед push."
        exit 1
    fi
fi

# Проверка наличия remote
if git remote | grep -q "origin"; then
    echo "✅ Remote 'origin' уже настроен"
    git remote -v
    echo ""
    read -p "Хотите обновить URL? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Введите URL вашего GitHub репозитория: " REPO_URL
        git remote set-url origin "$REPO_URL"
        echo "✅ URL обновлен"
    fi
else
    echo "📝 Настройка remote репозитория"
    read -p "Введите URL вашего GitHub репозитория (например: https://github.com/username/repo.git): " REPO_URL
    
    if [ -z "$REPO_URL" ]; then
        echo "❌ URL не может быть пустым"
        exit 1
    fi
    
    git remote add origin "$REPO_URL"
    echo "✅ Remote добавлен: $REPO_URL"
fi

echo ""
echo "📤 Отправка кода в GitHub..."

# Определяем имя ветки
BRANCH=$(git branch --show-current)

# Проверка конфликтов перед push
echo "🔍 Проверка синхронизации с удаленным репозиторием..."
git fetch origin "$BRANCH" 2>/dev/null || true

# Push в GitHub
if git push -u origin "$BRANCH"; then
    echo ""
    echo "✅ Успешно загружено в GitHub!"
    echo "🌐 Ваш репозиторий: $(git remote get-url origin)"
    echo ""
    echo "📊 Статистика последнего коммита:"
    git log -1 --stat --oneline
else
    echo ""
    echo "❌ Ошибка при загрузке. Возможные причины:"
    echo "   - Репозиторий не существует на GitHub"
    echo "   - Нет прав доступа"
    echo "   - Нужна аутентификация (используйте GitHub CLI или SSH ключи)"
    echo "   - Конфликт с удаленной веткой (используйте: git pull --rebase)"
    echo ""
    echo "💡 Создайте репозиторий на GitHub и повторите попытку"
    exit 1
fi

