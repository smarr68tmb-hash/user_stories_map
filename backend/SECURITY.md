# Безопасность USM-Service

## ✅ Реализованные меры защиты

### 1. Хеширование паролей
- Пароли хранятся в БД только в виде bcrypt-хешей
- Файл: `services/auth_service.py`

### 2. Маскировка чувствительных данных в логах
- Все пароли, токены и API-ключи автоматически маскируются
- JWT токены заменяются на `[MASKED_JWT]`
- Пароли заменяются на `[MASKED]`
- Файл: `utils/security.py` → `SecureLoggingMiddleware`

### 3. Валидация силы пароля
- Минимум 8 символов
- Минимум 1 заглавная буква
- Минимум 1 строчная буква  
- Минимум 1 цифра
- Файл: `schemas/user.py`

### 4. Rate Limiting
- Регистрация: 5 запросов в минуту
- Логин: 10 запросов в минуту
- Обновление токена: 10 запросов в минуту
- Файл: `api/auth.py`

### 5. JWT токены
- Access token: 30 минут TTL
- Refresh token: 7 дней TTL + ротация при каждом обновлении
- Токены подписаны секретным ключом (HS256)

---

## ⚠️ Обязательно для Production

### HTTPS (критически важно!)
Без HTTPS все данные (пароли, токены) передаются открытым текстом!

**Настройка с nginx:**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Редирект HTTP → HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### JWT Secret Key
Обязательно установите уникальный ключ минимум 32 символа:
```bash
export JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### Переменные окружения
```bash
ENVIRONMENT=production
JWT_SECRET_KEY=your-very-secure-random-key-at-least-32-chars
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

---

## 🔧 Дополнительные рекомендации

### HttpOnly Cookies для токенов (опционально)
Для дополнительной защиты от XSS можно хранить токены в httpOnly cookies вместо localStorage:

```python
# Пример изменений в api/auth.py
from fastapi.responses import JSONResponse

@router.post("/token")
def login(...):
    # ... создание токенов ...
    
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Только HTTPS
        samesite="strict",
        max_age=1800  # 30 минут
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=604800  # 7 дней
    )
    return response
```

### Content Security Policy
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';";
```

### CORS в production
Ограничьте `ALLOWED_ORIGINS` только вашими доменами:
```bash
ALLOWED_ORIGINS=https://yourdomain.com
```

---

## 📋 Чеклист перед деплоем

- [ ] HTTPS настроен и работает
- [ ] JWT_SECRET_KEY изменён на уникальный
- [ ] ENVIRONMENT=production
- [ ] DATABASE_URL указывает на PostgreSQL (не SQLite)
- [ ] ALLOWED_ORIGINS содержит только ваши домены
- [ ] Логи не содержат чувствительных данных (проверить!)
- [ ] Rate limiting работает
- [ ] Sentry настроен для мониторинга ошибок

