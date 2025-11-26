"""
Утилиты безопасности - маскировка чувствительных данных
"""
import re
import logging
from typing import Any, Dict, List, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger(__name__)

# Список полей, которые нужно маскировать
SENSITIVE_FIELDS = [
    "password",
    "access_token", 
    "refresh_token",
    "token",
    "authorization",
    "api_key",
    "secret",
    "jwt",
    "bearer",
]

# Паттерны для маскировки в строках
SENSITIVE_PATTERNS = [
    # JWT токены (eyJ...)
    (r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[MASKED_JWT]'),
    # Bearer токены в заголовках
    (r'Bearer\s+[A-Za-z0-9_.-]+', 'Bearer [MASKED]'),
    # API ключи (sk-..., pplx-...)
    (r'(sk-|pplx-)[A-Za-z0-9]+', '[MASKED_API_KEY]'),
    # Refresh токены (base64-подобные длинные строки)
    (r'"refresh_token"\s*:\s*"[A-Za-z0-9_-]{20,}"', '"refresh_token": "[MASKED]"'),
    # Пароли в JSON
    (r'"password"\s*:\s*"[^"]*"', '"password": "[MASKED]"'),
]


def mask_sensitive_value(value: str) -> str:
    """Маскирует чувствительное значение, оставляя первые 4 символа"""
    if not value or len(value) < 8:
        return "****"
    return value[:4] + "****" + value[-2:] if len(value) > 10 else value[:4] + "****"


def mask_dict(data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    """Рекурсивно маскирует чувствительные поля в словаре"""
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Проверяем, является ли ключ чувствительным
        is_sensitive = any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS)
        
        if is_sensitive and isinstance(value, str):
            masked[key] = mask_sensitive_value(value)
        elif isinstance(value, dict):
            masked[key] = mask_dict(value, key)
        elif isinstance(value, list):
            masked[key] = [
                mask_dict(item, key) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    
    return masked


def mask_string(text: str) -> str:
    """Маскирует чувствительные данные в строке"""
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Маскирует чувствительные заголовки"""
    masked = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
            masked[key] = mask_sensitive_value(value) if value else value
        else:
            masked[key] = value
    return masked


class SecureLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для безопасного логирования запросов.
    Маскирует пароли, токены и другие чувствительные данные.
    
    ВАЖНО: НЕ читает тела запросов чтобы не ломать их обработку!
    Логируется только метод, путь и маскированные заголовки.
    """
    
    def __init__(self, app, log_bodies: bool = False):
        super().__init__(app)
        # log_bodies отключён принудительно - чтение body ломает запросы
        self.log_bodies = False  # Игнорируем параметр для безопасности
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Пропускаем OPTIONS запросы (CORS preflight) без логирования
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Логируем запрос с маскированными заголовками (только в DEBUG)
        if logger.isEnabledFor(logging.DEBUG):
            masked_headers = mask_headers(dict(request.headers))
            logger.debug(
                f"Request: {request.method} {request.url.path} "
                f"Headers: {masked_headers}"
            )
        
        # НЕ читаем body - это сломает обработку запроса!
        # Body можно прочитать только один раз в Starlette
        
        response = await call_next(request)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Response: {request.method} {request.url.path} "
                f"Status: {response.status_code}"
            )
        
        return response


def get_safe_log_message(message: str, data: Any = None) -> str:
    """
    Создаёт безопасное сообщение для логирования.
    Маскирует все чувствительные данные.
    """
    masked_message = mask_string(message)
    
    if data is not None:
        if isinstance(data, dict):
            masked_data = mask_dict(data)
            return f"{masked_message} | Data: {masked_data}"
        elif isinstance(data, str):
            return f"{masked_message} | {mask_string(data)}"
    
    return masked_message


# Для удобного импорта
__all__ = [
    "mask_sensitive_value",
    "mask_dict", 
    "mask_string",
    "mask_headers",
    "SecureLoggingMiddleware",
    "get_safe_log_message",
    "SENSITIVE_FIELDS",
]

