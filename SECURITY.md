# Security Guidelines

## Environment Variables

### ⚠️ НИКОГДА НЕ КОММИТЬТЕ .env ФАЙЛЫ

`.env` файлы содержат чувствительную информацию (API ключи, секретные ключи, пароли БД) и **НЕ ДОЛЖНЫ** попадать в git.

### Правильная настройка

1. **Backend**:
   ```bash
   cd backend
   cp .env.example .env
   # Отредактируйте .env своими реальными ключами
   ```

2. **Frontend**:
   ```bash
   cd frontend
   cp .env.example .env
   # Отредактируйте .env если нужно изменить URL backend
   ```

3. **Проверка**: Убедитесь что `.env` в `.gitignore`:
   ```bash
   git check-ignore backend/.env frontend/.env
   # Должно показать что файлы игнорируются
   ```

### Что делать если случайно закоммитили секреты

Если вы случайно закоммитили `.env` файл с секретами:

1. **НЕ ДЕЛАЙТЕ** просто `git rm .env` - секреты останутся в истории!

2. **Удалите из истории git**:
   ```bash
   # Удалить файл из всей истории
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch backend/.env' \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (ВНИМАНИЕ: перезапишет историю на remote)
   git push origin --force --all
   ```

3. **ПОМЕНЯЙТЕ ВСЕ СЕКРЕТЫ** которые были в закоммиченном файле:
   - JWT_SECRET_KEY
   - OPENAI_API_KEY / GROQ_API_KEY / PERPLEXITY_API_KEY
   - DATABASE_URL (пароль БД)
   - Любые другие ключи

4. **Сообщите команде** если это shared репозиторий

### Production секреты

В production используйте:
- **Environment variables** вашего хостинга (Render, Heroku, AWS, etc.)
- **Secret managers** (AWS Secrets Manager, HashiCorp Vault)
- **НИКОГДА** не храните production секреты в коде или .env файлах

### Проверка безопасности зависимостей

Регулярно запускайте:

```bash
# Backend
cd backend
safety check -r requirements.txt

# Frontend
cd frontend
npm audit
```

### Rate Limiting

В production убедитесь что:
- Rate limiting настроен корректно (см. `config.py`)
- CORS настроен только на ваши домены
- JWT секрет минимум 32 символа

### Reporting Security Issues

Если вы нашли уязвимость в коде:
1. **НЕ создавайте публичный issue**
2. Напишите напрямую мейнтейнеру
3. Опишите проблему и шаги для воспроизведения

---

**Последнее обновление**: 2025-12-02
